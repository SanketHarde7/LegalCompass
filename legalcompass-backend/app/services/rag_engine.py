import os
import re
import numpy as np
from typing import Dict, List, Optional
from app.schemas.contract import Clause
from app.core.config import settings
import logging

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
os.environ["HF_HUB_DISABLE_XET"] = "1"

logger = logging.getLogger(__name__)

RISK_WEIGHTS = {
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
    "NEUTRAL": 0,
}

NON_RISK_KINDS = {"DEFINITION", "HEADING", "RECITAL", "BOILERPLATE"}

# Intent detection: recognizes inquiries asking to rank, identify, or summarize highest/top/worst risks
SPECIFIC_CLAUSE_TARGET_RE = re.compile(
    r"\b(?:why\s+is|explain|what\s+does|how\s+does)\s+(?:clause|section|article|paragraph)\s+[0-9]+",
    re.IGNORECASE,
)

GLOBAL_RISK_PATTERNS = [
    re.compile(
        r"\b(?:most|highest|top|worst|biggest|greatest|major|main|key|critical|primary|severe)\b.*\b(?:risk|risks|risky|exposure|exposures|danger|dangers|trap|traps|hazard|liabilities|liability|harm|unfair|predatory|adverse)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:risk|risks|risky|exposure|danger|trap|unfairness)\b.*\b(?:rank|ranking|rankings|order|hierarchy|breakdown|summary|overview|list)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:rank|ranking|list)\b.*\b(?:risk|risks|risky|exposure|exposures|traps|clauses|provisions)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:materially\s+risky|material\s+risks?|high\s+risk\s+(?:clauses?|provisions?|terms?)|worst\s+(?:clauses?|provisions?|terms?))\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:where\s+am\s+i\s+most\s+exposed|what\s+should\s+i\s+be\s+most\s+worried\s+about|greatest\s+exposure|biggest\s+traps?|top\s+concerns?)\b",
        re.IGNORECASE,
    ),
]


def is_global_risk_query(query: str) -> bool:
    """Detects whether a user prompt has global contract-risk/ranking intent.
    Zero-hardcoded: matches generalized semantic phrasing without contract/clause specificity.
    """
    q = query.strip()
    if not q:
        return False
    if SPECIFIC_CLAUSE_TARGET_RE.search(q):
        return False
    return any(p.search(q) for p in GLOBAL_RISK_PATTERNS)


# Protective / mitigating language patterns: clauses containing these protections without unilateral traps
# should never be ranked as material risks merely because of their section/category.
RE_PROTECTIVE_MITIGATION = re.compile(
    r"\b(?:"
    r"client\s+shall\s+(?:defend|indemnify|hold\s+harmless)\s+contractor|"
    r"contractor\s+(?:shall\s+not\s+be\s+liable|has\s+no\s+liability|shall\s+have\s+no\s+(?:duty|obligation)\s+to\s+indemnify)|"
    r"except\s+(?:to\s+the\s+extent\s+caused\s+by|for)\s+(?:client|counterparty)|"
    r"solely\s+to\s+the\s+extent\s+(?:caused\s+by|arising\s+from)\s+contractor's\s+(?:gross\s+negligence|willful)|"
    r"(?:total|aggregate)\s+liability\s+(?:of\s+contractor\s+)?shall\s+(?:be\s+limited|not\s+exceed|be\s+capped)\s+to\s+(?:fees|amounts)|"
    r"capped\s+at\s+(?:total\s+fees|fees\s+received|amounts\s+paid)|"
    r"conditioned\s+upon\s+(?:full\s+)?payment|"
    r"subject\s+to\s+prior\s+written\s+notice\s+and\s+(?:opportunity|right)\s+to\s+cure"
    r")\b",
    re.IGNORECASE,
)


def is_risk_bearing_clause(c: Clause) -> bool:
    """Returns True if the clause can carry material legal/operational risk.
    Strictly excludes definitions, headings, recitals, and boilerplate.
    """
    is_rb = getattr(c, "is_risk_bearing", True)
    if is_rb is False:
        return False
    kind = (getattr(c, "clause_kind", "OPERATIVE") or "OPERATIVE").upper()
    if kind in NON_RISK_KINDS:
        return False
    return True


