from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.db.async_session import get_async_db
from app.db.models.admin_user import AdminUser
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_async_db)):
    """Authenticate and receive access + refresh tokens."""
    result = await db.execute(
        select(AdminUser).where(AdminUser.username == body.username, AdminUser.is_active == True)
    )
    user = result.scalars().first()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return TokenResponse(
        access_token=create_access_token(subject=user.username),
        refresh_token=create_refresh_token(subject=user.username),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    subject = decode_token(body.refresh_token, expected_type="refresh")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    return TokenResponse(
        access_token=create_access_token(subject=subject),
        refresh_token=create_refresh_token(subject=subject),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    """Logout is handled client-side by discarding the tokens."""
