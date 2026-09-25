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
            self._groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY, max_retries=0)
            logger.info(f"Groq client initialized with model: {settings.GROQ_MODEL_ID}")
        except Exception as e:
            logger.warning(f"Failed to initialize Groq client: {e}")
            self._groq_client = False
        return self._groq_client if self._groq_client is not False else None

    def _get_provider_order(self) -> List[str]:
        """Returns ordered list of providers based on settings.LLM_PROVIDER_ORDER.
        Defaults to ['groq', 'gemini'] as primary/failover.
        """
        raw = getattr(settings, "LLM_PROVIDER_ORDER", "") or "groq,gemini"
        providers = [p.strip().lower() for p in raw.split(",") if p.strip()]
        valid = [p for p in providers if p in ("groq", "gemini")]
        if not valid:
            return ["groq", "gemini"]
        for p in ("groq", "gemini"):
            if p not in valid:
                valid.append(p)
        return valid

    def _get_gemini_candidate_models(self) -> List[str]:
        """Returns ordered list of Gemini model candidates to attempt, prioritizing active, high-quota models."""
        configured = (getattr(settings, "GEMINI_MODEL_ID", "") or "").strip()
        candidates = ["gemini-3.5-flash-lite", configured, "gemini-3.8-flash", "gemini-flash-latest"]
        deprecated = {"gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"}
        seen = set()
        res = []
        for m in candidates:
            if m and m not in seen and m not in deprecated:
                seen.add(m)
                res.append(m)
        if "gemini-3.5-flash-lite" not in res:
            res.insert(0, "gemini-3.5-flash-lite")
        return res

    # =========================================================================
    # Contract Analysis (JSON Mode)
    # =========================================================================
    async def _call_llm_json(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Invokes Groq or Gemini with JSON mode according to provider preference order (Groq primary, Gemini failover)."""
        providers = self._get_provider_order()
        for provider in providers:
            if provider == "groq":
                groq = self._get_groq_client()
                if groq:
                    try:
                        logger.info(f"Invoking Groq model: {settings.GROQ_MODEL_ID}")
                        chat_completion = await asyncio.wait_for(
                            groq.chat.completions.create(
                                messages=[
                                    {"role": "system", "content": AUDITOR_PROMPT},
                                    {"role": "user", "content": prompt},
                                ],
                                model=settings.GROQ_MODEL_ID,
                                temperature=0.1,
                                max_tokens=1500,
                                response_format={"type": "json_object"},
                            ),
                            timeout=15.0,
                        )
                        raw_json = chat_completion.choices[0].message.content
                        if raw_json:
                            parsed = self._extract_json(raw_json)
                            if parsed:
                                return parsed
                    except Exception as e:
                        err_msg = str(e)
                        if "429" in err_msg:
                            logger.warning(f"Groq 429 rate limit hit. Failing over immediately to next provider: {e}")
                        else:
                            logger.warning(f"Groq call failed or timed out: {e}. Failing over to next provider...")

            elif provider == "gemini":
                gemini = self._get_gemini_client()
                if gemini:
                    for g_model in self._get_gemini_candidate_models():
                        try:
                            logger.info(f"Invoking Gemini model: {g_model}")
                            response = await asyncio.wait_for(
                                asyncio.to_thread(
                                    gemini.models.generate_content,
                                    model=g_model,
                                    contents=prompt,
                                    config={
                                        "system_instruction": AUDITOR_PROMPT,
                                        "response_mime_type": "application/json",
                                        "temperature": 0.1,
                                    },
                                ),
                                timeout=20.0,
                            )
                            if response.text:
                                parsed = self._extract_json(response.text)
                                if parsed:
                                    return parsed
                            break
                        except Exception as e:
                            err_str = str(e)
                            if any(k in err_str for k in ("404", "503", "UNAVAILABLE", "NOT_FOUND", "RESOURCE_EXHAUSTED")):
                                logger.warning(f"Gemini model {g_model} returned {e}, trying next candidate...")
                                continue
                            logger.warning(f"Gemini call failed or timed out: {e}.")
                            break

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

        # Process batches sequentially (bounded by semaphore to respect rate limits)
        sem = asyncio.Semaphore(1)

        async def _process_single_batch(batch_idx: int, batch: List[Clause]):
            async with sem:
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
                try:
                    return await self._call_llm_json(prompt)
                except Exception as e:
                    logger.warning(f"Batch {batch_idx + 1} analysis failed: {e}")
                    return None

        batch_results = await asyncio.gather(
            *[_process_single_batch(idx, b) for idx, b in enumerate(batches)],
            return_exceptions=True,
        )

        for batch_res in batch_results:
            if isinstance(batch_res, dict) and "clauses" in batch_res:
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
    # Chat Canonical Context Formatting
    # =========================================================================
    def format_chat_clause(self, c: Clause) -> str:
        """Formats a single clause into canonical structured format for chat context."""
        cid = getattr(c, "id", "clause")
        title = getattr(c, "title", "Untitled Clause")
        kind = getattr(c, "clause_kind", "OPERATIVE")
        risk_bearing = getattr(c, "is_risk_bearing", True)
        risk_level = getattr(c, "risk_level", "LOW")
        unfairness = getattr(c, "unfairness_score", 30)
        category = getattr(c, "category", "OTHER")
        text = getattr(c, "text", "")
        summary = getattr(c, "plain_english_summary", "") or getattr(c, "plainSummary", "")
        reasons_list = getattr(c, "risk_reasons", []) or []

        if reasons_list:
            reasons_str = "\n".join(f"- {r}" for r in reasons_list)
        else:
            reasons_str = "- None (Standard or balanced provision)"

        pushback = getattr(c, "suggested_pushback", None) or getattr(c, "suggestion", None)
        pushback_str = f"\nSuggested Pushback: {pushback}" if pushback else ""

        return (
            f"[{cid}]\n"
            f"Title: {title}\n"
            f"Kind: {kind}\n"
            f"Risk Bearing: {str(risk_bearing).lower()}\n"
            f"Risk Level: {risk_level}\n"
            f"Unfairness Score: {unfairness}\n"
            f"Risk Reasons:\n{reasons_str}\n"
            f"Category: {category}\n"
            f"Text:\n{text}\n"
            f"Summary:\n{summary}"
            f"{pushback_str}"
        )

    def format_chat_context(
        self,
        context_clauses: List[Clause],
        contract_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Constructs full system message prompt including Active Contract Context and Canonical Clauses."""
        filename = contract_info.get("filename", "Active Contract") if contract_info else "Active Contract"
        fairness = contract_info.get("overall_fairness_score", "N/A") if contract_info else "N/A"

        context_text = "\n\n".join(
            [self.format_chat_clause(c) for c in context_clauses]
        ) if context_clauses else "General contract terms."

        return (
            f"{COPILOT_CHAT_PROMPT}\n\n"
            f"ACTIVE CONTRACT CONTEXT:\n"
            f"- Document Filename: {filename}\n"
            f"- Overall Fairness Score: {fairness}/100\n\n"
            f"RELEVANT CLAUSES IN CONTEXT:\n{context_text}"
        )

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
        logger.info(f"stream_chat_response received {len(context_clauses)} context_clauses: {[c.id for c in context_clauses]}")

        allowed_clause_ids: Set[str] = {c.id for c in context_clauses} if context_clauses else set()
        system_message = self.format_chat_context(context_clauses, contract_info)

        streamed_success = False
        accumulated_raw_text = ""

        # Iterate providers in preference order (Groq primary, Gemini failover)
        for provider in self._get_provider_order():
            if streamed_success:
                break

            if provider == "groq":
                groq = self._get_groq_client()
                if groq:
                    emitted_visible_text = ""
                    provider_raw_text = ""
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
                            max_tokens=1000,
                            stream=True,
                        )
                        stream_filter = CitationStreamFilter()
                        async for chunk in stream:
                            delta = chunk.choices[0].delta.content or ""
                            if delta:
                                provider_raw_text += delta
                                filtered = stream_filter.process_chunk(delta)
                                if filtered:
                                    emitted_visible_text += filtered
                                    payload = json.dumps({"type": "token", "content": filtered})
                                    yield f"data: {payload}\n\n"
                                    await asyncio.sleep(0.01)

                        flushed = stream_filter.flush()
                        if flushed:
                            emitted_visible_text += flushed
                            payload = json.dumps({"type": "token", "content": flushed})
                            yield f"data: {payload}\n\n"

                        if emitted_visible_text.strip():
                            accumulated_raw_text = provider_raw_text
                            streamed_success = True
                        else:
                            logger.warning("Groq stream finished but produced zero usable visible text. Failing over...")
                            accumulated_raw_text = ""
                    except Exception as e:
                        if emitted_visible_text.strip():
                            logger.warning(f"Groq streaming interrupted after partial output: {e}.")
                            accumulated_raw_text = provider_raw_text
                            streamed_success = True
                        else:
                            logger.warning(f"Groq streaming failed: {e}. Failing over...")
                            accumulated_raw_text = ""

            elif provider == "gemini":
                gemini = self._get_gemini_client()
                if gemini:
                    for g_model in self._get_gemini_candidate_models():
                        emitted_visible_text = ""
                        provider_raw_text = ""
                        try:
                            logger.info(f"Streaming chat via Gemini: {g_model}")
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
                                model=g_model,
                                contents=contents,
                                config={
                                    "system_instruction": system_message,
                                    "temperature": 0.2,
                                    "max_output_tokens": 1000,
                                },
                            )
                            stream_filter = CitationStreamFilter()
                            for chunk in response_stream:
                                if chunk.text:
                                    provider_raw_text += chunk.text
                                    filtered = stream_filter.process_chunk(chunk.text)
                                    if filtered:
                                        emitted_visible_text += filtered
                                        payload = json.dumps({"type": "token", "content": filtered})
                                        yield f"data: {payload}\n\n"
                                        await asyncio.sleep(0.01)

                            flushed = stream_filter.flush()
                            if flushed:
                                emitted_visible_text += flushed
                                payload = json.dumps({"type": "token", "content": flushed})
                                yield f"data: {payload}\n\n"

                            if emitted_visible_text.strip():
                                accumulated_raw_text = provider_raw_text
                                streamed_success = True
                                break
                            else:
                                logger.warning(f"Gemini model {g_model} produced zero usable visible text.")
                                accumulated_raw_text = ""
                        except Exception as e:
                            err_str = str(e)
                            if any(k in err_str for k in ("404", "503", "UNAVAILABLE", "NOT_FOUND", "RESOURCE_EXHAUSTED")) and not emitted_visible_text.strip():
                                logger.warning(f"Gemini model {g_model} returned {e}, trying next candidate...")
                                continue
                            if emitted_visible_text.strip():
                                logger.warning(f"Gemini streaming interrupted: {e}.")
                                accumulated_raw_text = provider_raw_text
                                streamed_success = True
                                break
                            else:
                                logger.warning(f"Gemini streaming failed: {e}.")
                                accumulated_raw_text = ""
                                break

        # 3. Fallback Heuristic Generator
        if not streamed_success:
            logger.info("Executing heuristic streaming fallback...")
            stream_filter = CitationStreamFilter()
            provider_raw_text = ""
            emitted_visible_text = ""
            async for token in self._heuristic_stream(query, context_clauses):
                provider_raw_text += token
                filtered = stream_filter.process_chunk(token)
                if filtered:
                    emitted_visible_text += filtered
                    payload = json.dumps({"type": "token", "content": filtered})
                    yield f"data: {payload}\n\n"
                    await asyncio.sleep(0.02)

            flushed = stream_filter.flush()
            if flushed:
                emitted_visible_text += flushed
                payload = json.dumps({"type": "token", "content": flushed})
                yield f"data: {payload}\n\n"

            accumulated_raw_text = provider_raw_text
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

        for provider in self._get_provider_order():
            if provider == "groq":
                groq = self._get_groq_client()
                if groq:
                    try:
                        logger.info(f"Simulating scenario via Groq: {settings.GROQ_MODEL_ID}")
                        comp = await asyncio.wait_for(
                            groq.chat.completions.create(
                                model=settings.GROQ_MODEL_ID,
                                messages=[
                                    {"role": "system", "content": SIMULATION_PROMPT},
                                    {"role": "user", "content": user_msg},
                                ],
                                response_format={"type": "json_object"},
                                temperature=0.1,
                                max_tokens=2048,
                            ),
                            timeout=20.0,
                        )
                        raw = comp.choices[0].message.content
                        if raw:
                            data = self._extract_json(raw)
                            if data:
                                return ScenarioSimulationResult(**data)
                    except Exception as e:
                        logger.warning(f"Groq simulation failed or timed out: {e}. Failing over to next provider...")

            elif provider == "gemini":
                gemini = self._get_gemini_client()
                if gemini:
                    for g_model in self._get_gemini_candidate_models():
                        try:
                            logger.info(f"Simulating scenario via Gemini: {g_model}")
                            response = await asyncio.wait_for(
                                asyncio.to_thread(
                                    gemini.models.generate_content,
                                    model=g_model,
                                    contents=user_msg,
                                    config={
                                        "system_instruction": SIMULATION_PROMPT,
                                        "response_mime_type": "application/json",
                                        "temperature": 0.1,
                                    },
                                ),
                                timeout=25.0,
                            )
                            if response.text:
                                data = self._extract_json(response.text)
                                if data:
                                    return ScenarioSimulationResult(**data)
                            break
                        except Exception as e:
                            err_str = str(e)
                            if any(k in err_str for k in ("404", "503", "UNAVAILABLE", "NOT_FOUND", "RESOURCE_EXHAUSTED")):
                                logger.warning(f"Gemini model {g_model} returned {e}, trying next candidate...")
                                continue
                            logger.warning(f"Gemini simulation failed or timed out: {e}.")
                            break

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
                # Match strictly on returned clause_id against original clause_id
                matched_cd = llm_map.get(orig_clause.id)

                # STEP 1: Heuristic structural classifier is the authoritative ground truth for structure
                heuristic_check = heuristic_engine.evaluate_clause(
                    orig_clause.title, orig_clause.text, all_clauses=initial_clauses
                )
                trusted_clause_kind = heuristic_check.clause_kind
                trusted_is_risk_bearing = heuristic_check.is_risk_bearing

                # STEP 2 & 3: Merge Structural & Risk fields using bidirectional validation
                if not trusted_is_risk_bearing:
                    # Structural classifier says NOT risk-bearing:
                    # Force NEUTRAL, unfairness <= 15, no pushback, no risk reasons
                    final_risk_level = "NEUTRAL"
                    raw_unfairness = int(matched_cd.get("unfairness_score", 10)) if matched_cd else 10
                    final_unfairness = min(raw_unfairness, 15)
                    final_suggestion = None
                    final_risk_reasons = []
                    final_plain_summary = (
                        matched_cd.get("plain_english_summary", "")
                        if matched_cd and matched_cd.get("plain_english_summary")
                        else heuristic_check.plain_summary
                    )
                    final_category = (
                        matched_cd.get("category", orig_clause.category or "OTHER")
                        if matched_cd
                        else heuristic_check.category
                    )
                else:
                    # Structural classifier says risk-bearing:
                    if matched_cd:
                        raw_llm_risk = str(matched_cd.get("risk_level", "LOW")).upper()
                        raw_llm_unfairness = int(matched_cd.get("unfairness_score", 30))
                        final_suggestion = matched_cd.get("suggested_pushback")
                        final_risk_reasons = (
                            matched_cd.get("risk_reasons", [])
                            if isinstance(matched_cd.get("risk_reasons"), list)
                            else []
                        )
                        final_plain_summary = matched_cd.get("plain_english_summary", "") or heuristic_check.plain_summary
                        final_category = matched_cd.get("category", orig_clause.category or "OTHER")

                        # Safety rule: HIGH requires triple-gate logic
                        if raw_llm_risk == "HIGH":
                            if heuristic_engine.passes_triple_gate(orig_clause.title, orig_clause.text, heuristic_check):
                                final_risk_level = "HIGH"
                                final_unfairness = raw_llm_unfairness
                            else:
                                logger.info(
                                    f"Triple-gate safety: LLM assigned HIGH on {orig_clause.id} "
                                    f"but clause lacks all three gates; downgrading to MEDIUM."
                                )
                                final_risk_level = "MEDIUM"
                                final_unfairness = min(raw_llm_unfairness, 65)
                        else:
                            # Preserve LLM result (MEDIUM, LOW, etc.) - do not auto-downgrade to LOW
                            final_risk_level = raw_llm_risk
                            final_unfairness = raw_llm_unfairness
                    else:
                        # Fallback to heuristic evaluation when no LLM match exists
                        final_risk_level = heuristic_check.risk_level
                        final_unfairness = heuristic_check.unfairness_score
                        final_suggestion = heuristic_check.suggested_pushback
                        final_risk_reasons = list(heuristic_check.risk_reasons)
                        final_plain_summary = heuristic_check.plain_summary
                        final_category = heuristic_check.category

                analyzed_clauses.append(
                    Clause(
                        id=orig_clause.id,
                        index=orig_clause.index or idx,
                        title=orig_clause.title,
                        text=orig_clause.text,
                        category=final_category,
                        riskLevel=final_risk_level,
                        plainSummary=final_plain_summary or "Standard commercial legal covenant.",
                        suggestion=final_suggestion,
                        unfairnessScore=final_unfairness,
                        clauseKind=trusted_clause_kind,
                        isRiskBearing=trusted_is_risk_bearing,
                        riskReasons=final_risk_reasons,
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
            assessment = heuristic_engine.evaluate_clause(clause.title, clause.text, all_clauses=initial_clauses)
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

    def _generate_tailored_counter_proposal(self, clause: Clause) -> str:
        """Generates a protective replacement clause tailored to the actual clause text and risk reasons.
        Avoids generic or section-name-only boilerplate rewrites.
        """
        # 1. Prefer canonical suggested_pushback if already attached
        pushback = getattr(clause, "suggested_pushback", None) or getattr(clause, "suggestion", None)
        if pushback and len(str(pushback).strip()) > 10:
            return str(pushback).strip()

        text_lower = (getattr(clause, "text", "") or "").lower()
        title_lower = (getattr(clause, "title", "") or "").lower()
        reasons = " ".join(getattr(clause, "risk_reasons", []) or []).lower()
        combined = f"{title_lower} {text_lower} {reasons}"

        # 2. Intellectual Property & Work Product
        if any(k in combined for k in ["intellectual property", "inventions", "work made for hire", "deliverables", "assigns all", "assign all"]):
            return "All intellectual property rights in and to Deliverables shall transfer exclusively to Client strictly upon Contractor's receipt of full and complete invoice payment."

        # 3. Order of Precedence & Invoicing Carve-Outs
        if any(k in combined for k in ["order of precedence", "purchase order", "invoice shall control", "override"]):
            return "The terms and conditions of this Agreement shall strictly prevail and control over any conflict with any Purchase Order or invoice."

        # 4. Indemnification & Defense Costs
        if any(k in combined for k in ["indemn", "hold harmless", "defense costs", "attorney fees"]):
            return "Each party shall mutually indemnify the other against third-party claims arising solely from its gross negligence. Total liability under this indemnity shall be capped at fees received under this Agreement."

        # 5. Termination & Forfeiture
        if any(k in combined for k in ["terminat", "cancel", "forfeit"]):
            return "Either party may terminate for convenience upon thirty (30) days prior written notice. Upon termination, Client shall pay Contractor for all completed work and non-cancelable commitments."

        # 6. Renewal & Term Extensions
        if any(k in combined for k in ["renew", "auto-renew", "extension", "lock-in"]):
            return "Any extension or renewal of the term shall require the mutual written agreement of both parties executed prior to term expiration."

        # 7. Payment Terms, Setoff & Withholding
        if any(k in combined for k in ["payment", "invoice", "withhold", "setoff", "net 90", "net 60"]):
            return "Invoices shall be payable within thirty (30) days of receipt. Undisputed invoice portions shall be disbursed immediately, and disputed items resolved in good faith."

        # 8. Inspection / Audit / Tenancy Entry
        if any(k in combined for k in ["audit", "inspection", "enter premises", "deposit"]):
            return "Audits or premise inspections may occur only during normal business hours with at least seven (7) business days advance written notice."

        # Default fallback
        return "Obligations shall be mutual, reasonable, and capped at total fees paid under this Agreement, with neither party exercising unilateral discretion."

    async def _heuristic_stream(self, query: str, context: List[Clause]) -> AsyncGenerator[str, None]:
        """Simulates realistic conversational streaming chunks based on context."""
        from app.services.rag_engine import is_global_risk_query, is_materially_risky_clause

        logger.info(f"_heuristic_stream entry: query='{query}', context={len(context)} clauses: {[c.id for c in context]}")

        if is_global_risk_query(query) and context:
            # Filter strictly to materially risky clauses (HIGH or genuine MEDIUM)
            material_clauses = [c for c in context if is_materially_risky_clause(c)]
            logger.info(f"_heuristic_stream material_clauses: {len(material_clauses)} clauses: {[c.id for c in material_clauses]}")
            if not material_clauses:
                response_text = (
                    "Based on the canonical analysis of your agreement, no material legal risks or predatory operative provisions were detected. "
                    "The reviewed terms appear standard, balanced, or protective for your position.\n\n"
                    "*(LegalCompass provides educational risk analysis, not formal legal counsel.)*"
                )
            else:
                count = len(material_clauses)
                count_str = f"the {count}" if count > 1 else "the"
                lines = [
                    f"Based on the canonical analysis of your agreement, {count_str} materially risky operative provision{'s are' if count > 1 else ' is'}:\n"
                ]
                for idx, c in enumerate(material_clauses, 1):
                    cite = f" [CITE:{c.id}]"
                    summary = c.plain_english_summary or getattr(c, "plainSummary", "") or f"Assessed as {c.risk_level} risk with material imbalance."
                    lines.append(f"{idx}. **{c.title}** ({c.risk_level} Risk): {summary}{cite}")

                top_c = material_clauses[0]
                counter = self._generate_tailored_counter_proposal(top_c)
                lines.append(f"\n**Protective Counter-Proposal ({top_c.title}):** {counter}")
                if count < 5 and any(num in query.lower() for num in ["5", "five", "top 5", "top five"]):
                    lines.append(f"\n*(Note: Only {count} materially risky operative provision{'s exist' if count > 1 else ' exists'} in this agreement; remaining terms are balanced, standard, or protective.)*")
                lines.append("\n*(LegalCompass provides educational risk analysis, not formal legal counsel.)*")
                response_text = "\n".join(lines)
        else:
            matched_clause = context[0] if context else None
            cite_marker = f" [CITE:{matched_clause.id}]" if matched_clause else ""
            summary = (matched_clause.plain_english_summary or getattr(matched_clause, "plainSummary", "")) if matched_clause else "Review the highlighted terms for liability caps."
            counter = self._generate_tailored_counter_proposal(matched_clause) if matched_clause else "Propose balanced mutual terms to cap total financial liability and guarantee payment for completed milestones."
            response_text = (
                f"Based on your contract terms, particularly **{matched_clause.title if matched_clause else 'the agreement'}**, "
                "here is an analysis of your operational and legal risk:\n\n"
                f"1. **Core Exposure:** {summary}{cite_marker}\n"
                "2. **Legal Leverage:** The drafting party holds significant unilateral leverage under the current draft.\n\n"
                f"**Recommendation:** {counter}\n\n"
                "*(LegalCompass provides educational risk analysis, not formal legal counsel.)*"
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