def is_materially_risky_clause(c: Clause) -> bool:
    """Returns True if the clause represents a genuine material risk (HIGH, or MEDIUM with substantive imbalance).
    Requirements:
    1. Must be risk-bearing (strictly excludes DEFINITION, HEADING, RECITAL, BOILERPLATE).
    2. Excludes LOW and NEUTRAL clauses unconditionally (never used as fillers to reach 5).
    3. Excludes clauses containing mitigating/protective language (caps, mutuality, client-fault carve-outs,
       notice protections, payment protections) without substantive unilateral traps.
    4. Evaluates canonical fields (risk_level, unfairness_score, risk_reasons) and substantive text.
    """
    if not is_risk_bearing_clause(c):
        return False

    r_level = (getattr(c, "risk_level", "LOW") or "LOW").upper()
    # LOW or NEUTRAL clauses are NEVER materially risky provisions
    if r_level in ("LOW", "NEUTRAL"):
        return False

    unfairness = getattr(c, "unfairness_score", 0) or 0
    if unfairness < 35:
        return False

    text = getattr(c, "text", "") or ""
    text_lower = text.lower()
    reasons = getattr(c, "risk_reasons", []) or []

    # If MEDIUM: check whether it's actually protective or predominantly mitigated
    if r_level == "MEDIUM":
        is_protective = bool(RE_PROTECTIVE_MITIGATION.search(text_lower))
        has_material_trap = any(
            k in text_lower for k in [
                "uncapped", "unlimited", "forfeit", "immediately", "without limitation",
                "at will", "sole discretion", "sole option", "discretionary audit",
                "withhold", "setoff", "non-refundable", "90 days", "without cause",
            ]
        )
        if is_protective and not has_material_trap:
            return False

        has_exposure_reasons = any(bool(str(r).strip()) for r in reasons)
        if not has_exposure_reasons and unfairness < 45:
            return False

    return True


def rank_risk_clauses(clauses: List[Clause], limit: int = 7) -> List[Clause]:
    """Filters strictly for genuine materially risky clauses (HIGH, or MEDIUM with substantive imbalance)
    and sorts by canonical severity and unfairness.
    Never includes definitions, headings, recitals, non-risk-bearing boilerplate, or LOW/NEUTRAL clauses.
    Never pads or fills slots with LOW/NEUTRAL clauses just to reach the requested limit.
    """
    material_risks = [c for c in clauses if is_materially_risky_clause(c)]

    def sort_key(c: Clause):
        r_level = (getattr(c, "risk_level", "LOW") or "LOW").upper()
        weight = RISK_WEIGHTS.get(r_level, 0)
        unfairness = getattr(c, "unfairness_score", 0) or 0
        reasons_count = len(getattr(c, "risk_reasons", []) or [])
        return (weight, unfairness, reasons_count)

    ranked = sorted(material_risks, key=sort_key, reverse=True)
    return ranked[:limit]


class SessionIndex:
    def __init__(
        self,
        session_id: str,
        filename: str,
        clauses: List[Clause],
        embeddings: np.ndarray,
        overall_fairness_score: int = 50,
    ):
        self.session_id = session_id
        self.filename = filename
        self.clauses = clauses
        self.overall_fairness_score = overall_fairness_score
        self.texts = [f"{c.title}: {c.text}" for c in clauses]
        self.embeddings = embeddings  # Shape: (N, D), assumed L2-normalized


