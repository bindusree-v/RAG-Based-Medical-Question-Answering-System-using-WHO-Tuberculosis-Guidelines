# MediRAG AI – Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MEDIRAG AI SYSTEM                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────┐     ┌──────────┐      ┌────────────────────────────────┐  │
│  │ Browser  │────▶│  Nginx   │─────▶│     Next.js Frontend           │  │
│  │  Client  │     │  Proxy   │      │  - Dashboard / Chat            │  │
│  └──────────┘     └──────────┘      │  - Drug Interaction Checker    │  │
│                        │            │  - Treatment Protocol Search   │  │
│                        │            │  - Research Search             │  │
│                        │            │  - Document Upload Center      │  │
│                        │            │  - Knowledge Base Manager      │  │
│                        │            │  - Citation Viewer             │  │
│                        │            └────────────────────────────────┘  │
│                        │                         │ REST API              │
│                        ▼                         ▼                       │
│               ┌────────────────────────────────────────────────────┐    │
│               │              FastAPI Backend                        │    │
│               │                                                     │    │
│               │  ┌──────────────┐   ┌──────────────────────────┐  │    │
│               │  │  Auth Layer  │   │   API Routes              │  │    │
│               │  │  JWT + RBAC  │   │  /upload-document         │  │    │
│               │  │  Rate Limit  │   │  /validate-document       │  │    │
│               │  └──────────────┘   │  /medical-query           │  │    │
│               │                     │  /drug-interaction         │  │    │
│               │                     │  /symptom-query            │  │    │
│               │                     │  /treatment-protocol       │  │    │
│               │                     │  /documents                │  │    │
│               │                     │  /health                   │  │    │
│               │                     └──────────────────────────┘  │    │
│               │                                │                    │    │
│               │         ┌──────────────────────┘                   │    │
│               │         ▼                                           │    │
│               │  ┌──────────────────────────────────────────────┐  │    │
│               │  │         Document Ingestion Pipeline           │  │    │
│               │  │                                               │  │    │
│               │  │  Upload → Validate → Extract → Clean         │  │    │
│               │  │       → Chunk → Embed → Store                │  │    │
│               │  │                                               │  │    │
│               │  │  ┌─────────────────────────────────────┐    │  │    │
│               │  │  │  Medical Validation Engine           │    │  │    │
│               │  │  │  Keyword Scoring + Domain Check     │    │  │    │
│               │  │  │  ACCEPT: Clinical / Drug / Research │    │  │    │
│               │  │  │  REJECT: Resume / Invoice / General │    │  │    │
│               │  │  └─────────────────────────────────────┘    │  │    │
│               │  └──────────────────────────────────────────────┘  │    │
│               │                                                     │    │
│               │  ┌──────────────────────────────────────────────┐  │    │
│               │  │       LangGraph Multi-Agent System            │  │    │
│               │  │                                               │  │    │
│               │  │  User Query                                   │  │    │
│               │  │      │                                        │  │    │
│               │  │      ▼                                        │  │    │
│               │  │  ┌─────────┐                                  │  │    │
│               │  │  │ Router  │ (LLM-based classification)       │  │    │
│               │  │  └────┬────┘                                  │  │    │
│               │  │       ├──────────────────┬────────────┐       │  │    │
│               │  │       ▼                  ▼            ▼       │  │    │
│               │  │  ┌─────────┐  ┌──────────────┐  ┌─────────┐  │  │    │
│               │  │  │ Medical │  │    Drug       │  │Treatment│  │  │    │
│               │  │  │  Lit.   │  │ Interaction   │  │Protocol │  │  │    │
│               │  │  │ Agent   │  │    Agent      │  │  Agent  │  │  │    │
│               │  │  └─────────┘  └──────────────┘  └─────────┘  │  │    │
│               │  │       │              │                │        │  │    │
│               │  │  ┌─────────┐  ┌──────────────┐              │  │    │
│               │  │  │Medical  │  │  Symptom     │              │  │    │
│               │  │  │  QA     │  │  Knowledge   │              │  │    │
│               │  │  │ Agent   │  │    Agent     │              │  │    │
│               │  │  └─────────┘  └──────────────┘              │  │    │
│               │  └──────────────────────────────────────────────┘  │    │
│               │                                                     │    │
│               │  ┌──────────────────────────────────────────────┐  │    │
│               │  │              RAG Pipeline                     │  │    │
│               │  │                                               │  │    │
│               │  │  Query → Embed (BGE) → Similarity Search     │  │    │
│               │  │       → Top-K Retrieve → Context Assembly    │  │    │
│               │  │       → Llama 3 (Ollama) → Grounded Answer   │  │    │
│               │  │       → Citations + Confidence Score         │  │    │
│               │  └──────────────────────────────────────────────┘  │    │
│               │                │                                    │    │
│               │     ┌──────────┼──────────────┐                    │    │
│               │     ▼          ▼              ▼                    │    │
│               │  ┌──────┐  ┌────────┐   ┌──────────┐              │    │
│               │  │Chroma│  │SQLite/ │   │  Ollama  │              │    │
│               │  │  DB  │  │PostGre │   │  Llama3  │              │    │
│               │  │Vectors│  │  SQL  │   │ (Local)  │              │    │
│               │  └──────┘  └────────┘   └──────────┘              │    │
│               └────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     Document Storage (disk)                      │   │
│  │  data/uploaded_documents/{category}/  +  data/embeddings/       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Document Ingestion
```
1. User uploads PDF/DOCX/TXT via /upload-document
2. Medical Validation Engine:
   a. File type check (.pdf, .docx, .txt)
   b. Keyword scoring across 5 medical domains
   c. Rejection scoring for non-medical content
   d. Accept/Reject decision with confidence score
3. Text Extraction (pdfplumber → pypdf fallback, python-docx, plain text)
4. RecursiveCharacterTextSplitter (chunk_size=1000, overlap=200)
5. BAAI/bge-small-en-v1.5 embedding generation
6. ChromaDB vector storage with metadata
7. SQLite/PostgreSQL metadata record creation
```

