"""
MediRAG AI – Document Management API Routes

POST /upload-document
POST /validate-document
POST /process-document
GET  /documents
GET  /sources
DELETE /document/{id}
"""

from typing import Optional

from fastapi import (
    APIRouter, Depends, File, Form, HTTPException,
    Query, Request, UploadFile, status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.ingestion.document_processor import DocumentProcessor
from app.models.database import get_db, User
from app.models.schemas import (
    DocumentListResponse, DocumentMetadata, DocumentUploadResponse,
    DocumentProcessRequest, ValidationResult, KnowledgeBaseStats,
)
from app.services.document_service import DocumentService
from app.utils.security import get_current_user, require_role
from app.validation.medical_validator import ValidationEngine
from app.utils.logger import logger

router = APIRouter()
_validator = ValidationEngine()


@router.post("/upload-document", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    source: Optional[str] = Form(default=None),
    title: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload and ingest a medical document.
    Triggers validation → extraction → chunking → indexing pipeline.
    """
    # File size guard
    content = await file.read()
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.max_file_size_mb} MB.",
        )

    processor = DocumentProcessor(db)
    result = await processor.ingest(
        file_content=content,
        original_filename=file.filename,
        mime_type=file.content_type or "application/octet-stream",
        uploaded_by=current_user.id,
    )

    # If accepted, kick off vector indexing
    if result.validation.is_valid:
        doc_service = DocumentService(db)
        await doc_service.index_document(result.document_id)

    return result


@router.post("/validate-document", response_model=ValidationResult)
async def validate_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Validate a document without storing it.
    Returns validation result only – no ingestion occurs.
    """
    content = await file.read()
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large for validation.",
        )

    # Extract text in-memory
    from app.ingestion.text_extractor import TextExtractor
    extractor = TextExtractor()
    try:
        full_text, _ = extractor.extract_from_bytes(content, file.filename)
    except Exception as exc:
        return ValidationResult(
            is_valid=False,
            status="rejected",
            message=f"Text extraction failed: {exc}",
            confidence_score=0.0,
            rejection_reason="extraction_failure",
        )

    return _validator.validate_document(
        text=full_text,
        filename=file.filename,
        mime_type=file.content_type,
    )


@router.post("/process-document")
async def process_document(
    req: DocumentProcessRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "physician", "researcher")),
):
    """Trigger or re-trigger processing and indexing for an existing document."""
    processor = DocumentProcessor(db)
    success = await processor.reprocess_document(req.document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {req.document_id} not found.",
        )
    return {"message": "Document reprocessed successfully.", "document_id": req.document_id}


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all documents with pagination and optional filters."""
    service = DocumentService(db)
    return await service.list_documents(
        page=page,
        page_size=page_size,
        category=category,
        status=status,
    )


@router.get("/sources", response_model=DocumentListResponse)
async def list_sources(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all indexed (available) medical sources."""
    service = DocumentService(db)
    return await service.list_documents(
        page=page,
        page_size=page_size,
        status="indexed",
    )


@router.get("/documents/stats", response_model=KnowledgeBaseStats)
async def knowledge_base_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return aggregate knowledge base statistics."""
    service = DocumentService(db)
    return await service.get_knowledge_base_stats()


@router.get("/documents/{document_id}", response_model=DocumentMetadata)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get metadata for a specific document."""
    service = DocumentService(db)
    doc = await service.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )
    return DocumentMetadata.model_validate(doc)


@router.delete("/document/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "physician")),
):
    """Delete a document and remove its vectors from the knowledge base."""
    service = DocumentService(db)
    success = await service.delete_document(document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )
