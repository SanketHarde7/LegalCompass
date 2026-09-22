import os
import numpy as np
from typing import Dict, List, Optional
from app.schemas.contract import Clause
from app.core.config import settings
import logging

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
os.environ["HF_HUB_DISABLE_XET"] = "1"

logger = logging.getLogger(__name__)


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

    def get_session(self, session_id: str) -> Optional[SessionIndex]:
        return self.sessions.get(session_id)


rag_engine = RAGEngine()
