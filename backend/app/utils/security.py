"""
MediRAG AI – Security Utilities
JWT token management and password hashing using bcrypt directly.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import get_db, User
from app.models.schemas import TokenData
from app.utils.logger import logger

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ---------------------------------------------------------------------------
# Password Hashing
# ---------------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT Tokens
# ---------------------------------------------------------------------------

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            return None
        return TokenData(username=username, user_id=payload.get("user_id"), role=payload.get("role"))
    except JWTError as exc:
        logger.warning(f"JWT error: {exc}")
        return None


# ---------------------------------------------------------------------------
# FastAPI Dependencies
# ---------------------------------------------------------------------------

async def get_current_user(
    token: Optional[str] = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Auth disabled — return admin user unconditionally."""
    result = await db.execute(select(User).where(User.username == "admin"))
    user = result.scalar_one_or_none()
    if user:
        return user
    # Fallback: return a transient user object if DB has no admin
    class _FakeUser:
        id = "00000000-0000-0000-0000-000000000000"
        username = "guest"
        role_value = "admin"
        class role:
            value = "admin"
        is_active = True
    return _FakeUser()


def require_role(*allowed_roles: str):
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        return current_user  # auth disabled
    return _check


__all__ = ["hash_password", "verify_password", "create_access_token",
           "decode_access_token", "get_current_user", "require_role", "oauth2_scheme"]
