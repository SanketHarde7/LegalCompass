import re
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, AsyncGenerator, Dict, Any, Optional, Tuple, Set
from app.core.config import settings
from app.core.prompts import AUDITOR_PROMPT, SIMULATION_PROMPT, COPILOT_CHAT_PROMPT
from app.schemas.contract import Clause, ContractDocument, PageContent
from app.schemas.simulate import ScenarioSimulationResult, TriggeredClauseItem
from app.services.heuristic_engine import heuristic_engine
from app.services.fairness_calculator import calculate_overall_fairness

logger = logging.getLogger(__name__)

CITE_PATTERN = re.compile(r"\[CITE:([a-zA-Z0-9_-]+)\]")


def extract_citations_and_clean_text(
    text: str, allowed_clause_ids: Set[str]
) -> Tuple[List[str], str]:
    """Extracts valid, deduplicated citation IDs and strips citation markers from text.

    - Extracts all [CITE:clause_id] markers
    - Validates each against allowed_clause_ids
    - Discards invalid IDs silently
    - Deduplicates while preserving order
    - Removes all [CITE:...] markers from user-facing text
    """
    raw_citations = CITE_PATTERN.findall(text)
    valid_citations: List[str] = []
    seen: Set[str] = set()

    for cid in raw_citations:
        cid_clean = cid.strip()
        if cid_clean in allowed_clause_ids and cid_clean not in seen:
            valid_citations.append(cid_clean)
            seen.add(cid_clean)

    # Clean markers from text and normalize leftover duplicate spacing
    cleaned = CITE_PATTERN.sub("", text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r" +([.,;!?])", r"\1", cleaned)

    return valid_citations, cleaned.strip()


class CitationStreamFilter:
    """Filters [CITE:...] markers on the fly from streaming token chunks so they never leak to UI."""

    def __init__(self):
        self.buffer = ""

    def process_chunk(self, chunk: str) -> str:
        self.buffer += chunk
        if "[" not in self.buffer:
            out = self.buffer
            self.buffer = ""
            return out

        # If complete markers exist in buffer, strip them
        while True:
            match = CITE_PATTERN.search(self.buffer)
            if match:
                prefix = self.buffer[: match.start()]
                self.buffer = prefix + self.buffer[match.end() :]
            else:
                break

        # Check if buffer ends with a potential partial marker
        last_bracket = self.buffer.rfind("[")
        if last_bracket != -1:
            potential_marker = self.buffer[last_bracket:]
            if (
                potential_marker.startswith("[CITE:")
                or "[CITE:".startswith(potential_marker)
            ) and len(potential_marker) < 45:
                out = self.buffer[:last_bracket]
                self.buffer = potential_marker
                return out

        out = self.buffer
        self.buffer = ""
        return out

    def flush(self) -> str:
        """Flushes any remaining text at end of stream after removing any citation markers."""
        cleaned = CITE_PATTERN.sub("", self.buffer)
        cleaned = re.sub(r"\[CITE:[^\]]*$", "", cleaned)
        cleaned = re.sub(r"\[CITE?$", "", cleaned)
        self.buffer = ""
        return cleaned


