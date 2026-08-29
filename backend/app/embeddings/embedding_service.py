"""
MediRAG AI – Embedding Service
Uses BAAI/bge-small-en-v1.5 via sentence-transformers for local inference.
"""

from functools import lru_cache
from typing import List

from langchain_community.embeddings import HuggingFaceEmbeddings

from app.config import settings
from app.utils.logger import logger


class EmbeddingService:
    """
    Wrapper around HuggingFace sentence-transformer embeddings.
    Provides a consistent interface for the vector store layer.
    """

    def __init__(self):
        self._embeddings: HuggingFaceEmbeddings = None

    def _load(self) -> HuggingFaceEmbeddings:
        """Lazy-load the embedding model (only once)."""
        if self._embeddings is None:
            logger.info(
                f"Loading embedding model '{settings.embedding_model}' "
                f"on device '{settings.embedding_device}'"
            )
            self._embeddings = HuggingFaceEmbeddings(
                model_name=settings.embedding_model,
                model_kwargs={"device": settings.embedding_device},
                encode_kwargs={
                    "normalize_embeddings": True,  # BGE models benefit from normalization
                    "batch_size": 32,
                },
            )
            logger.info("Embedding model loaded successfully.")
        return self._embeddings

    @property
    def model(self) -> HuggingFaceEmbeddings:
        return self._load()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of text strings."""
        if not texts:
            return []
        return self.model.embed_documents(texts)

    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a single query string."""
        return self.model.embed_query(query)


# Singleton instance
@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
