"""
MediRAG AI – Prometheus Metrics
Exposes /metrics endpoint for Prometheus scraping.
Install: pip install prometheus-fastapi-instrumentator
"""

from app.utils.logger import logger


def setup_metrics(app) -> None:
    """
    Attach Prometheus instrumentation to the FastAPI app.
    Gracefully skips if the package is not installed.
    """
    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            excluded_handlers=["/health", "/metrics"],
        ).instrument(app).expose(app, endpoint="/metrics")

        logger.info("Prometheus metrics enabled at /metrics")
    except ImportError:
        logger.info(
            "prometheus-fastapi-instrumentator not installed. "
            "Metrics endpoint disabled. Add it to requirements.txt to enable."
        )
