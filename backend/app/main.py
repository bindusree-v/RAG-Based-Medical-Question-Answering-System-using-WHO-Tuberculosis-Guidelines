"""
MediRAG AI – Enterprise Healthcare Knowledge Assistant
FastAPI Application Entry Point
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api import api_router
from app.config import settings
from app.models.database import init_db
from app.utils.logger import setup_logger, logger
from app.utils.file_utils import ensure_directory_exists
from app.utils.metrics import setup_metrics


# ---------------------------------------------------------------------------
# Application Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # Initialize logger
    setup_logger(
        log_level="DEBUG" if settings.debug else "INFO",
        log_file="logs/medirag.log",
    )
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Ensure required directories exist
    dirs = [
        settings.upload_base_dir,
        settings.metadata_dir,
        settings.chroma_persist_directory,
        "logs",
    ]
    for category in settings.document_categories:
        dirs.append(os.path.join(settings.upload_base_dir, category))
    dirs.append(os.path.join(settings.upload_base_dir, "rejected"))

    for d in dirs:
        ensure_directory_exists(d)

    # Initialize database tables
    await init_db()
    logger.info("Database initialized.")

    yield

    logger.info(f"{settings.app_name} shutting down.")


# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------

limiter = Limiter(key_func=get_remote_address)


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    description=(
        "Enterprise Healthcare Knowledge Assistant powered by RAG, LangGraph, "
        "and local Llama 3. All responses are educational and informational only. "
        "Not a substitute for professional clinical judgment."
    ),
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)

# Rate limit state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# ---------------------------------------------------------------------------
# Security Headers Middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Cache-Control"] = "no-store"
    return response


# ---------------------------------------------------------------------------
# Global Exception Handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal error occurred. Please try again later."},
    )


# ---------------------------------------------------------------------------
# API Router Registration
# ---------------------------------------------------------------------------

app.include_router(api_router, prefix="/api/v1")

# Prometheus metrics (optional – skips gracefully if package not installed)
setup_metrics(app)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "disclaimer": (
            "Educational and informational use only. "
            "Not a substitute for professional clinical judgment."
        ),
    }
