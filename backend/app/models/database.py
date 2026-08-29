"""
MediRAG AI – Database Models (SQLAlchemy ORM)
Defines all persistent data models for documents, users, and audit logs.
"""

from datetime import datetime
from typing import AsyncGenerator
import uuid

from sqlalchemy import (
    Column, String, DateTime, Boolean, Text, Float,
    Integer, ForeignKey, Enum as SAEnum
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
import enum

from app.config import settings


# ---------------------------------------------------------------------------
# Engine & Session Factory
# ---------------------------------------------------------------------------

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DocumentCategory(str, enum.Enum):
    MEDICAL_PDF = "medical_pdfs"
    TREATMENT_GUIDELINE = "treatment_guidelines"
    DRUG_DATABASE = "drug_databases"
    RESEARCH_ARTICLE = "research_articles"
    MEDICAL_BOOK = "medical_books"
    CLINICAL_PROTOCOL = "clinical_protocols"
    UNKNOWN = "unknown"


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    REJECTED = "rejected"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    PHYSICIAN = "physician"
    RESEARCHER = "researcher"
    VIEWER = "viewer"


# ---------------------------------------------------------------------------
# Database Models
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)

    documents = relationship("Document", back_populates="uploaded_by_user")
    audit_logs = relationship("AuditLog", back_populates="user")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(200), nullable=True)

    # Classification
    category = Column(
        SAEnum(DocumentCategory),
        default=DocumentCategory.UNKNOWN,
        nullable=False
    )
    medical_specialty = Column(String(200), nullable=True)
    source = Column(String(500), nullable=True)
    title = Column(String(1000), nullable=True)
    authors = Column(Text, nullable=True)
    publication_year = Column(Integer, nullable=True)

    # Processing
    processing_status = Column(
        SAEnum(ProcessingStatus),
        default=ProcessingStatus.PENDING,
        nullable=False
    )
    embedding_status = Column(Boolean, default=False, nullable=False)
    chunk_count = Column(Integer, default=0, nullable=True)
    version = Column(Integer, default=1, nullable=False)

    # Validation
    is_validated = Column(Boolean, default=False, nullable=False)
    validation_score = Column(Float, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Metadata
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=True)

    uploaded_by_user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding_id = Column(String(500), nullable=True)  # ID in vector store
    page_number = Column(Integer, nullable=True)
    section = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    document = relationship("Document", back_populates="chunks")


class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    query_type = Column(String(100), nullable=False)  # medical_query, drug_interaction, etc.
    query_text = Column(Text, nullable=False)
    response_summary = Column(Text, nullable=True)
    sources_used = Column(Text, nullable=True)  # JSON list of document IDs
    confidence_score = Column(Float, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action = Column(String(200), nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(36), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="audit_logs")


# ---------------------------------------------------------------------------
# Dependencies & Helpers
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yield an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
