"""
MediRAG AI – Pydantic Schemas (Request / Response Models)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field, validator
import enum


# ---------------------------------------------------------------------------
# Auth Schemas
# ---------------------------------------------------------------------------

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    PHYSICIAN = "physician"
    RESEARCHER = "researcher"
    VIEWER = "viewer"


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.VIEWER


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None
    role: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


# ---------------------------------------------------------------------------
# Document Schemas
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


class ValidationResult(BaseModel):
    is_valid: bool
    status: str  # "accepted" | "rejected"
    message: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    detected_category: Optional[DocumentCategory] = None
    medical_specialty: Optional[str] = None
    rejection_reason: Optional[str] = None


class DocumentMetadata(BaseModel):
    id: str
    filename: str
    original_filename: str
    category: DocumentCategory
    medical_specialty: Optional[str] = None
    source: Optional[str] = None
    title: Optional[str] = None
    processing_status: ProcessingStatus
    embedding_status: bool
    chunk_count: int = 0
    is_validated: bool
    validation_score: Optional[float] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    file_size: Optional[int] = None

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    validation: ValidationResult
    processing_status: ProcessingStatus
    message: str


class DocumentListResponse(BaseModel):
    total: int
    documents: List[DocumentMetadata]
    page: int = 1
    page_size: int = 20


class DocumentProcessRequest(BaseModel):
    document_id: str
    force_reprocess: bool = False


# ---------------------------------------------------------------------------
# Medical Query Schemas
# ---------------------------------------------------------------------------

class SourceCitation(BaseModel):
    document_id: str
    filename: str
    title: Optional[str] = None
    category: Optional[str] = None
    medical_specialty: Optional[str] = None
    page_number: Optional[int] = None
    excerpt: str
    relevance_score: float = Field(ge=0.0, le=1.0)


class MedicalQueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)
    query_type: Optional[str] = "general"
    top_k: Optional[int] = Field(default=5, ge=1, le=20)
    filters: Optional[Dict[str, Any]] = None


class MedicalQueryResponse(BaseModel):
    query: str
    answer: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    sources: List[SourceCitation]
    agent_used: str
    response_time_ms: int
    disclaimer: str = (
        "Educational and informational use only. "
        "Not a substitute for professional clinical judgment."
    )


# ---------------------------------------------------------------------------
# Drug Interaction Schemas
# ---------------------------------------------------------------------------

class DrugInteractionRequest(BaseModel):
    drug_a: str = Field(..., min_length=1, max_length=500)
    drug_b: str = Field(..., min_length=1, max_length=500)
    additional_drugs: Optional[List[str]] = []
    patient_context: Optional[str] = None


class InteractionDetail(BaseModel):
    drugs_involved: List[str]
    interaction_type: str
    severity: str  # "major", "moderate", "minor", "contraindicated"
    mechanism: Optional[str] = None
    clinical_effects: str
    management: str
    monitoring: Optional[str] = None


class DrugInteractionResponse(BaseModel):
    drugs_queried: List[str]
    interactions_found: List[InteractionDetail]
    overall_risk_level: str
    clinical_summary: str
    monitoring_recommendations: str
    sources: List[SourceCitation]
    confidence_score: float = Field(ge=0.0, le=1.0)
    disclaimer: str = (
        "Educational and informational use only. "
        "Not a substitute for professional clinical judgment."
    )


# ---------------------------------------------------------------------------
# Symptom & Treatment Schemas
# ---------------------------------------------------------------------------

class SymptomQueryRequest(BaseModel):
    symptoms: List[str] = Field(..., min_length=1)
    patient_demographics: Optional[Dict[str, Any]] = None
    duration: Optional[str] = None
    severity: Optional[str] = None


class TreatmentProtocolRequest(BaseModel):
    condition: str = Field(..., min_length=2, max_length=500)
    patient_context: Optional[str] = None
    guideline_source: Optional[str] = None
    evidence_level: Optional[str] = None  # "A", "B", "C"


class TreatmentProtocolResponse(BaseModel):
    condition: str
    protocol_summary: str
    treatment_steps: List[str]
    first_line_treatment: Optional[str] = None
    contraindications: Optional[List[str]] = None
    monitoring_parameters: Optional[List[str]] = None
    evidence_level: Optional[str] = None
    guideline_source: Optional[str] = None
    sources: List[SourceCitation]
    confidence_score: float
    disclaimer: str = (
        "Educational and informational use only. "
        "Not a substitute for professional clinical judgment."
    )


# ---------------------------------------------------------------------------
# Health & System Schemas
# ---------------------------------------------------------------------------

class ComponentStatus(BaseModel):
    status: str  # "healthy", "degraded", "unhealthy"
    message: Optional[str] = None
    latency_ms: Optional[int] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    components: Dict[str, ComponentStatus]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeBaseStats(BaseModel):
    total_documents: int
    indexed_documents: int
    pending_documents: int
    failed_documents: int
    total_chunks: int
    total_queries: int
    categories: Dict[str, int]
