"""
MediRAG AI – Authentication API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.schemas import UserCreate, UserResponse, Token, LoginRequest
from app.services.auth_service import AuthService
from app.utils.security import get_current_user
from app.models.database import User

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account."""
    service = AuthService(db)
    try:
        user = await service.register_user(user_data)
        return UserResponse.model_validate(user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Authenticate and obtain a JWT token."""
    service = AuthService(db)
    user = await service.authenticate(form_data.username, form_data.password)

    if not user:
        await service.log_audit(
            action="login_failed",
            details=f"Failed login for username: {form_data.username}",
            ip_address=request.client.host if request.client else None,
            success=False,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = await service.create_token(user)
    await service.log_audit(
        action="login_success",
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
    )
    return token


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return UserResponse.model_validate(current_user)
