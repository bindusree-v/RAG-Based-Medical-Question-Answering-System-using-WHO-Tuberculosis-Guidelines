"""
MediRAG AI – File Utility Helpers
"""

import os
import re
import uuid
from pathlib import Path


def generate_unique_id() -> str:
    """Generate a UUID4 string."""
    return str(uuid.uuid4())


def get_file_extension(filename: str) -> str:
    """Return lowercase file extension including dot, e.g. '.pdf'."""
    return Path(filename).suffix.lower()


def sanitize_filename(filename: str) -> str:
    """
    Remove dangerous characters from filename.
    Replaces whitespace with underscores and strips non-alphanumeric chars.
    """
    # Remove path separators and null bytes
    filename = filename.replace("/", "_").replace("\\", "_").replace("\x00", "")
    # Replace spaces
    filename = filename.replace(" ", "_")
    # Keep only safe characters
    filename = re.sub(r"[^\w\-.]", "", filename)
    return filename[:255]  # Limit length


def ensure_directory_exists(path: str) -> Path:
    """Create directory and all parents if they do not exist."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def human_readable_size(size_bytes: int) -> str:
    """Convert byte count to human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes //= 1024
    return f"{size_bytes:.1f} TB"


__all__ = [
    "generate_unique_id", "get_file_extension",
    "sanitize_filename", "ensure_directory_exists",
    "human_readable_size",
]
