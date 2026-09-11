"""
CodeSentinel RAG Module: Embedding Pipeline.

Model Selection:
`all-MiniLM-L6-v2` (384-dimensional dense vector embeddings).
Rationale:
1. High Semantic Quality: Finetuned on over 1B sentence pairs, exceptionally strong on
   both structured prose (requirements, docstrings) and tokenized code identifiers.
2. Computational Efficiency: 384 dimensions allow fast vector indexing and cosine distance
   scans in Qdrant with minimal latency and memory overhead.
3. Fast Cold Start: Ideal for lightweight microservice deployment.

Includes deterministic fallback vector generation for test mode and offline environments.
"""

import hashlib
import math
from typing import List, Union
import numpy as np

from app.core.logging import logger

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None


class EmbeddingPipeline:
    """Computes dense vector representations for text and code chunks."""

    VECTOR_DIMENSION = 384
    DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        self.model_name = model_name
        self._model = None
        self._initialized = False

    def initialize(self) -> None:
        """Lazy load the sentence-transformers model if available."""
        if self._initialized:
            return

        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                logger.info(f"Loading embedding model '{self.model_name}'...")
                self._model = SentenceTransformer(self.model_name)
                self._initialized = True
                logger.info(f"Embedding model '{self.model_name}' initialized successfully.")
                return
            except Exception as e:
                logger.warning(f"Could not load SentenceTransformer model ({e}). Using deterministic fallback.")
        
        self._initialized = True

    def _deterministic_embed(self, text: str) -> List[float]:
        """
        Generate a high-quality, deterministic 384-dimensional normalized vector
        from token n-grams and hashing for test and offline execution.
        """
        if not text:
            vec = np.zeros(self.VECTOR_DIMENSION, dtype=np.float32)
            vec[0] = 1.0
            return vec.tolist()

        vector = np.zeros(self.VECTOR_DIMENSION, dtype=np.float32)
        words = text.lower().split()
        for idx, word in enumerate(words):
            # Compute hash bucket and pseudo-random weight
            h = hashlib.sha256(f"{word}_{idx % 7}".encode("utf-8")).digest()
            bucket = int.from_bytes(h[:4], "big") % self.VECTOR_DIMENSION
            val = ((h[4] / 255.0) * 2.0) - 1.0
            vector[bucket] += float(val)

        # Normalize to unit sphere for cosine similarity
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        else:
            vector[0] = 1.0

        return vector.tolist()

    def embed_query(self, query: str) -> List[float]:
        """Embed a single query string."""
        self.initialize()
        if self._model is not None:
            try:
                emb = self._model.encode(query, convert_to_numpy=True, normalize_embeddings=True)
                return emb.tolist()
            except Exception as e:
                logger.warning(f"Embedding query failed with model ({e}), falling back: {query[:50]}")
        return self._deterministic_embed(query)

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """Batch embed a list of documents."""
        self.initialize()
        if not documents:
            return []

        if self._model is not None:
            try:
                embeddings = self._model.encode(
                    documents,
                    batch_size=32,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                )
                return [emb.tolist() for emb in embeddings]
            except Exception as e:
                logger.warning(f"Batch embedding failed ({e}), using fallback.")

        return [self._deterministic_embed(doc) for doc in documents]


# Global singleton instance
embedding_pipeline = EmbeddingPipeline()
