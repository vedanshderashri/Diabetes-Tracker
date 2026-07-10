"""
MedAI Assistant - Authentication API
User registration, login, and token management.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, get_current_user, log_audit_event,
)
from app.models.user import User
from app.models.patient import PatientProfile
from app.schemas.schemas import (
    UserRegister, UserLogin, TokenResponse,
    TokenRefresh, UserResponse, UserUpdate,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, request: Request, db: AsyncSession = Depends(get_db)):
    """Register a new patient account."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create user
    user = User(
        id=str(uuid.uuid4()),
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role="patient",
        language_preference=data.language_preference,
    )
    db.add(user)

    # Create empty patient profile
    profile = PatientProfile(
        id=str(uuid.uuid4()),
        user_id=user.id,
    )
    db.add(profile)
    await db.flush()

    # Generate tokens
    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id)

    # Audit log
    await log_audit_event(
        db, user.id, "register", "user",
        details=f"New user registered: {data.email}",
        ip_address=request.client.host if request.client else None,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    """Authenticate and get access tokens."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id)

    await log_audit_event(
        db, user.id, "login", "user",
        ip_address=request.client.host if request.client else None,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=dict)
async def refresh_token(data: TokenRefresh, db: AsyncSession = Depends(get_db)):
    """Refresh access token using refresh token."""
    payload = decode_token(data.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    new_access_token = create_access_token(user.id, user.role)
    return {"access_token": new_access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user."""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update current user account details."""
    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.phone is not None:
        current_user.phone = data.phone
    if data.language_preference is not None:
        current_user.language_preference = data.language_preference
    if data.password is not None:
        current_user.password_hash = hash_password(data.password)

    db.add(current_user)
    await log_audit_event(
        db, current_user.id, "update_account", "user",
        details="Updated user account details",
    )
    # The transaction commit is handled automatically by get_db yield dependency.
    return UserResponse.model_validate(current_user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete current user account and all associated data."""
    # Delete upload folder on disk
    import shutil
    from app.core.config import get_settings
    settings = get_settings()
    upload_dir = settings.upload_path / current_user.id
    if upload_dir.exists() and upload_dir.is_dir():
        try:
            shutil.rmtree(upload_dir, ignore_errors=True)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to delete user upload folder: {e}")

    await db.delete(current_user)
    return None
