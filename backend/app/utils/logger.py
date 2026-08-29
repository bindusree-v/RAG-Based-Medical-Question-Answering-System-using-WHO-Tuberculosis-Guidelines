"""
MediRAG AI – Structured Logging
Uses loguru for structured, leveled, and rotated logging.
"""

import sys
from loguru import logger


def setup_logger(log_level: str = "INFO", log_file: str = "logs/medirag.log") -> None:
    """Configure loguru logger with console and file sinks."""

    # Remove default sink
    logger.remove()

    # Console sink – human-readable
    logger.add(
        sys.stdout,
        level=log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # File sink – JSON structured for log aggregation
    logger.add(
        log_file,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
        rotation="100 MB",
        retention="30 days",
        compression="zip",
        serialize=True,
    )

    logger.info("MediRAG AI logger initialized.")


__all__ = ["setup_logger", "logger"]
