"""
MediRAG AI – Document Service
Business logic for document management, listing, and deletion.
"""

from typing import List, Optional
from datetime import datetime

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document, DocumentChunk, ProcessingStatus
from app.models.schemas import DocumentListResponse, DocumentMetadata, KnowledgeBaseStats
from app.vectorstore.vector_store_manager import get_vector_store_manager
from app.utils.logger import logger
import json


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._vsm = get_vector_store_manager()

    async def list_documents(
        self,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None,
        status: Optional[str] = None,
    ) -> DocumentListResponse:
        """Paginated list of documents with optional filters."""
        query = select(Document)

        if category:
            query = query.where(Document.category == category)
        if status:
            query = query.where(Document.processing_status == status)

        # Count total
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        # Paginate
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(Document.uploaded_at.desc())

        result = await self.db.execute(query)
        docs = result.scalars().all()

        return DocumentListResponse(
            total=total,
            documents=[DocumentMetadata.model_validate(d) for d in docs],
            page=page,
            page_size=page_size,
        )

    async def get_document(self, document_id: str) -> Optional[Document]:
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document and its vectors from the system."""
        doc = await self.get_document(document_id)
        if not doc:
            return False

        # Remove from vector store
        try:
            self._vsm.remove_document(document_id, self.db)
        except Exception as exc:
            logger.warning(f"Vector deletion warning for {document_id}: {exc}")

        # Delete chunks
        await self.db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )

        # Delete document record
        await self.db.delete(doc)
        logger.info(f"Document {document_id} deleted.")
        return True

    async def get_knowledge_base_stats(self) -> KnowledgeBaseStats:
        """Return aggregate knowledge base statistics."""
        total = await self.db.execute(select(func.count(Document.id)))
        indexed = await self.db.execute(
            select(func.count(Document.id)).where(
                Document.processing_status == ProcessingStatus.INDEXED
            )
        )
        pending = await self.db.execute(
            select(func.count(Document.id)).where(
                Document.processing_status == ProcessingStatus.PENDING
            )
        )
        failed = await self.db.execute(
            select(func.count(Document.id)).where(
                Document.processing_status == ProcessingStatus.FAILED
            )
        )
        total_chunks = await self.db.execute(select(func.count(DocumentChunk.id)))

        # Category breakdown
        from app.models.database import DocumentCategory
        categories = {}
        for cat in DocumentCategory:
            count = await self.db.execute(
                select(func.count(Document.id)).where(Document.category == cat)
            )
            val = count.scalar_one()
            if val > 0:
                categories[cat.value] = val

        return KnowledgeBaseStats(
            total_documents=total.scalar_one(),
            indexed_documents=indexed.scalar_one(),
            pending_documents=pending.scalar_one(),
            failed_documents=failed.scalar_one(),
            total_chunks=total_chunks.scalar_one(),
            total_queries=0,  # Could track from QueryLog table
            categories=categories,
        )

    async def index_document(self, document_id: str) -> int:
        """Trigger vector indexing for a document."""
        return await self._vsm.index_document(document_id, self.db)
