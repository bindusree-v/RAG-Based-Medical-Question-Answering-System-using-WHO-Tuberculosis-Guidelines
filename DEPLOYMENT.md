# MediRAG AI – Production Deployment Guide

## Prerequisites

- Docker 24+ and Docker Compose v2
- 16 GB RAM minimum (32 GB recommended for Llama 3)
- 20 GB free disk space
- NVIDIA GPU optional (for faster LLM inference)
- Ollama installed locally or via Docker

---

## 1. Pull and Configure Llama 3

```bash
# Install Ollama (Linux/macOS)
curl -fsSL https://ollama.com/install.sh | sh

# Pull Llama 3 model
ollama pull llama3

# Verify
ollama list
```

---

## 2. Configure Environment

```bash
cd backend
cp .env.example .env
# Edit .env:
#   SECRET_KEY=<generate with: openssl rand -hex 32>
#   DATABASE_URL=sqlite+aiosqlite:///./medirag.db  # or PostgreSQL
#   OLLAMA_BASE_URL=http://localhost:11434
```

```bash
# Frontend
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > frontend/.env.local
```

---

## 3. Docker Compose (Recommended)

```bash
# Build and start all services
docker compose up --build -d

# Pull Llama 3 into the Ollama container
docker exec medirag_ollama ollama pull llama3

# Check health
curl http://localhost:8000/api/v1/health
```

Services:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs (DEBUG=true only)

---

## 4. Local Development

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 5. Register First Admin User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@hospital.org",
    "password": "SecureAdminPass123!",
    "role": "admin"
  }'
```

---

## 6. Upload Your First Medical Document

```bash
# Login and get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin&password=SecureAdminPass123!" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Upload a medical PDF
curl -X POST http://localhost:8000/api/v1/documents/upload-document \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/medical_guideline.pdf"
```

---

## 7. Production Checklist

- [ ] Change `SECRET_KEY` to a cryptographically random value
- [ ] Set `DEBUG=false`
- [ ] Configure PostgreSQL (replace SQLite)
- [ ] Enable HTTPS via Nginx with Let's Encrypt
- [ ] Set `ALLOWED_ORIGINS` to your domain only
- [ ] Configure log rotation and alerting
- [ ] Set up regular database backups
- [ ] Review and restrict user roles

---

## 8. GPU Acceleration

Edit `docker-compose.yml` and uncomment the GPU section under `ollama` service.
Requires NVIDIA Container Toolkit.

---

## Architecture

```
Browser → Nginx → Next.js Frontend
               → FastAPI Backend → Ollama (Llama 3)
                                 → ChromaDB (vectors)
                                 → SQLite/PostgreSQL (metadata)
```

All inference is fully **local and offline**. No data leaves your infrastructure.
