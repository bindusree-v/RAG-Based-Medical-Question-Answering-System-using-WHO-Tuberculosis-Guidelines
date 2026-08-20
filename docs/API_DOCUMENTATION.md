# MediRAG AI – API Documentation

Base URL: `http://localhost:8000/api/v1`

All protected endpoints require: `Authorization: Bearer <token>`

---

## Authentication

### POST /auth/register
Register a new user account.

**Request Body:**
```json
{
  "username": "dr_smith",
  "email": "dr.smith@hospital.org",
  "password": "SecurePass123!",
  "role": "physician"
}
```

**Roles:** `admin` | `physician` | `researcher` | `viewer`

**Response 201:**
```json
{
  "id": "uuid",
  "username": "dr_smith",
  "email": "dr.smith@hospital.org",
  "role": "physician",
  "is_active": true,
  "created_at": "2024-01-15T10:00:00"
}
```

---

### POST /auth/login
Authenticate and receive JWT token. Accepts `application/x-www-form-urlencoded`.

**Request:** `username=dr_smith&password=SecurePass123!`

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

### GET /auth/me
Return currently authenticated user profile.

**Response 200:** Same as register response.

---

## Documents

### POST /documents/upload-document
Upload and ingest a medical document. `multipart/form-data`.

**Form Fields:**
- `file` (required) – PDF, DOCX, or TXT file (max 50 MB)
- `source` (optional) – Publisher/source string
- `title` (optional) – Document title

**Response 201:**
```json
{
  "document_id": "uuid",
  "filename": "uuid_guidelines.pdf",
  "validation": {
    "is_valid": true,
    "status": "accepted",
    "message": "Document validated as healthcare-related content.",
    "confidence_score": 0.87,
    "detected_category": "treatment_guidelines",
    "medical_specialty": "Cardiology"
  },
  "processing_status": "indexed",
  "message": "Document successfully validated, processed, and indexed."
}
```

**Rejection Example:**
```json
{
  "validation": {
    "is_valid": false,
    "status": "rejected",
    "message": "Only healthcare-related documents are permitted.",
    "confidence_score": 0.12,
    "rejection_reason": "non_medical_content:financial"
  },
  "processing_status": "rejected"
}
```

---

### POST /documents/validate-document
Validate without storing. `multipart/form-data`.

**Form Fields:** `file` (required)

**Response 200:** ValidationResult object (same structure as above).

---

### POST /documents/process-document
Re-trigger processing for an existing document.

**Request Body:**
```json
{
  "document_id": "uuid",
  "force_reprocess": false
}
```

**Required Role:** `admin` | `physician` | `researcher`

---

### GET /documents/documents
List documents with pagination and filters.

**Query Parameters:**
- `page` (default: 1)
- `page_size` (default: 20, max: 100)
- `category` (optional) – Filter by document category
- `status` (optional) – Filter by processing_status

**Response 200:**
```json
{
  "total": 42,
  "page": 1,
  "page_size": 20,
  "documents": [
    {
      "id": "uuid",
      "filename": "uuid_guidelines.pdf",
      "original_filename": "hypertension_guidelines.pdf",
      "category": "treatment_guidelines",
      "medical_specialty": "Cardiology",
      "processing_status": "indexed",
      "embedding_status": true,
      "chunk_count": 38,
      "is_validated": true,
      "validation_score": 0.87,
      "uploaded_at": "2024-01-15T10:00:00"
    }
  ]
}
```

---

### GET /documents/documents/{id}
Get metadata for a single document.

---

### GET /documents/sources
List only indexed (searchable) documents.

---

### GET /documents/documents/stats
Knowledge base aggregate statistics.

**Response 200:**
```json
{
  "total_documents": 42,
  "indexed_documents": 38,
  "pending_documents": 2,
  "failed_documents": 1,
  "total_chunks": 1547,
  "total_queries": 204,
  "categories": {
    "treatment_guidelines": 12,
    "research_articles": 18,
    "drug_databases": 8
  }
}
```

---

### DELETE /document/{id}
Delete a document and remove its vectors.

**Required Role:** `admin` | `physician`

**Response:** 204 No Content

---

## Medical Queries

All query endpoints return responses grounded in indexed medical literature with source citations.

### POST /query/medical-query
General evidence-based medical Q&A.

