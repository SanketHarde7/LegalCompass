from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatStreamRequest
from app.services.rag_engine import rag_engine
from app.services.llm_service import llm_service
from app.schemas.contract import Clause
from typing import List
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
        # If user explicitly selected a clause, guarantee it's in context
        if request.selected_clause_id:
            selected = next((c for c in session.clauses if c.id == request.selected_clause_id), None)
            if selected:
                context_clauses.append(selected)

        top_k = rag_engine.retrieve_top_k(session_id, query, k=4)
        for c in top_k:
            if c not in context_clauses:
                context_clauses.append(c)
    elif request.contract_context:
        # Fallback to frontend contract context if backend was restarted or using preset
        filename = request.contract_context.filename or filename
        overall_fairness = request.contract_context.overall_fairness_score or overall_fairness
        if request.contract_context.clauses:
            for c_data in request.contract_context.clauses:
                c_id = c_data.get("id", "")
                c_title = c_data.get("title", "")
                c_text = c_data.get("text", "") or c_data.get("originalText", "")
                c_risk = c_data.get("riskLevel", "LOW")
                c_summary = c_data.get("plainSummary", "")
                c_sugg = c_data.get("suggestion", "")
                clause_obj = Clause(
                    id=c_id,
                    title=c_title,
                    text=c_text,
                    risk_level=c_risk,
                    plain_english_summary=c_summary,
                    suggested_pushback=c_sugg,
                    category=c_data.get("category", "OTHER"),
                )
                if request.selected_clause_id and c_id == request.selected_clause_id:
                    context_clauses.insert(0, clause_obj)
                elif len(context_clauses) < 4:
                    context_clauses.append(clause_obj)
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