### Query Processing
```
1. User submits clinical query
2. LangGraph routes to appropriate agent:
   - "drug interaction" → Drug Interaction Agent
   - "treatment protocol" → Treatment Protocol Agent
   - "symptoms" → Symptom Knowledge Agent
   - "research literature" → Medical Literature Agent
   - general → Medical QA Agent
3. RAG Pipeline:
   a. Query embedded with BGE model
   b. Cosine similarity search in ChromaDB (Top-K)
   c. Context assembly from retrieved chunks
   d. Prompt construction with medical context
   e. Llama 3 (Ollama) inference
4. Response includes:
   - Grounded answer
   - Source citations with relevance scores
   - Confidence score
   - Disclaimer
```

## Security Architecture

```
┌─────────────────────────────────────────────────┐
│                Security Layers                  │
├─────────────────────────────────────────────────┤
│  1. Nginx Rate Limiting (30 req/min API)        │
│  2. JWT Bearer Token Authentication            │
│  3. Role-Based Access Control (RBAC)           │
│     Admin > Physician > Researcher > Viewer    │
│  4. File Upload Validation (type + size + content) │
│  5. Input sanitization (Pydantic v2)           │
│  6. Security HTTP Headers                      │
│  7. Audit Logging (all actions)                │
│  8. Local-only inference (no external APIs)    │
└─────────────────────────────────────────────────┘
```

## Component Summary

| Component | Technology | Purpose |
|---|---|---|
| API Gateway | Nginx 1.25 | Reverse proxy, rate limiting, SSL termination |
| Backend Framework | FastAPI + Uvicorn | Async REST API |
| Agent Orchestration | LangGraph | Multi-agent query routing |
| LLM Framework | LangChain | Prompt management, chain execution |
| Local LLM | Llama 3 + Ollama | Offline inference |
| Embeddings | BAAI/bge-small-en-v1.5 | Semantic vector generation |
| Vector Store | ChromaDB (+ FAISS) | Similarity search |
| Metadata DB | SQLite / PostgreSQL | Document records, users, audit logs |
| Document Processing | pdfplumber, pypdf, python-docx | Text extraction |
| Chunking | LangChain RecursiveCharacterTextSplitter | Context-aware chunking |
| Frontend | Next.js 14 + TypeScript | Healthcare dashboard UI |
| Styling | Tailwind CSS + shadcn/ui | Component library |
| Auth | JWT + bcrypt | Stateless authentication |
| Containerization | Docker + Docker Compose | Deployment |
| CI/CD | GitHub Actions | Automated testing + build |