**Request Body:**
```json
{
  "query": "What are current treatment recommendations for hypertension?",
  "query_type": "general",
  "top_k": 5
}
```

**Response 200:**
```json
{
  "query": "What are current treatment recommendations for hypertension?",
  "answer": "Based on the indexed clinical guidelines, first-line treatment for hypertension includes...",
  "confidence_score": 0.82,
  "sources": [
    {
      "document_id": "uuid",
      "filename": "jnc8_guidelines.pdf",
      "title": "JNC-8 Hypertension Guidelines",
      "category": "treatment_guidelines",
      "medical_specialty": "Cardiology",
      "page_number": 12,
      "excerpt": "For the general population ≥60 years, initiate pharmacologic treatment...",
      "relevance_score": 0.91
    }
  ],
  "agent_used": "Treatment Protocol Agent",
  "response_time_ms": 3240,
  "disclaimer": "Educational and informational use only. Not a substitute for professional clinical judgment."
}
```

---

### POST /query/drug-interaction
Analyze drug-drug interactions.

**Request Body:**
```json
{
  "drug_a": "Warfarin",
  "drug_b": "Aspirin",
  "additional_drugs": [],
  "patient_context": "65-year-old with atrial fibrillation"
}
```

**Response 200:**
```json
{
  "drugs_queried": ["Warfarin", "Aspirin"],
  "interactions_found": [
    {
      "drugs_involved": ["Warfarin", "Aspirin"],
      "interaction_type": "Pharmacodynamic",
      "severity": "Major",
      "mechanism": "Additive anticoagulation and antiplatelet effects",
      "clinical_effects": "Significantly increased risk of bleeding...",
      "management": "Avoid combination unless benefit clearly outweighs risk...",
      "monitoring": "Monitor INR, signs of bleeding"
    }
  ],
  "overall_risk_level": "Major",
  "clinical_summary": "...",
  "monitoring_recommendations": "INR monitoring every 2-4 weeks...",
  "sources": [...],
  "confidence_score": 0.79,
  "disclaimer": "..."
}
```

---

### POST /query/symptom-query
Retrieve clinical knowledge from presenting symptoms.

**Request Body:**
```json
{
  "symptoms": ["chest pain", "dyspnea", "diaphoresis"],
  "patient_demographics": {"age": 58, "gender": "male"},
  "duration": "2 hours",
  "severity": "severe"
}
```

**Response 200:** MedicalQueryResponse (same structure as /medical-query)

---

### POST /query/treatment-protocol
Retrieve evidence-based treatment protocols.

**Request Body:**
```json
{
  "condition": "Community-Acquired Pneumonia",
  "guideline_source": "IDSA",
  "evidence_level": "A"
}
```

**Response 200:**
```json
{
  "condition": "Community-Acquired Pneumonia",
  "protocol_summary": "...",
  "treatment_steps": [
    "1. Assess severity using CURB-65 or PSI score",
    "2. Outpatient (low risk): Amoxicillin 1g TID or Doxycycline 100mg BID",
    "..."
  ],
  "first_line_treatment": "Amoxicillin 1g three times daily for 5 days",
  "contraindications": ["Beta-lactam allergy"],
  "monitoring_parameters": ["Temperature", "Oxygen saturation", "WBC"],
  "evidence_level": "A",
  "sources": [...],
  "confidence_score": 0.88,
  "disclaimer": "..."
}
```

---

## System

### GET /health
System health check (no authentication required).

**Response 200:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "components": {
    "database": {"status": "healthy", "latency_ms": 2},
    "vector_store": {"status": "healthy", "message": "Vectors: 1547", "latency_ms": 5},
    "llm": {"status": "healthy", "message": "Model 'llama3' available", "latency_ms": 48}
  },
  "timestamp": "2024-01-15T10:30:00"
}
```

---

## Error Responses

All errors follow RFC 7807 format:

```json
{
  "detail": "Human-readable error message"
}
```

| Status | Meaning |
|---|---|
| 400 | Bad Request – invalid input |
| 401 | Unauthorized – missing or invalid token |
| 403 | Forbidden – insufficient role |
| 404 | Not Found – resource does not exist |
| 409 | Conflict – duplicate resource |
| 413 | Payload Too Large – file exceeds 50 MB |
| 422 | Unprocessable Entity – validation error |
| 429 | Too Many Requests – rate limit exceeded |
| 500 | Internal Server Error |