class RAGEngine:
    """Local, in-memory RAG system using FastEmbed BGE-small-en-v1.5 and cosine similarity."""

    def __init__(self):
        self.sessions: Dict[str, SessionIndex] = {}
        self._embedder = None
        self._embedder_failed = False

    def _get_embedder(self):
        """Lazy-loads FastEmbed ONNX embedding model."""
        if self._embedder is None and not self._embedder_failed:
            try:
                from fastembed import TextEmbedding
                logger.info(f"Loading FastEmbed model: {settings.EMBEDDING_MODEL}")
                self._embedder = TextEmbedding(model_name=settings.EMBEDDING_MODEL, max_workers=1)
                logger.info("FastEmbed embedding model loaded successfully.")
            except Exception as e:
                logger.warning(f"FastEmbed failed to initialize: {e}. Falling back to TF-IDF bag-of-words vectors.")
                self._embedder_failed = True
        return self._embedder

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Embeds a list of texts into normalized numpy vectors."""
        embedder = self._get_embedder()
        if embedder:
            try:
                raw_embeds = list(embedder.embed(texts))
                matrix = np.array(raw_embeds, dtype=np.float32)
                # Normalize for cosine similarity via dot product
                norms = np.linalg.norm(matrix, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                return matrix / norms
            except Exception as e:
                logger.error(f"Embedding generation error: {e}. Using fallback vectorizer.")

        # Lightweight TF-IDF / character-word hash fallback
        return self._fallback_embed(texts)

    def _fallback_embed(self, texts: List[str], dim: int = 384) -> np.ndarray:
        """Deterministic, zero-dependency embedding fallback for offline or memory-restricted environments."""
        matrix = np.zeros((len(texts), dim), dtype=np.float32)
        for i, text in enumerate(texts):
            words = text.lower().split()
            for w in words:
                idx = hash(w) % dim
                matrix[i, idx] += 1.0
            norm = np.linalg.norm(matrix[i])
            if norm > 0:
                matrix[i] /= norm
        return matrix

    def index_document(
        self,
        session_id: str,
        filename: str,
        clauses: List[Clause],
        overall_fairness_score: int = 50,
    ) -> SessionIndex:
        """Embeds and indexes all document clauses into the session memory."""
        chunk_texts = [f"{c.title}\n{c.text}\n{c.plain_english_summary}" for c in clauses]
        if not chunk_texts:
            chunk_texts = ["No clauses extracted."]

        embeddings = self.embed_texts(chunk_texts)
        session_idx = SessionIndex(
            session_id=session_id,
            filename=filename,
            clauses=clauses,
            embeddings=embeddings,
            overall_fairness_score=overall_fairness_score,
        )
        self.sessions[session_id] = session_idx
        return session_idx

    def retrieve_top_k(self, session_id: str, query: str, k: int = 4) -> List[Clause]:
        """Retrieves top-k most relevant clauses using cosine similarity (np.dot)."""
        session = self.sessions.get(session_id)
        if not session or not session.clauses:
            return []

        # If document has fewer clauses than k, return all
        if len(session.clauses) <= k:
            return session.clauses

        query_vec = self.embed_texts([query])[0]  # Shape: (D,)
        scores = np.dot(session.embeddings, query_vec)  # Cosine similarity
        top_indices = np.argsort(scores)[::-1][:k]

        return [session.clauses[i] for i in top_indices]

    def retrieve_chat_context(
        self,
        session_id: str,
        query: str,
        selected_clause_id: Optional[str] = None,
        k: int = 7,
    ) -> List[Clause]:
        """Builds contextual clauses for the chat copilot.
        If the query has global risk ranking intent, prioritize canonical risk-bearing clauses
        (ranked by risk_level + unfairness_score) plus semantic RAG coverage.
        Otherwise, uses standard focused RAG retrieval with selected clause and neighbors.
        """
        session = self.sessions.get(session_id)
        if not session or not session.clauses:
            return []

        all_clauses = session.clauses

        if is_global_risk_query(query):
            # 1. Candidate pool: only genuinely materially risky clauses (HIGH or MEDIUM with substantive imbalance)
            material_risks = [c for c in all_clauses if is_materially_risky_clause(c)]
            if not material_risks:
                return []

            # 2. Semantic RAG coverage for query, filtering strictly to material risks
            top_rag = self.retrieve_top_k(session_id, query, k=max(k, 5))
            rag_ids = {c.id for c in top_rag if is_materially_risky_clause(c)}

            # 3. Rank materially risky clauses:
            # Primary: risk_level (HIGH: 3 > MEDIUM: 2)
            # Secondary: unfairness_score descending
            # Tertiary: semantic RAG match boost
            # Quaternary: risk_reasons count
            def risk_sort_key(c: Clause):
                r_level = (getattr(c, "risk_level", "LOW") or "LOW").upper()
                weight = RISK_WEIGHTS.get(r_level, 0)
                unfairness = getattr(c, "unfairness_score", 0) or 0
                in_rag = 1 if c.id in rag_ids else 0
                reasons_count = len(getattr(c, "risk_reasons", []) or [])
                return (weight, unfairness, in_rag, reasons_count)

            ranked = sorted(material_risks, key=risk_sort_key, reverse=True)
            return ranked[:k]

        # Standard RAG behavior for specific clause / scenario inquiries
        context_clauses: List[Clause] = []
        if selected_clause_id:
            selected_idx = next((i for i, c in enumerate(all_clauses) if c.id == selected_clause_id), None)
            if selected_idx is not None:
                context_clauses.append(all_clauses[selected_idx])
                if selected_idx > 0 and all_clauses[selected_idx - 1] not in context_clauses:
                    context_clauses.append(all_clauses[selected_idx - 1])
                if selected_idx + 1 < len(all_clauses) and all_clauses[selected_idx + 1] not in context_clauses:
                    context_clauses.append(all_clauses[selected_idx + 1])

        top_k = self.retrieve_top_k(session_id, query, k=k)
        for c in top_k:
            if c not in context_clauses:
                context_clauses.append(c)

        return context_clauses

    def get_session(self, session_id: str) -> Optional[SessionIndex]:
        return self.sessions.get(session_id)


rag_engine = RAGEngine()
