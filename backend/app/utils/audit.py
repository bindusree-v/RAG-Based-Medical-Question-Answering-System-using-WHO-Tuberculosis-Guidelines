"""
MediRAG AI – Audit Logging Helper
Convenience wrapper for writing audit log entries from anywhere in the app.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AuditLog
from app.utils.logger import logger


async def write_audit(
    db: AsyncSession,
    action: str,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    success: bool = True,
) -> None:
    """Write an audit log entry to the database."""
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            created_at=datetime.utcnow(),
        )
        db.add(entry)
        logger.debug(f"Audit: action={action} user={user_id} resource={resource_type}/{resource_id}")
    except Exception as exc:
        logger.warning(f"Failed to write audit log: {exc}")
