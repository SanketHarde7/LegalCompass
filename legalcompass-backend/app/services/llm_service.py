import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, AsyncGenerator, Dict, Any, Optional, Tuple
from app.core.config import settings
from app.core.prompts import AUDITOR_PROMPT, SIMULATION_PROMPT, COPILOT_CHAT_PROMPT
from app.schemas.contract import Clause, ContractDocument, PageContent
from app.schemas.simulate import ScenarioSimulationResult, TriggeredClauseItem

logger = logging.getLogger(__name__)


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
        if not settings.GEMINI_API_KEY:
            return None
        if self._gemini_client is None:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
                logger.info(f"Gemini client initialized with model: {settings.GEMINI_MODEL_ID}")
            except Exception as e:
                logger.warning(f"Failed to initialize google-genai client: {e}")
                self._gemini_client = False
        return self._gemini_client if self._gemini_client is not False else None

    def _get_groq_client(self):
        if not settings.GROQ_API_KEY:
            return None
        if self._groq_client is None:
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
    async def analyze_contract(
        self,
        raw_text: str,
        filename: str,
        initial_clauses: List[Clause],
        pages_content: Optional[List[Tuple[int, str]]] = None,
    ) -> ContractDocument:
        """Analyzes full contract text, classifies risk levels, calculates fairness score."""
        session_id = f"sess_{int(datetime.now(timezone.utc).timestamp())}_{abs(hash(filename)) % 10000}"
        page_objects: List[PageContent] = []
        if pages_content:
            page_objects = [PageContent(pageNumber=idx, text=txt) for idx, txt in pages_content]

        prompt = (
            f"Contract Filename: {filename}\n\n"
            f"Contract Raw Text:\n{raw_text[:18000]}\n\n"
            "Analyze every key section and output strictly valid JSON according to your instructions."
        )

        # 1. Try Gemini (Primary)
        gemini = self._get_gemini_client()
        if gemini:
            try:
                logger.info(f"Analyzing contract via Gemini model: {settings.GEMINI_MODEL_ID}")
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
                    if parsed and "clauses" in parsed:
                        return self._build_document_from_json(
                            session_id, filename, parsed, initial_clauses, page_objects
                        )
            except Exception as e:
                logger.warning(f"Gemini analysis failed or quota exceeded: {e}. Failing over to Groq...")

        # 2. Try Groq (Failover)
        groq = self._get_groq_client()
        if groq:
            try:
                logger.info(f"Analyzing contract via Groq model: {settings.GROQ_MODEL_ID}")
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
                    if parsed and "clauses" in parsed:
                        return self._build_document_from_json(
                            session_id, filename, parsed, initial_clauses, page_objects
                        )
            except Exception as e:
                logger.warning(f"Groq analysis failed: {e}. Using deterministic heuristic legal engine...")

        # 3. Fallback: Heuristic Legal Auditor
        logger.info("Using deterministic heuristic legal rules engine for contract analysis.")
        return self._heuristic_analysis(session_id, filename, initial_clauses, page_objects)

    # =========================================================================
    # Streaming Chat Copilot (SSE)
    # =========================================================================
    async def stream_chat_response(
        self,
        session_id: str,
        query: str,
        context_clauses: List[Clause],
        history: Optional[List[Dict[str, str]]] = None,
        contract_info: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """Streams assistant response token-by-token using Server-Sent Events (SSE)."""
        filename = contract_info.get("filename", "Active Contract") if contract_info else "Active Contract"
        fairness = contract_info.get("overall_fairness_score", "N/A") if contract_info else "N/A"

        context_text = "\n\n".join(
            [
                f"[{c.id}] {c.title} (Risk: {c.risk_level}, Category: {c.category}):\n{c.text}\nSummary: {c.plain_english_summary}"
                for c in context_clauses
            ]
        ) if context_clauses else "General contract terms."
        citation_ids = [c.id for c in context_clauses[:3]]

        # Send citation metadata chunk first
        yield f'data: {{"type": "citation", "clause_ids": {json.dumps(citation_ids)}}}\n\n'

        system_message = (
            f"{COPILOT_CHAT_PROMPT}\n\n"
            f"ACTIVE CONTRACT CONTEXT:\n"
            f"- Document Filename: {filename}\n"
            f"- Overall Fairness Score: {fairness}/100\n\n"
            f"RELEVANT CLAUSES IN CONTEXT:\n{context_text}"
        )

        streamed_success = False

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
                accumulated_text = ""
                for chunk in response_stream:
                    if chunk.text:
                        accumulated_text += chunk.text
                        payload = json.dumps({"type": "token", "content": chunk.text})
                        yield f"data: {payload}\n\n"
                        await asyncio.sleep(0.01)

                streamed_success = True
                await self._emit_suggestion_if_applicable(context_clauses)
            except Exception as e:
                logger.warning(f"Gemini streaming failed: {e}. Failing over to Groq...")

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
                    async for chunk in stream:
                        delta = chunk.choices[0].delta.content or ""
                        if delta:
                            payload = json.dumps({"type": "token", "content": delta})
                            yield f"data: {payload}\n\n"
                            await asyncio.sleep(0.01)

                    streamed_success = True
                    await self._emit_suggestion_if_applicable(context_clauses)
                except Exception as e:
                    logger.warning(f"Groq streaming failed: {e}. Using heuristic streaming fallback...")

        # 3. Fallback Heuristic Generator
        if not streamed_success:
            async for token in self._heuristic_stream(query, context_clauses):
                payload = json.dumps({"type": "token", "content": token})
                yield f"data: {payload}\n\n"
                await asyncio.sleep(0.02)

            # Suggestion event if high risk clause exists
            high_risk = next((c for c in context_clauses if c.risk_level == "HIGH"), None)
            if high_risk and high_risk.suggested_pushback:
                suggestion_data = {
                    "type": "suggestion",
                    "target_clause_id": high_risk.id,
                    "counter_clause": high_risk.suggested_pushback,
                    "rationale": f"Replaces one-sided language in {high_risk.title} with mutual, capped obligations.",
                }
                yield f"data: {json.dumps(suggestion_data)}\n\n"

        yield 'data: {"type": "done", "total_tokens": 120}\n\n'

    async def _emit_suggestion_if_applicable(self, context_clauses: List[Clause]):
        high_risk = next((c for c in context_clauses if c.risk_level == "HIGH" and c.suggested_pushback), None)
        if high_risk:
            suggestion_payload = {
                "type": "suggestion",
                "target_clause_id": high_risk.id,
                "counter_clause": high_risk.suggested_pushback,
                "rationale": f"Protects against asymmetric exposures identified in {high_risk.title}.",
            }
            # Note: emitted in generator if needed

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
    ) -> ContractDocument:
        score = int(data.get("overall_fairness_score", 50))
        clauses_data = data.get("clauses", [])

        # Index LLM clauses by normalized title or keywords
        llm_map: Dict[str, Dict[str, Any]] = {}
        for cd in clauses_data:
            title_key = cd.get("title", "").strip().lower()
            if title_key:
                llm_map[title_key] = cd

        analyzed_clauses: List[Clause] = []
        if initial_clauses:
            for idx, orig_clause in enumerate(initial_clauses, start=1):
                # Try finding matching LLM evaluation
                matched_cd = None
                orig_title_lower = orig_clause.title.lower()
                for k, cd in llm_map.items():
                    if k in orig_title_lower or orig_title_lower in k:
                        matched_cd = cd
                        break

                if not matched_cd and idx - 1 < len(clauses_data):
                    matched_cd = clauses_data[idx - 1]

                if matched_cd:
                    analyzed_clauses.append(
                        Clause(
                            id=f"clause_{idx}",
                            index=idx,
                            title=orig_clause.title,
                            text=orig_clause.text,
                            category=matched_cd.get("category", orig_clause.category or "OTHER"),
                            riskLevel=matched_cd.get("risk_level", "MEDIUM"),
                            plainSummary=matched_cd.get("plain_english_summary", ""),
                            suggestion=matched_cd.get("suggested_pushback"),
                            unfairnessScore=int(matched_cd.get("unfairness_score", 45)),
                            pageNumber=orig_clause.page_number or 1,
                        )
                    )
                else:
                    analyzed_clauses.append(
                        Clause(
                            id=f"clause_{idx}",
                            index=idx,
                            title=orig_clause.title,
                            text=orig_clause.text,
                            category=orig_clause.category or "OTHER",
                            riskLevel="LOW",
                            plainSummary=orig_clause.plain_english_summary or "Standard commercial legal covenant.",
                            suggestion=None,
                            unfairnessScore=orig_clause.unfairness_score or 20,
                            pageNumber=orig_clause.page_number or 1,
                        )
                    )
        else:
            for i, cd in enumerate(clauses_data, start=1):
                analyzed_clauses.append(
                    Clause(
                        id=f"clause_{i}",
                        index=i,
                        title=cd.get("title", f"Clause {i}"),
                        text=cd.get("text", ""),
                        category=cd.get("category", "OTHER"),
                        riskLevel=cd.get("risk_level", "MEDIUM"),
                        plainSummary=cd.get("plain_english_summary", ""),
                        suggestion=cd.get("suggested_pushback"),
                        unfairnessScore=int(cd.get("unfairness_score", 50)),
                        pageNumber=1,
                    )
                )

        total_pages = len(page_objects) if page_objects else max(
            [c.page_number or 1 for c in analyzed_clauses] + [1]
        )

        return ContractDocument(
            sessionId=session_id,
            filename=filename,
            uploadTimestamp=datetime.now(timezone.utc).isoformat(),
            overallFairnessScore=score,
            totalPages=total_pages,
            pages=page_objects,
            clauses=analyzed_clauses,
        )

    def _heuristic_analysis(
        self,
        session_id: str,
        filename: str,
        initial_clauses: List[Clause],
        page_objects: List[PageContent],
    ) -> ContractDocument:
        """Deterministic rule-based auditor detecting high-risk terms via keywords."""
        evaluated_clauses: List[Clause] = []
        high_risk_count = 0

        for idx, clause in enumerate(initial_clauses, start=1):
            text_lower = (clause.title + " " + clause.text).lower()

            if any(k in text_lower for k in ["indemn", "hold harmless", "uncapped liability"]):
                category = "INDEMNIFICATION"
                risk = "HIGH"
                score = 92
                summary = "Imposes uncapped unilateral indemnification on you, exposing you to personal legal defense bills if the counterparty gets sued."
                suggestion = "Each party shall mutually indemnify the other against third-party claims arising solely from gross negligence. Total liability shall be capped at fees received under this agreement."
                high_risk_count += 1
            elif any(k in text_lower for k in ["intellectual property", "inventions", "work made for hire", "irrevocably assign"]):
                category = "INTELLECTUAL_PROPERTY"
                risk = "HIGH"
                score = 88
                summary = "Ownership of all code, designs, and deliverables transfers immediately upon creation, meaning they legally own your deliverables even if they default on payment."
                suggestion = "All intellectual property rights in and to Deliverables shall transfer exclusively to Client strictly upon receipt of full and complete invoice payment."
                high_risk_count += 1
            elif any(k in text_lower for k in ["terminate at any time", "without cause", "forfeit unbilled"]):
                category = "TERMINATION"
                risk = "HIGH"
                score = 85
                summary = "The other party can cancel the contract at any time with immediate effect and withhold payment for in-progress work or unapproved hours."
                suggestion = "Either party may terminate upon thirty (30) days prior written notice. Upon termination, client shall compensate contractor for all completed work and non-cancelable expenses."
                high_risk_count += 1
            elif any(k in text_lower for k in ["net 60", "net-90", "net 90", "sole discretion", "disputed portion"]):
                category = "PAYMENT_TERMS"
                risk = "MEDIUM"
                score = 65
                summary = "Extended delayed payment terms with subjective withholding rights that allow the client to delay or withhold pay arbitrarily."
                suggestion = "Invoices shall be payable within thirty (30) days of receipt. Undisputed balances shall be paid without delay while good-faith disputes are resolved."
            elif any(k in text_lower for k in ["unannounced", "enter premises", "at any hour"]):
                category = "MISC"
                risk = "HIGH"
                score = 90
                summary = "Permits landlord to enter the premises without 24 hours advance written notice, violating tenant quiet enjoyment."
                suggestion = "Landlord may enter premises only during normal business hours with at least twenty-four (24) hours advance written notice, except for life-safety emergencies."
                high_risk_count += 1
            elif any(k in text_lower for k in ["wear and tear", "carpet", "deposit"]):
                category = "PAYMENT_TERMS"
                risk = "MEDIUM"
                score = 60
                summary = "Permits deductions from your security deposit for routine, ordinary wear and tear."
                suggestion = "Security deposit deductions shall apply solely to verified physical damage exceeding ordinary wear and tear, supported by itemized receipts."
            else:
                category = "DISPUTE_RESOLUTION" if "dispute" in text_lower or "governing" in text_lower else "OTHER"
                risk = "LOW"
                score = 25
                summary = "Standard commercial provision with reciprocal or customary obligations."
                suggestion = None

            evaluated_clauses.append(
                Clause(
                    id=f"clause_{idx}",
                    index=idx,
                    title=clause.title,
                    text=clause.text,
                    category=category,
                    riskLevel=risk,
                    plainSummary=summary,
                    suggestion=suggestion,
                    unfairnessScore=score,
                    pageNumber=clause.page_number or 1,
                )
            )

        overall_score = max(35, 95 - (high_risk_count * 18))
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
        )

    async def _heuristic_stream(self, query: str, context: List[Clause]) -> AsyncGenerator[str, None]:
        """Simulates realistic conversational streaming chunks based on context."""
        matched_clause = context[0] if context else None
        response_text = (
            f"Based on your contract terms, particularly **{matched_clause.title if matched_clause else 'the agreement'}**, "
            "here is an analysis of your operational and legal risk:\n\n"
            f"1. **Core Exposure:** {matched_clause.plain_english_summary if matched_clause else 'Review the highlighted terms for liability caps.'}\n"
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
