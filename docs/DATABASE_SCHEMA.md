# MediRAG AI – Database Schema

## Entity Relationship Overview

```
users ──────────────────── documents ──────────── document_chunks
  │                             │
  └── audit_logs           query_logs
```

---

## Table: users

Stores authenticated healthcare professional accounts.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | VARCHAR(36) | PK | UUID v4 |
| username | VARCHAR(100) | UNIQUE, NOT NULL, INDEX | Login username |
| email | VARCHAR(255) | UNIQUE, NOT NULL, INDEX | Email address |
| hashed_password | VARCHAR(255) | NOT NULL | bcrypt hash |
| role | ENUM | NOT NULL, DEFAULT 'viewer' | admin/physician/researcher/viewer |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | Account active flag |
| created_at | DATETIME | NOT NULL | Registration timestamp |
| last_login | DATETIME | NULL | Last successful login |

---

## Table: documents

Tracks every uploaded medical document through its lifecycle.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | VARCHAR(36) | PK | UUID v4 |
| filename | VARCHAR(500) | NOT NULL | Stored filename (uuid_original) |
| original_filename | VARCHAR(500) | NOT NULL | User-provided filename |
| file_path | VARCHAR(1000) | NOT NULL | Absolute path on disk |
| file_size | INTEGER | NULL | Size in bytes |
| mime_type | VARCHAR(200) | NULL | Detected MIME type |
| category | ENUM | NOT NULL | medical_pdfs/treatment_guidelines/drug_databases/research_articles/medical_books/clinical_protocols/unknown |
| medical_specialty | VARCHAR(200) | NULL | Detected specialty (e.g. Cardiology) |
| source | VARCHAR(500) | NULL | Document source / publisher |
| title | VARCHAR(1000) | NULL | Document title |
| authors | TEXT | NULL | Author list |
| publication_year | INTEGER | NULL | Year of publication |
| processing_status | ENUM | NOT NULL | pending/validating/processing/indexed/failed/rejected |
| embedding_status | BOOLEAN | NOT NULL, DEFAULT FALSE | Vectors stored in ChromaDB |
| chunk_count | INTEGER | DEFAULT 0 | Number of text chunks |
| version | INTEGER | NOT NULL, DEFAULT 1 | Document version |
| is_validated | BOOLEAN | NOT NULL, DEFAULT FALSE | Passed medical validation |
| validation_score | FLOAT | NULL | Domain confidence [0.0–1.0] |
| rejection_reason | TEXT | NULL | Reason if rejected |
| uploaded_at | DATETIME | NOT NULL | Upload timestamp |
| processed_at | DATETIME | NULL | Processing completion timestamp |
| uploaded_by | VARCHAR(36) | FK→users.id | Uploader |

**Indexes:** category, processing_status, uploaded_at

---

## Table: document_chunks

Stores text chunks derived from documents, linked to vector store IDs.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | VARCHAR(36) | PK | UUID v4 |
| document_id | VARCHAR(36) | FK→documents.id, NOT NULL | Parent document |
| chunk_index | INTEGER | NOT NULL | Sequential index within document |
| content | TEXT | NOT NULL | Raw text content of the chunk |
| embedding_id | VARCHAR(500) | NULL | ChromaDB/FAISS vector ID |
| page_number | INTEGER | NULL | Source page number |
| section | VARCHAR(500) | NULL | Detected section (Abstract, Methods, etc.) |
| created_at | DATETIME | NOT NULL | Creation timestamp |

**Indexes:** document_id

---

## Table: query_logs

Audit trail of all medical queries for analytics and compliance.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | VARCHAR(36) | PK | UUID v4 |
| user_id | VARCHAR(36) | FK→users.id, NULL | Querying user (NULL = anonymous) |
| query_type | VARCHAR(100) | NOT NULL | medical_query/drug_interaction/symptom_query/treatment_protocol |
| query_text | TEXT | NOT NULL | Full query text |
| response_summary | TEXT | NULL | First 500 chars of response |
| sources_used | TEXT | NULL | JSON array of document IDs |
| confidence_score | FLOAT | NULL | Response confidence [0.0–1.0] |
| response_time_ms | INTEGER | NULL | End-to-end latency |
| created_at | DATETIME | NOT NULL | Query timestamp |

**Indexes:** user_id, created_at

---

## Table: audit_logs

Complete audit trail for security and compliance.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | VARCHAR(36) | PK | UUID v4 |
| user_id | VARCHAR(36) | FK→users.id, NULL | Acting user |
| action | VARCHAR(200) | NOT NULL | login_success/login_failed/document_uploaded/document_deleted/etc. |
| resource_type | VARCHAR(100) | NULL | documents/users/queries |
| resource_id | VARCHAR(36) | NULL | Affected resource ID |
| details | TEXT | NULL | Additional context (JSON) |
| ip_address | VARCHAR(50) | NULL | Client IP |
| user_agent | VARCHAR(500) | NULL | HTTP User-Agent |
| success | BOOLEAN | NOT NULL, DEFAULT TRUE | Action succeeded |
| created_at | DATETIME | NOT NULL | Event timestamp |

**Indexes:** user_id, created_at, action

---

## Enum Values Reference

### UserRole
```
admin       – Full system access, user management
physician   – Upload, query, delete documents
researcher  – Upload, query documents
viewer      – Query documents only
```

### DocumentCategory
```
medical_pdfs          – General medical PDFs
treatment_guidelines  – Clinical guidelines (AHA, WHO, etc.)
drug_databases        – Pharmacology references, formularies
research_articles     – Peer-reviewed research, RCTs
medical_books         – Medical textbooks, atlases
clinical_protocols    – Hospital SOPs, care pathways
unknown               – Pending classification
```

### ProcessingStatus
```
pending      – Uploaded, awaiting processing
validating   – Domain validation in progress
processing   – Text extraction + chunking in progress
indexed      – Fully embedded and searchable
failed       – Processing error occurred
rejected     – Failed medical domain validation
```
