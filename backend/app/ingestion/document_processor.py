"""
MediRAG AI – Document Processing Pipeline

Full pipeline:
  Upload → Validate → Extract Text → Clean → Chunk → Embed → Store
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.ingestion.text_extractor import TextExtractor
from app.ingestion.chunker import MedicalTextChunker
from app.models.database import Document, DocumentChunk, ProcessingStatus, DocumentCategory
from app.models.schemas import DocumentUploadResponse, ValidationResult
from app.utils.file_utils import generate_unique_id, sanitize_filename, ensure_directory_exists
from app.utils.logger import logger
from app.validation.medical_validator import ValidationEngine


class DocumentProcessor:
    """
    Orchestrates the full document ingestion pipeline.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.extractor = TextExtractor()
        self.chunker = MedicalTextChunker()
        self.validator = ValidationEngine()

    async def ingest(
        self,
        file_content: bytes,
        original_filename: str,
        mime_type: str,
        uploaded_by: Optional[str] = None,
    ) -> DocumentUploadResponse:
        """
        Full ingestion pipeline entry point. Returns a DocumentUploadResponse.
        """
        doc_id = generate_unique_id()
        safe_name = sanitize_filename(original_filename)
        stored_filename = f"{doc_id}_{safe_name}"

        # ------------------------------------------------------------------
        # 1. Extract text for validation (in-memory)
        # ------------------------------------------------------------------
        try:
            full_text, pages = self.extractor.extract_from_bytes(
                file_content, original_filename
            )
        except Exception as exc:
            logger.error(f"Text extraction failed for '{original_filename}': {exc}")
            return DocumentUploadResponse(
                document_id=doc_id,
                filename=stored_filename,
                validation=ValidationResult(
                    is_valid=False,
                    status="rejected",
                    message=f"Failed to extract text from document: {exc}",
                    confidence_score=0.0,
                    rejection_reason="extraction_failure",
                ),
                processing_status=ProcessingStatus.FAILED,
                message="Document could not be processed due to extraction failure.",
            )

        # ------------------------------------------------------------------
        # 2. Validate medical domain
        # ------------------------------------------------------------------
        validation_result = self.validator.validate_document(
            text=full_text,
            filename=original_filename,
            mime_type=mime_type,
        )

        # Determine storage category
        category = (
            validation_result.detected_category or DocumentCategory.MEDICAL_PDF
            if validation_result.is_valid
            else DocumentCategory.UNKNOWN
        )

        # ------------------------------------------------------------------
        # 3. Save file to disk (even if rejected – for audit purposes)
        # ------------------------------------------------------------------
        category_dir = (
            Path(settings.upload_base_dir) / category.value
            if validation_result.is_valid
            else Path(settings.upload_base_dir) / "rejected"
        )
        ensure_directory_exists(str(category_dir))
        file_path = category_dir / stored_filename

        try:
            file_path.write_bytes(file_content)
        except Exception as exc:
            logger.error(f"Failed to save file '{stored_filename}': {exc}")

        # ------------------------------------------------------------------
        # 4. Persist Document record in DB
        # ------------------------------------------------------------------
        processing_status = (
            ProcessingStatus.PENDING if validation_result.is_valid else ProcessingStatus.REJECTED
        )

        doc_record = Document(
            id=doc_id,
            filename=stored_filename,
            original_filename=original_filename,
            file_path=str(file_path),
            file_size=len(file_content),
            mime_type=mime_type,
            category=category,
            medical_specialty=validation_result.medical_specialty,
            processing_status=processing_status,
            is_validated=validation_result.is_valid,
            validation_score=validation_result.confidence_score,
            rejection_reason=validation_result.rejection_reason,
            uploaded_by=uploaded_by,
        )
        self.db.add(doc_record)
        await self.db.flush()

        if not validation_result.is_valid:
            logger.warning(
                f"Document '{original_filename}' rejected: {validation_result.rejection_reason}"
            )
            return DocumentUploadResponse(
                document_id=doc_id,
                filename=stored_filename,
                validation=validation_result,
                processing_status=ProcessingStatus.REJECTED,
                message=validation_result.message,
            )

        # ------------------------------------------------------------------
        # 5. Process valid document: chunk and embed
        # ------------------------------------------------------------------
        await self._process_document(doc_record, full_text, pages)

        return DocumentUploadResponse(
            document_id=doc_id,
            filename=stored_filename,
            validation=validation_result,
            processing_status=doc_record.processing_status,
            message="Document successfully validated, processed, and indexed.",
        )

    async def _process_document(self, doc: Document, full_text: str, pages) -> None:
        """Chunk the document and prepare chunks for embedding."""
        doc.processing_status = ProcessingStatus.PROCESSING

        # Chunk text
        chunks = self.chunker.chunk_document(
            text=full_text,
            document_id=doc.id,
        )

        # Persist chunks
        for chunk in chunks:
            db_chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                page_number=chunk.page_number,
                section=chunk.section,
            )
            self.db.add(db_chunk)

        doc.chunk_count = len(chunks)
        doc.processing_status = ProcessingStatus.INDEXED
        doc.processed_at = datetime.utcnow()

        logger.info(
            f"Document '{doc.original_filename}' processed: "
            f"{len(chunks)} chunks created."
        )

    async def reprocess_document(self, document_id: str) -> bool:
        """Re-extract and re-chunk an already stored document."""
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            return False

        if not Path(doc.file_path).exists():
            logger.error(f"File not found on disk: {doc.file_path}")
            doc.processing_status = ProcessingStatus.FAILED
            return False

        file_content = Path(doc.file_path).read_bytes()
        full_text, pages = self.extractor.extract_from_bytes(
            file_content, doc.original_filename
        )

        # Delete existing chunks
        existing_chunks = await self.db.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        for chunk in existing_chunks.scalars():
            await self.db.delete(chunk)

        await self._process_document(doc, full_text, pages)
        return True
