"""
MediRAG AI – Authentication Service
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import User, AuditLog
from app.models.schemas import UserCreate, Token
from app.utils.security import hash_password, verify_password, create_access_token
from app.utils.logger import logger
from app.config import settings


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_user(self, user_data: UserCreate) -> User:
        """Create a new user account."""
        # Check for duplicates
        existing = await self.db.execute(
            select(User).where(
                (User.username == user_data.username) | (User.email == user_data.email)
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Username or email already registered.")

        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hash_password(user_data.password),
            role=user_data.role,
        )
        self.db.add(user)
        await self.db.flush()
        logger.info(f"New user registered: {user.username} (role={user.role})")
        return user

    async def authenticate(self, username: str, password: str) -> Optional[User]:
        """Verify credentials and return user if valid."""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.hashed_password):
            return None

        # Update last login
        user.last_login = datetime.utcnow()
        return user

    async def create_token(self, user: User) -> Token:
        """Generate JWT access token for authenticated user."""
        token = create_access_token(
            data={"sub": user.username, "user_id": user.id, "role": user.role.value}
        )
        return Token(
            access_token=token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )

    async def log_audit(
        self,
        action: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
    ) -> None:
        """Write an audit log entry."""
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            success=success,
        )
        self.db.add(log)
