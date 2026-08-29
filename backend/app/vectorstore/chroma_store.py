"""
MediRAG AI – ChromaDB Vector Store
Manages persistent vector embeddings for medical document chunks.
"""

from typing import Any, Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document as LCDocument

from app.config import settings
from app.embeddings.embedding_service import get_embedding_service
from app.utils.logger import logger


COLLECTION_NAME = "medirag_medical_knowledge"


class ChromaVectorStore:
    """
    Persistent ChromaDB vector store with a single medical knowledge collection.
    """

    def __init__(self):
        self._client: Optional[chromadb.PersistentClient] = None
        self._store: Optional[Chroma] = None
        self._embedding_service = get_embedding_service()

    def _get_client(self) -> chromadb.PersistentClient:
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=settings.chroma_persist_directory,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        return self._client

    def _get_store(self) -> Chroma:
        if self._store is None:
            self._store = Chroma(
                client=self._get_client(),
                collection_name=COLLECTION_NAME,
                embedding_function=self._embedding_service.model,
            )
        return self._store

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def add_documents(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Add text chunks with metadata to the vector store.

        Returns:
            List of internal ChromaDB IDs assigned to each chunk.
        """
        if not texts:
            return []

        lc_docs = [
            LCDocument(page_content=text, metadata=meta)
            for text, meta in zip(texts, metadatas)
        ]

        store = self._get_store()
        if ids:
            added_ids = store.add_documents(lc_docs, ids=ids)
        else:
            added_ids = store.add_documents(lc_docs)

        logger.debug(f"Added {len(added_ids)} vectors to ChromaDB.")
        return added_ids

    def delete_by_document_id(self, document_id: str) -> None:
        """Remove all chunks belonging to a given document."""
        collection = self._get_client().get_collection(COLLECTION_NAME)
        # ChromaDB supports metadata-based deletion
        collection.delete(where={"document_id": document_id})
        logger.info(f"Deleted vectors for document_id={document_id}")

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[LCDocument, float]]:
        """
        Perform similarity search, returning (document, score) pairs.
        Scores are cosine similarity in [0, 1].
        """
        store = self._get_store()
        results = store.similarity_search_with_relevance_scores(
            query=query,
            k=k,
            filter=filter_metadata,
        )
        return results

    def get_collection_stats(self) -> Dict[str, Any]:
        """Return basic stats about the vector collection."""
        try:
            collection = self._get_client().get_collection(COLLECTION_NAME)
            count = collection.count()
            return {"collection": COLLECTION_NAME, "vector_count": count}
        except Exception as exc:
            logger.warning(f"Could not fetch collection stats: {exc}")
            return {"collection": COLLECTION_NAME, "vector_count": 0, "error": str(exc)}
