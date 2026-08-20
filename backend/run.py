"""
MediRAG AI – Development Server Entry Point
"""

import uvicorn
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
        workers=1,  # Use 1 worker for local LLM; scale with proper GPU setup
    )
