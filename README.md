# MediRAG AI – Enterprise Healthcare Knowledge Assistant

> **Educational and informational use only. Not a substitute for professional clinical judgment.**

A production-grade, fully offline Healthcare AI Assistant that enables healthcare professionals to retrieve evidence-based information from medical literature, drug databases, treatment guidelines, and clinical protocols using Retrieval-Augmented Generation (RAG) and multi-agent AI workflows.

---

## Core Features

| Feature | Description |
|---|---|
| Medical Literature Search | Semantic search across indexed medical papers and journals |
| Drug Interaction Checker | AI-powered drug safety analysis with severity grading |
| Clinical Guideline Retrieval | Evidence-based protocol retrieval |
| Treatment Protocol Assistant | Step-by-step clinical management guidance |
| Symptom-Based Knowledge Retrieval | Clinical knowledge from presenting symptoms |
| Evidence-Based Medical Q&A | Grounded answers with source citations |
| Source Citation Viewer | Full provenance for every response |
| Offline Local LLM Inference | Llama 3 via Ollama — fully air-gapped |
| Medical Document Validation Engine | Rejects non-medical uploads automatically |
| Knowledge Base Dashboard | Document management with indexing status |

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, Pydantic, Uvicorn |
| AI/LLM | Llama 3 (local), Ollama |
| RAG | LangChain, LangGraph (multi-agent) |
| Embeddings | BAAI/bge-small-en-v1.5 (sentence-transformers) |
| Vector DB | ChromaDB (+ FAISS support) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |
| Infrastructure | Docker, Nginx, GitHub Actions |

---

## Project Structure

```
medirag-ai/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routes
│   │   ├── agents/        # LangGraph multi-agent system
│   │   ├── embeddings/    # Embedding service (BGE)
│   │   ├── ingestion/     # Text extraction + chunking
│   │   ├── models/        # DB models + Pydantic schemas
│   │   ├── rag/           # RAG pipeline + prompts
│   │   ├── services/      # Business logic
│   │   ├── utils/         # Security, logging, file utils
│   │   ├── validation/    # Medical domain validator
│   │   ├── vectorstore/   # ChromaDB integration
│   │   └── tests/         # Unit + integration tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/    # UI components
│   │   ├── hooks/         # React hooks
│   │   ├── pages/         # Next.js pages
│   │   └── services/      # API client
│   └── Dockerfile
├── data/
│   ├── uploaded_documents/
│   └── embeddings/
├── nginx/
├── docker-compose.yml
└── DEPLOYMENT.md
```

---

## AI Agents (LangGraph)

1. **Medical Literature Agent** – Research retrieval, clinical evidence search
2. **Drug Interaction Agent** – Safety checks, contraindication lookup
3. **Treatment Protocol Agent** – Protocol retrieval, clinical workflow guidance
4. **Medical QA Agent** – Evidence-based question answering
5. **Knowledge Base Agent** – Document indexing and metadata management

---

## Quick Start

```bash
git clone <repo>
cd medirag-ai

# Pull Llama 3
ollama pull llama3

# Start everything
docker compose up --build -d

# Open browser
open http://localhost:3000
```

See [DEPLOYMENT.md](./DEPLOYMENT.md) for full production setup.

---

## Security

- JWT authentication with role-based access control (Admin, Physician, Researcher, Viewer)
- Secure file upload with type and size validation
- Input sanitization on all endpoints
- API rate limiting
- Full audit logging
- Local inference only — no external API calls
- No patient data storage

---

## Disclaimer

This system is designed for **educational and informational purposes only**. It is intended to assist healthcare professionals with access to medical knowledge, not to replace clinical judgment, diagnosis, or treatment decisions. Always consult qualified healthcare providers for medical decisions.
