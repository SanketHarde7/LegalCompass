from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatStreamRequest
from app.services.rag_engine import rag_engine, is_global_risk_query, rank_risk_clauses
from app.services.llm_service import llm_service
from app.schemas.contract import Clause
from typing import Any, List
import logging


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", summary="Conversational legal copilot with Server-Sent Events (SSE) streaming")
async def chat_copilot(request: ChatStreamRequest):
    """Streams token-by-token responses, interactive clause citations, and counter-clause suggestions."""
    session_id = request.session_id
    query = request.message.strip()

    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_INPUT", "message": "Message query cannot be empty."},
        )

    # 1. Retrieve RAG context clauses and document context
    session = rag_engine.get_session(session_id)
    context_clauses: List[Clause] = []
    filename = "Active Agreement"
    overall_fairness: Any = 50

    if session:
        filename = session.filename
        overall_fairness = getattr(session, "overall_fairness_score", 50)
        context_clauses = rag_engine.retrieve_chat_context(
            session_id=session_id,
            query=query,
            selected_clause_id=request.selected_clause_id,
            k=7,
        )
    elif request.contract_context:
        # Fallback to frontend contract context
        filename = request.contract_context.filename or filename
        overall_fairness = request.contract_context.overall_fairness_score or overall_fairness
        raw_clauses: List[Clause] = []
        if request.contract_context.clauses:
            for idx, c_data in enumerate(request.contract_context.clauses, start=1):
                c_id = c_data.get("id") or f"clause_{idx}"
                c_title = c_data.get("title") or f"Clause {idx}"
                c_text = c_data.get("text") or c_data.get("originalText") or ""
                c_risk = c_data.get("riskLevel") or c_data.get("risk_level") or "LOW"
                c_summary = c_data.get("plainSummary") or c_data.get("plain_english_summary") or ""
                c_sugg = c_data.get("suggestion") or c_data.get("suggested_pushback") or None
                c_cat = c_data.get("category") or "OTHER"
                c_kind = c_data.get("clauseKind") or c_data.get("clause_kind") or "OPERATIVE"

                # Preserve supplied is_risk_bearing exactly, or infer from clause_kind if omitted
                if "isRiskBearing" in c_data and c_data["isRiskBearing"] is not None:
                    c_is_rb = bool(c_data["isRiskBearing"])
                elif "is_risk_bearing" in c_data and c_data["is_risk_bearing"] is not None:
                    c_is_rb = bool(c_data["is_risk_bearing"])
                else:
                    c_is_rb = str(c_kind).upper() not in ("DEFINITION", "HEADING", "RECITAL", "BOILERPLATE")

                # Preserve supplied unfairness_score exactly, without defaulting to 30 when missing
                if "unfairnessScore" in c_data and c_data["unfairnessScore"] is not None:
                    c_unfairness = int(c_data["unfairnessScore"])
                elif "unfairness_score" in c_data and c_data["unfairness_score"] is not None:
                    c_unfairness = int(c_data["unfairness_score"])
                else:
                    # Rational default matching the canonical risk severity, avoiding false-drop of HIGH/MEDIUM
                    c_unfairness = {"HIGH": 80, "MEDIUM": 60, "LOW": 20, "NEUTRAL": 10}.get(str(c_risk).upper(), 30)

                # Preserve supplied risk_reasons exactly
                raw_reasons = c_data.get("riskReasons") if "riskReasons" in c_data else c_data.get("risk_reasons")
                if raw_reasons is None:
                    c_reasons = []
                elif isinstance(raw_reasons, list):
                    c_reasons = [str(r) for r in raw_reasons]
                else:
                    c_reasons = [str(raw_reasons)]

                c_page = c_data.get("pageNumber") or c_data.get("page_number") or 1

                clause_obj = Clause(
                    id=c_id,
                    index=idx,
                    title=c_title,
                    text=c_text,
                    risk_level=c_risk,
                    plain_english_summary=c_summary,
                    suggested_pushback=c_sugg,
                    category=c_cat,
                    clause_kind=c_kind,
                    is_risk_bearing=c_is_rb,
                    risk_reasons=c_reasons,
                    unfairness_score=c_unfairness,
                    page_number=c_page,
                )
                raw_clauses.append(clause_obj)

        is_global = is_global_risk_query(query)
        if is_global:
            context_clauses = rank_risk_clauses(raw_clauses, limit=7)
        else:
            if request.selected_clause_id:
                sel = next((c for c in raw_clauses if c.id == request.selected_clause_id), None)
                if sel:
                    context_clauses.append(sel)
            # Find relevant clauses by query term matches
            query_words = [w.lower() for w in query.split() if len(w) > 3]
            scored_clauses = []
            for c in raw_clauses:
                if request.selected_clause_id and c.id == request.selected_clause_id:
                    continue
                c_text_lower = (c.title + " " + c.text).lower()
                matches = sum(1 for w in query_words if w in c_text_lower)
                if matches > 0:
                    scored_clauses.append((matches, c))
            scored_clauses.sort(key=lambda x: x[0], reverse=True)
            for _, c in scored_clauses:
                if len(context_clauses) < 7:
                    context_clauses.append(c)
            for c in raw_clauses:
                if c not in context_clauses and len(context_clauses) < 7:
                    context_clauses.append(c)

        # Opportunistically re-index session into RAG engine so future requests benefit from vector retrieval
        if session_id and raw_clauses and not rag_engine.get_session(session_id):
            try:
                score_val = overall_fairness if isinstance(overall_fairness, int) else 50
                rag_engine.index_document(
                    session_id=session_id,
                    filename=filename,
                    clauses=raw_clauses,
                    overall_fairness_score=score_val,
                )
            except Exception as e:
                logger.warning(f"Could not re-index session {session_id} in RAG engine: {e}")
    else:
        logger.info(f"No active RAG session found for {session_id}. Answering with generic legal context.")

    # 2. Convert history to dicts if present (maintain up to 6 turns of memory)
    history_dicts = None
    if request.history:
        history_dicts = [{"role": h.role, "content": h.content} for h in request.history[-6:]]

    # 3. Stream SSE response with contract info and memory
    contract_info = {
        "filename": filename,
        "overall_fairness_score": overall_fairness,
    }
    context_ids = [c.id for c in context_clauses]
    logger.info(f"Final context clauses passed to stream_chat_response: {context_ids}")

    event_stream = llm_service.stream_chat_response(
        session_id=session_id,
        query=query,
        context_clauses=context_clauses,
        history=history_dicts,
        contract_info=contract_info,
    )

    return StreamingResponse(
        event_stream,
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