class LLMService:
    """Multi-provider LLM service with dynamic model IDs from env and automatic failover.

    Priority:
    1. Google Gemini (using settings.GEMINI_API_KEY and settings.GEMINI_MODEL_ID)
    2. Failover to Groq (using settings.GROQ_API_KEY and settings.GROQ_MODEL_ID)
    3. Heuristic / Rule-based Legal Engine fallback if both fail or keys are unset.
    """

    def __init__(self):
        self._gemini_client = None
        self._groq_client = None

    # =========================================================================
    # Client Initializations
    # =========================================================================
    def _get_gemini_client(self):
        if self._gemini_client is not None:
            return self._gemini_client if self._gemini_client is not False else None
        if not settings.GEMINI_API_KEY:
            return None
        try:
            from google import genai
            self._gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
            logger.info(f"Gemini client initialized with model: {settings.GEMINI_MODEL_ID}")
        except Exception as e:
            logger.warning(f"Failed to initialize google-genai client: {e}")
            self._gemini_client = False
        return self._gemini_client if self._gemini_client is not False else None

    def _get_groq_client(self):
        if self._groq_client is not None:
            return self._groq_client if self._groq_client is not False else None
        if not settings.GROQ_API_KEY:
            return None
        try:
            from groq import AsyncGroq
            self._groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
            logger.info(f"Groq client initialized with model: {settings.GROQ_MODEL_ID}")
        except Exception as e:
            logger.warning(f"Failed to initialize Groq client: {e}")
            self._groq_client = False
        return self._groq_client if self._groq_client is not False else None

    # =========================================================================
    # Contract Analysis (JSON Mode)
    # =========================================================================
    async def _call_llm_json(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Invokes Gemini or Groq with JSON mode and returns parsed dictionary."""
        # 1. Try Gemini (Primary)
        gemini = self._get_gemini_client()
        if gemini:
            try:
                logger.info(f"Invoking Gemini model: {settings.GEMINI_MODEL_ID}")
                response = gemini.models.generate_content(
                    model=settings.GEMINI_MODEL_ID,
                    contents=prompt,
                    config={
                        "system_instruction": AUDITOR_PROMPT,
                        "response_mime_type": "application/json",
                        "temperature": 0.1,
                    },
                )
                if response.text:
                    parsed = self._extract_json(response.text)
                    if parsed:
                        return parsed
            except Exception as e:
                logger.warning(f"Gemini call failed or quota exceeded: {e}. Failing over to Groq...")

        # 2. Try Groq (Failover)
        groq = self._get_groq_client()
        if groq:
            try:
                logger.info(f"Invoking Groq model: {settings.GROQ_MODEL_ID}")
                chat_completion = await groq.chat.completions.create(
                    messages=[
                        {"role": "system", "content": AUDITOR_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    model=settings.GROQ_MODEL_ID,
                    temperature=0.1,
                    response_format={"type": "json_object"},
                )
                raw_json = chat_completion.choices[0].message.content
                if raw_json:
                    parsed = self._extract_json(raw_json)
                    if parsed:
                        return parsed
            except Exception as e:
                logger.warning(f"Groq call failed: {e}.")

        return None

    async def analyze_contract(
        self,
        raw_text: str,
        filename: str,
        initial_clauses: List[Clause],
        pages_content: Optional[List[Tuple[int, str]]] = None,
        document_title: Optional[str] = None,
    ) -> ContractDocument:
        """Analyzes structured contract clauses, classifies risk levels, calculates fairness score."""
        session_id = f"sess_{int(datetime.now(timezone.utc).timestamp())}_{abs(hash(filename)) % 10000}"
        page_objects: List[PageContent] = []
        if pages_content:
            page_objects = [PageContent(pageNumber=idx, text=txt) for idx, txt in pages_content]

        if not initial_clauses:
            logger.info("No initial clauses found to analyze.")
            return self._heuristic_analysis(session_id, filename, initial_clauses, page_objects, document_title)

        # -------------------------------------------------------------------------
        # Root cause F: Split initial_clauses into sequential batches (~6,000 chars per batch).
        # Ensures full coverage without hitting model context limits or dropping trailing sections.
        # -------------------------------------------------------------------------
        batches: List[List[Clause]] = []
        current_batch: List[Clause] = []
        current_chars = 0

        for c in initial_clauses:
            clause_len = len(c.title or "") + len(c.text or "")
            if current_chars + clause_len > 6000 and current_batch:
                batches.append(current_batch)
                current_batch = [c]
                current_chars = clause_len
            else:
                current_batch.append(c)
                current_chars += clause_len

        if current_batch:
            batches.append(current_batch)

        all_evaluated_clauses: List[Dict[str, Any]] = []
        fairness_scores: List[int] = []
        overview_snippets: List[str] = []
        total_batches = len(batches)

        for batch_idx, batch in enumerate(batches):
            # Root cause E: Send ALREADY-PARSED initial_clauses as structured JSON payload
            structured_clauses = [
                {"clause_id": c.id, "title": c.title, "text": c.text}
                for c in batch
            ]
            batch_header = f" (Batch {batch_idx + 1} of {total_batches})" if total_batches > 1 else ""
            prompt = (
                f"Contract Filename: {filename}\n"
                f"Document Title: {document_title or 'N/A'}\n\n"
                f"Input Clauses to Audit{batch_header}:\n"
                f"{json.dumps(structured_clauses, indent=2)}\n\n"
                "Audit each of the above clauses. Echo back the exact 'clause_id' for every clause evaluated, and output strictly valid JSON according to instructions."
            )

            batch_res = await self._call_llm_json(prompt)
            if batch_res and "clauses" in batch_res:
                for cd in batch_res.get("clauses", []):
                    all_evaluated_clauses.append(cd)
                if "overall_fairness_score" in batch_res:
                    try:
                        fairness_scores.append(int(batch_res["overall_fairness_score"]))
                    except (ValueError, TypeError):
                        pass
                if "summary_overview" in batch_res and batch_res["summary_overview"]:
                    overview_snippets.append(str(batch_res["summary_overview"]).strip())

        if all_evaluated_clauses:
            avg_score = round(sum(fairness_scores) / len(fairness_scores)) if fairness_scores else 50
            merged_overview = " ".join(overview_snippets) if overview_snippets else f"Analyzed {len(initial_clauses)} clauses across {len(page_objects)} pages."
            merged_data = {
                "overall_fairness_score": avg_score,
                "summary_overview": merged_overview,
                "clauses": all_evaluated_clauses,
            }
            return self._build_document_from_json(
                session_id, filename, merged_data, initial_clauses, page_objects, document_title
            )

        # 3. Fallback: Heuristic Legal Auditor
        logger.info("Using deterministic heuristic legal rules engine for contract analysis.")
        return self._heuristic_analysis(session_id, filename, initial_clauses, page_objects, document_title)

    def _get_applicable_suggestion(self, context_clauses: List[Clause]) -> Optional[Dict[str, Any]]:
        """Canonical helper: finds first HIGH-risk clause with suggested_pushback.
        Returns structured suggestion payload or None when no suggestion exists.
        """
        if not context_clauses:
            return None
        high_risk = next(
            (
                c for c in context_clauses
                if (c.risk_level == "HIGH" or getattr(c, "riskLevel", None) == "HIGH")
                and (c.suggested_pushback or getattr(c, "suggestion", None))
            ),
            None,
        )
        if high_risk:
            pushback = high_risk.suggested_pushback or getattr(high_risk, "suggestion", None)
            return {
                "type": "suggestion",
                "target_clause_id": high_risk.id,
                "counter_clause": pushback,
                "rationale": f"Replaces one-sided language in {high_risk.title} with mutual, capped obligations.",
            }
        return None

    # =========================================================================
    # Streaming Chat Copilot (SSE)
    # =========================================================================
    async def stream_chat_response(
        self,
        session_id: str = "",
        query: str = "",
        context_clauses: Optional[List[Clause]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        contract_info: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Streams assistant response token-by-token using Server-Sent Events (SSE).
        Deterministic event order:
        1. token events (with citation markers filtered out on the fly)
        2. suggestion event, if applicable
        3. citation event (valid context clause IDs only, deduplicated, ordered)
        4. done event
        """
        # Flexible positional handling if query passed as 1st arg and context_clauses as 2nd arg
        if isinstance(session_id, str) and isinstance(query, list) and context_clauses is None:
            context_clauses = query
            query = session_id
            session_id = ""
        context_clauses = context_clauses or []

        filename = contract_info.get("filename", "Active Contract") if contract_info else "Active Contract"
        fairness = contract_info.get("overall_fairness_score", "N/A") if contract_info else "N/A"

        def _format_chat_clause(c: Clause) -> str:
            reasons = f" | Reasons: {'; '.join(c.risk_reasons)}" if getattr(c, "risk_reasons", None) else ""
            kind = getattr(c, "clause_kind", "OPERATIVE")
            risk_bearing = getattr(c, "is_risk_bearing", True)
            unfairness = getattr(c, "unfairness_score", 30)
            return (
                f"[{c.id}] {c.title} (Kind: {kind}, Risk: {c.risk_level}, Unfairness: {unfairness}/100, "
                f"Risk-Bearing: {risk_bearing}, Category: {c.category}{reasons}):\n"
                f"{c.text}\nSummary: {c.plain_english_summary}"
            )

        context_text = "\n\n".join(
            [_format_chat_clause(c) for c in context_clauses]
        ) if context_clauses else "General contract terms."

        allowed_clause_ids: Set[str] = {c.id for c in context_clauses} if context_clauses else set()

        system_message = (
            f"{COPILOT_CHAT_PROMPT}\n\n"
            f"ACTIVE CONTRACT CONTEXT:\n"
            f"- Document Filename: {filename}\n"
            f"- Overall Fairness Score: {fairness}/100\n\n"
            f"RELEVANT CLAUSES IN CONTEXT:\n{context_text}"
        )

        streamed_success = False
        accumulated_raw_text = ""

        # 1. Try Gemini (Primary Engine with Multi-Turn Conversational Memory)
        gemini = self._get_gemini_client()
        if gemini:
            try:
                logger.info(f"Streaming chat via Gemini: {settings.GEMINI_MODEL_ID}")
                contents = []
                # Pass previous conversational memory turns
                if history:
                    for h in history[-6:]:
                        role = "model" if h.get("role") in ["assistant", "model"] else "user"
                        text = (h.get("content") or "").strip()
                        if text:
                            contents.append({"role": role, "parts": [{"text": text}]})

                # Append current user prompt
                contents.append({"role": "user", "parts": [{"text": query}]})

                response_stream = gemini.models.generate_content_stream(
                    model=settings.GEMINI_MODEL_ID,
                    contents=contents,
                    config={
                        "system_instruction": system_message,
                        "temperature": 0.2,
                        "max_output_tokens": 1000,
                    },
                )
                stream_filter = CitationStreamFilter()
                accumulated_raw_text = ""
                for chunk in response_stream:
                    if chunk.text:
                        accumulated_raw_text += chunk.text
                        filtered = stream_filter.process_chunk(chunk.text)
                        if filtered:
                            payload = json.dumps({"type": "token", "content": filtered})
                            yield f"data: {payload}\n\n"
                            await asyncio.sleep(0.01)

                flushed = stream_filter.flush()
                if flushed:
                    payload = json.dumps({"type": "token", "content": flushed})
                    yield f"data: {payload}\n\n"

                streamed_success = True
            except Exception as e:
                logger.warning(f"Gemini streaming failed: {e}. Failing over to Groq...")
                accumulated_raw_text = ""

        # 2. Try Groq (Failover with Conversational Memory)
        if not streamed_success:
            groq = self._get_groq_client()
            if groq:
                try:
                    logger.info(f"Streaming chat via Groq: {settings.GROQ_MODEL_ID}")
                    messages = [{"role": "system", "content": system_message}]
                    if history:
                        for h in history[-6:]:
                            role = "assistant" if h.get("role") in ["assistant", "model"] else "user"
                            text = (h.get("content") or "").strip()
                            if text:
                                messages.append({"role": role, "content": text})
                    messages.append({"role": "user", "content": query})

                    stream = await groq.chat.completions.create(
                        model=settings.GROQ_MODEL_ID,
                        messages=messages,
                        temperature=0.2,
                        max_tokens=350,
                        stream=True,
                    )
                    stream_filter = CitationStreamFilter()
                    accumulated_raw_text = ""
                    async for chunk in stream:
                        delta = chunk.choices[0].delta.content or ""
                        if delta:
                            accumulated_raw_text += delta
                            filtered = stream_filter.process_chunk(delta)
                            if filtered:
                                payload = json.dumps({"type": "token", "content": filtered})
                                yield f"data: {payload}\n\n"
                                await asyncio.sleep(0.01)

                    flushed = stream_filter.flush()
                    if flushed:
                        payload = json.dumps({"type": "token", "content": flushed})
                        yield f"data: {payload}\n\n"

                    streamed_success = True
                except Exception as e:
                    logger.warning(f"Groq streaming failed: {e}. Using heuristic streaming fallback...")
                    accumulated_raw_text = ""

        # 3. Fallback Heuristic Generator
        if not streamed_success:
            stream_filter = CitationStreamFilter()
            accumulated_raw_text = ""
            async for token in self._heuristic_stream(query, context_clauses):
                accumulated_raw_text += token
                filtered = stream_filter.process_chunk(token)
                if filtered:
                    payload = json.dumps({"type": "token", "content": filtered})
                    yield f"data: {payload}\n\n"
                    await asyncio.sleep(0.02)

            flushed = stream_filter.flush()
            if flushed:
                payload = json.dumps({"type": "token", "content": flushed})
                yield f"data: {payload}\n\n"

            streamed_success = True

        # 2. Suggestion event, if applicable (canonical implementation for all paths)
        suggestion_payload = self._get_applicable_suggestion(context_clauses)
        if suggestion_payload:
            yield f"data: {json.dumps(suggestion_payload)}\n\n"

        # 3. Citation event (grounded strictly in context_clauses, deduplicated, ordered)
        valid_citations, _ = extract_citations_and_clean_text(accumulated_raw_text, allowed_clause_ids)
        yield f'data: {{"type": "citation", "clause_ids": {json.dumps(valid_citations)}}}\n\n'

        # 4. Final done event
        yield 'data: {"type": "done", "total_tokens": 120}\n\n'

    # =========================================================================
    # Scenario Simulation
    # =========================================================================
    async def simulate_scenario(
        self, session_id: str, prompt: str, context_clauses: List[Clause]
    ) -> ScenarioSimulationResult:
        """Simulates real-world operational and financial risks for a what-if query."""
        context_str = "\n\n".join([f"[{c.id}] {c.title}:\n{c.text}" for c in context_clauses])
        user_msg = f"Scenario Prompt: {prompt}\n\nContextual Contract Clauses:\n{context_str}"

        # 1. Try Gemini
        gemini = self._get_gemini_client()
        if gemini:
            try:
                logger.info(f"Simulating scenario via Gemini: {settings.GEMINI_MODEL_ID}")
                response = gemini.models.generate_content(
                    model=settings.GEMINI_MODEL_ID,
                    contents=user_msg,
                    config={
                        "system_instruction": SIMULATION_PROMPT,
                        "response_mime_type": "application/json",
                        "temperature": 0.1,
                    },
                )
                if response.text:
                    data = self._extract_json(response.text)
                    if data:
                        return ScenarioSimulationResult(**data)
            except Exception as e:
                logger.warning(f"Gemini simulation failed: {e}. Failing over to Groq...")

        # 2. Try Groq
        groq = self._get_groq_client()
        if groq:
            try:
                logger.info(f"Simulating scenario via Groq: {settings.GROQ_MODEL_ID}")
                comp = await groq.chat.completions.create(
                    model=settings.GROQ_MODEL_ID,
                    messages=[
                        {"role": "system", "content": SIMULATION_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                raw = comp.choices[0].message.content
                if raw:
                    data = self._extract_json(raw)
                    if data:
                        return ScenarioSimulationResult(**data)
            except Exception as e:
                logger.warning(f"Groq simulation failed: {e}. Using heuristic simulation...")

        # 3. Fallback Heuristic
        return self._heuristic_simulate(prompt, context_clauses)

    # =========================================================================
    # Helpers & Fallback Rule Engine
    # =========================================================================
    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        try:
            return json.loads(text)
        except Exception:
            # Try to find first { and last }
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                try:
                    return json.loads(text[start : end + 1])
                except Exception:
                    pass
        return None

    def _build_document_from_json(
        self,
        session_id: str,
        filename: str,
        data: Dict[str, Any],
        initial_clauses: List[Clause],
        page_objects: List[PageContent],
        document_title: Optional[str] = None,
    ) -> ContractDocument:
        score = int(data.get("overall_fairness_score", 50))
        clauses_data = data.get("clauses", [])

        # Root cause E: Index LLM evaluations strictly by clause_id
        llm_map: Dict[str, Dict[str, Any]] = {}
        for cd in clauses_data:
            cid = cd.get("clause_id")
            if cid:
                llm_map[str(cid).strip()] = cd

        analyzed_clauses: List[Clause] = []
        if initial_clauses:
            for idx, orig_clause in enumerate(initial_clauses, start=1):
                # Root cause E: Match strictly on returned clause_id against original clause_id
                matched_cd = llm_map.get(orig_clause.id)

                # Root cause D: Deleted positional fallback `if not matched_cd and idx - 1 < len(clauses_data)`.
                # Never map by array position!

                if matched_cd:
                    # Accuracy V2: Read structural classification fields from LLM response
                    llm_clause_kind = matched_cd.get("clause_kind", "OPERATIVE")
                    llm_is_risk_bearing = matched_cd.get("is_risk_bearing", True)
                    llm_risk_reasons = matched_cd.get("risk_reasons", [])
                    llm_risk_level = matched_cd.get("risk_level", "LOW")
                    llm_unfairness = int(matched_cd.get("unfairness_score", 20))

                    # Accuracy V2: Post-LLM validation gate — prevent LLM from hallucinating
                    # HIGH risk on non-risk-bearing clauses (definitions, headings, recitals).
                    # Use heuristic engine as ground-truth for structural classification.
                    heuristic_check = heuristic_engine.evaluate_clause(orig_clause.title, orig_clause.text)
                    if not heuristic_check.is_risk_bearing:
                        # Heuristic says non-risk-bearing — override LLM if it disagrees
                        llm_clause_kind = heuristic_check.clause_kind
                        llm_is_risk_bearing = False
                        if llm_risk_level == "HIGH":
                            llm_risk_level = "LOW"
                            llm_unfairness = min(llm_unfairness, 15)
                            llm_risk_reasons = []
                            logger.info(f"Post-LLM gate: overrode HIGH->LOW on non-risk-bearing clause {orig_clause.id} ({heuristic_check.clause_kind})")
                        elif llm_risk_level == "MEDIUM":
                            llm_risk_level = "LOW"
                            llm_unfairness = min(llm_unfairness, 15)
                            llm_risk_reasons = []

                    analyzed_clauses.append(
                        Clause(
                            id=orig_clause.id,
                            index=orig_clause.index or idx,
                            title=orig_clause.title,
                            text=orig_clause.text,
                            category=matched_cd.get("category", orig_clause.category or "OTHER"),
                            riskLevel=llm_risk_level,
                            plainSummary=matched_cd.get("plain_english_summary", ""),
                            suggestion=matched_cd.get("suggested_pushback"),
                            unfairnessScore=llm_unfairness,
                            clauseKind=llm_clause_kind,
                            isRiskBearing=llm_is_risk_bearing,
                            riskReasons=llm_risk_reasons if isinstance(llm_risk_reasons, list) else [],
                            pageNumber=orig_clause.page_number or 1,
                            startOffset=orig_clause.start_offset,
                            endOffset=orig_clause.end_offset,
                        )
                    )
                else:
                    # Root cause E: If no match exists for a given original clause, use heuristic engine
                    # for structural classification instead of defaulting to LOW.
                    heuristic_fb = heuristic_engine.evaluate_clause(orig_clause.title, orig_clause.text)
                    analyzed_clauses.append(
                        Clause(
                            id=orig_clause.id,
                            index=orig_clause.index or idx,
                            title=orig_clause.title,
                            text=orig_clause.text,
                            category=heuristic_fb.category,
                            riskLevel=heuristic_fb.risk_level,
                            plainSummary=heuristic_fb.plain_summary or "Standard commercial legal covenant.",
                            suggestion=heuristic_fb.suggested_pushback,
                            unfairnessScore=heuristic_fb.unfairness_score,
                            clauseKind=heuristic_fb.clause_kind,
                            isRiskBearing=heuristic_fb.is_risk_bearing,
                            riskReasons=list(heuristic_fb.risk_reasons),
                            pageNumber=orig_clause.page_number or 1,
                            startOffset=orig_clause.start_offset,
                            endOffset=orig_clause.end_offset,
                        )
                    )
        else:
            for i, cd in enumerate(clauses_data, start=1):
                cid = cd.get("clause_id") or f"clause_{i}"
                analyzed_clauses.append(
                    Clause(
                        id=cid,
                        index=i,
                        title=cd.get("title", f"Clause {i}"),
                        text=cd.get("text", ""),
                        category=cd.get("category", "OTHER"),
                        riskLevel=cd.get("risk_level", "MEDIUM"),
                        plainSummary=cd.get("plain_english_summary", ""),
                        suggestion=cd.get("suggested_pushback"),
                        unfairnessScore=int(cd.get("unfairness_score", 50)),
                        clauseKind=cd.get("clause_kind", "OPERATIVE"),
                        isRiskBearing=cd.get("is_risk_bearing", True),
                        riskReasons=cd.get("risk_reasons", []),
                        pageNumber=1,
                    )
                )

        total_pages = len(page_objects) if page_objects else max(
            [c.page_number or 1 for c in analyzed_clauses] + [1]
        )

        # Fix 3: Authoritative overall fairness score calculated directly from merged final clauses
        overall_score = calculate_overall_fairness(analyzed_clauses)

        return ContractDocument(
            sessionId=session_id,
            filename=filename,
            uploadTimestamp=datetime.now(timezone.utc).isoformat(),
            overallFairnessScore=overall_score,
            totalPages=total_pages,
            pages=page_objects,
            clauses=analyzed_clauses,
            documentTitle=document_title,
        )

    def _heuristic_analysis(
        self,
        session_id: str,
        filename: str,
        initial_clauses: List[Clause],
        page_objects: List[PageContent],
        document_title: Optional[str] = None,
    ) -> ContractDocument:
        """Deterministic structural rule-based legal engine with structural pre-screening + Triple Gate."""
        evaluated_clauses: List[Clause] = []

        for idx, clause in enumerate(initial_clauses, start=1):
            assessment = heuristic_engine.evaluate_clause(clause.title, clause.text)
            evaluated_clauses.append(
                Clause(
                    id=clause.id,
                    index=clause.index or idx,
                    title=clause.title,
                    text=clause.text,
                    category=assessment.category,
                    riskLevel=assessment.risk_level,
                    plainSummary=assessment.plain_summary,
                    suggestion=assessment.suggested_pushback,
                    unfairnessScore=assessment.unfairness_score,
                    clauseKind=assessment.clause_kind,
                    isRiskBearing=assessment.is_risk_bearing,
                    riskReasons=list(assessment.risk_reasons),
                    pageNumber=clause.page_number or 1,
                    startOffset=clause.start_offset,
                    endOffset=clause.end_offset,
                )
            )

        # Fix 3: Authoritative overall fairness score calculated directly from final evaluated clauses
        overall_score = calculate_overall_fairness(evaluated_clauses)
        total_pages = len(page_objects) if page_objects else max(
            [c.page_number or 1 for c in evaluated_clauses] + [1]
        )

        return ContractDocument(
            sessionId=session_id,
            filename=filename,
            uploadTimestamp=datetime.now(timezone.utc).isoformat(),
            overallFairnessScore=overall_score,
            totalPages=total_pages,
            pages=page_objects,
            clauses=evaluated_clauses,
            documentTitle=document_title,
        )

    async def _heuristic_stream(self, query: str, context: List[Clause]) -> AsyncGenerator[str, None]:
        """Simulates realistic conversational streaming chunks based on context."""
        matched_clause = context[0] if context else None
        cite_marker = f" [CITE:{matched_clause.id}]" if matched_clause else ""
        response_text = (
            f"Based on your contract terms, particularly **{matched_clause.title if matched_clause else 'the agreement'}**, "
            "here is an analysis of your operational and legal risk:\n\n"
            f"1. **Core Exposure:** {matched_clause.plain_english_summary if matched_clause else 'Review the highlighted terms for liability caps.'}{cite_marker}\n"
            "2. **Legal Leverage:** The drafting party holds significant unilateral leverage under the current draft.\n\n"
            "**Recommendation:** Propose balanced mutual terms to cap total financial liability and guarantee payment for completed milestones."
        )
        words = response_text.split(" ")
        for word in words:
            yield word + " "
            await asyncio.sleep(0.02)

    def _heuristic_simulate(self, prompt: str, context: List[Clause]) -> ScenarioSimulationResult:
        """Heuristic what-if scenario evaluator."""
        first = context[0] if context else None
        return ScenarioSimulationResult(
            scenarioTitle=prompt[:60],
            triggeredClauses=[
                TriggeredClauseItem(
                    clauseId=first.id if first else "clause_1",
                    clauseTitle=first.title if first else "Standard Contract Terms",
                    impact="Contract provisions strictly enforce unilateral terms against contractor/tenant.",
                )
            ],
            riskEvaluation="Under the current contract terms, the counterparty retains legal discretion to terminate or delay performance without penalty, exposing you to uncompensated hours or loss of deposit.",
            financialExposure="Up to 100% of unpaid invoice balance or forfeited deposit with no contractually guaranteed late interest remedies.",
            recommendedAction="Negotiate mutual 30-day notice requirements and condition performance or IP transfers strictly on cleared funds.",
            riskLevel="HIGH",
        )


llm_service = LLMService()
