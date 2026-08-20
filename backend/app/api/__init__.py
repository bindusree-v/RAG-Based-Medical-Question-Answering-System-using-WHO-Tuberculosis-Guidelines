from fastapi import APIRouter
from .auth import router as auth_router
from .documents import router as documents_router
from .queries import router as queries_router
from .health import router as health_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(documents_router, prefix="/documents", tags=["Documents"])
api_router.include_router(queries_router, prefix="/query", tags=["Medical Queries"])
api_router.include_router(health_router, prefix="", tags=["System"])
