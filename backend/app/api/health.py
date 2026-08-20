"""
MediRAG AI – Health Check API
"""

import time
from datetime import datetime

import httpx
from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.models.database import AsyncSessionLocal
from app.models.schemas import HealthResponse, ComponentStatus
from app.vectorstore.vector_store_manager import get_vector_store_manager

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    System health check endpoint.
    Returns status of all components: database, vector store, and LLM.
    """
    components: dict = {}

    # --- Database ---
    try:
        t0 = time.time()
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        components["database"] = ComponentStatus(
            status="healthy",
            latency_ms=int((time.time() - t0) * 1000),
        )
    except Exception as exc:
        components["database"] = ComponentStatus(
            status="unhealthy",
            message=str(exc),
        )

    # --- Vector Store (ChromaDB) ---
    try:
        t0 = time.time()
        vsm = get_vector_store_manager()
        stats = vsm.get_stats()
        components["vector_store"] = ComponentStatus(
            status="healthy",
            message=f"Vectors: {stats.get('vector_count', 0)}",
            latency_ms=int((time.time() - t0) * 1000),
        )
    except Exception as exc:
        components["vector_store"] = ComponentStatus(
            status="unhealthy",
            message=str(exc),
        )

    # --- Ollama LLM ---
    try:
        t0 = time.time()
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            llm_available = settings.llm_model in " ".join(models)
            components["llm"] = ComponentStatus(
                status="healthy" if llm_available else "degraded",
                message=f"Model '{settings.llm_model}' {'available' if llm_available else 'not found'}",
                latency_ms=int((time.time() - t0) * 1000),
            )
        else:
            components["llm"] = ComponentStatus(status="degraded", message="Ollama returned non-200")
    except Exception as exc:
        components["llm"] = ComponentStatus(
            status="unhealthy",
            message=f"Ollama not reachable: {exc}",
        )

    # Overall status
    statuses = [c.status for c in components.values()]
    if all(s == "healthy" for s in statuses):
        overall = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall = "unhealthy"
    else:
        overall = "degraded"

    return HealthResponse(
        status=overall,
        version=settings.app_version,
        environment=settings.environment,
        components=components,
        timestamp=datetime.utcnow(),
    )
