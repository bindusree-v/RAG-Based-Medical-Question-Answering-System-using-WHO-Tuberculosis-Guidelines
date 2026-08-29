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
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create required directories
RUN mkdir -p logs \
    ../data/uploaded_documents/medical_pdfs \
    ../data/uploaded_documents/treatment_guidelines \
    ../data/uploaded_documents/drug_databases \
    ../data/uploaded_documents/research_articles \
    ../data/uploaded_documents/medical_books \
    ../data/uploaded_documents/clinical_protocols \
    ../data/uploaded_documents/rejected \
    ../data/embeddings/vector_store/chroma_db \
    ../data/metadata

# Non-root user for security
RUN useradd -m -u 1000 medirag && chown -R medirag:medirag /app
USER medirag

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
