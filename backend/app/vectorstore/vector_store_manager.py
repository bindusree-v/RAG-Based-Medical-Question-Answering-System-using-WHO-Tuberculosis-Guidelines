"""
MediRAG AI – Vector Store Manager
Handles embedding generation and indexing of document chunks.
"""

from functools import lru_cache
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import Document, DocumentChunk, ProcessingStatus
from app.utils.logger import logger
from app.vectorstore.chroma_store import ChromaVectorStore
from app.vectorstore.faiss_store import FAISSVectorStore


class VectorStoreManager:
    """
    Bridges the SQL document chunks table and the configured vector store.
    Supports ChromaDB (default) or FAISS (set VECTOR_STORE_TYPE=faiss).
    """

    def __init__(self):
        if settings.vector_store_type.lower() == "faiss":
            logger.info("Using FAISS vector store.")
            self._store = FAISSVectorStore()
        else:
            logger.info("Using ChromaDB vector store.")
            self._store = ChromaVectorStore()

    def get_store(self) -> ChromaVectorStore:
        return self._store

    async def index_document(self, document_id: str, db: AsyncSession) -> int:
        """
        Fetch all chunks for a document and add them to the vector store.
        Returns the number of chunks indexed.
        """
        # Fetch document
        doc_result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = doc_result.scalar_one_or_none()
        if not doc:
            logger.error(f"Document {document_id} not found.")
            return 0

        # Fetch chunks
        chunks_result = await db.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        chunks = chunks_result.scalars().all()

        if not chunks:
            logger.warning(f"No chunks found for document {document_id}")
            return 0

        texts = [chunk.content for chunk in chunks]
        metadatas = [
            {
                "document_id": document_id,
                "chunk_id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "filename": doc.original_filename,
                "category": doc.category.value if doc.category else "unknown",
                "medical_specialty": doc.medical_specialty or "unknown",
                "page_number": chunk.page_number or 0,
                "section": chunk.section or "unknown",
                "source": doc.source or doc.original_filename,
                "title": doc.title or doc.original_filename,
            }
            for chunk in chunks
        ]
        ids = [f"{document_id}_{chunk.chunk_index}" for chunk in chunks]

        added_ids = self._store.add_documents(texts=texts, metadatas=metadatas, ids=ids)

        # Update embedding IDs on chunks
        for chunk, emb_id in zip(chunks, added_ids):
            chunk.embedding_id = emb_id

        # Mark document as embedded
        doc.embedding_status = True
        doc.processing_status = ProcessingStatus.INDEXED

        logger.info(
            f"Indexed {len(added_ids)} vectors for document '{doc.original_filename}'"
        )
        return len(added_ids)

    async def remove_document(self, document_id: str, db: AsyncSession) -> None:
        """Remove all vectors for a document from the vector store."""
        self._store.delete_by_document_id(document_id)

        # Reset embedding status
        doc_result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = doc_result.scalar_one_or_none()
        if doc:
            doc.embedding_status = False
            doc.processing_status = ProcessingStatus.PENDING

    def search(self, query: str, k: int = None, filters: dict = None):
        """Proxy similarity search to the underlying store."""
        k = k or settings.top_k_results
        return self._store.similarity_search(query=query, k=k, filter_metadata=filters)

    def get_stats(self) -> dict:
        return self._store.get_collection_stats()


@lru_cache(maxsize=1)
def get_vector_store_manager() -> VectorStoreManager:
    return VectorStoreManager()
