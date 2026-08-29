# MediRAG AI – Backend Dockerfile
FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libmagic1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch==2.3.0 --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create app-local directories that don't need persistence across deploys.
# /data/* is the Render persistent disk mount (set via render.yaml).
# We still pre-create them so the image works in plain Docker too.
RUN mkdir -p logs \
    /data/uploaded_documents/medical_pdfs \
    /data/uploaded_documents/treatment_guidelines \
    /data/uploaded_documents/drug_databases \
    /data/uploaded_documents/research_articles \
    /data/uploaded_documents/medical_books \
    /data/uploaded_documents/clinical_protocols \
    /data/uploaded_documents/rejected \
    /data/embeddings/vector_store/chroma_db \
    /data/metadata

# Non-root user for security
RUN useradd -m -u 1000 medirag \
    && chown -R medirag:medirag /app \
    && chown -R medirag:medirag /data
USER medirag

# Render injects $PORT at runtime; default to 8000 for local Docker runs.
ENV PORT=8000

EXPOSE $PORT

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:${PORT}/health')" || exit 1

# Use shell form so $PORT is expanded at container start time.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1
