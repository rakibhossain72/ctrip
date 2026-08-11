"""
FastAPI dependencies: app state helpers, admin JWT auth, and merchant API key auth.
"""
from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy import select

from app.core.security import decode_token, verify_api_key
from app.db.async_session import get_async_db
from app.db.models.api_key import KEY_PREFIX_LENGTH, ApiKey
from app.db.models.user import User
from app.utils.helpers import now_utc
from app.wallet import WalletKeyManager

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
_api_key_scheme = APIKeyHeader(name="X-Api-Key", auto_error=False)


def get_blockchains(request: Request):
    """Dependency to access initialized blockchains from app state."""
    return request.app.state.blockchains  # pylint: disable=no-member


def get_wallet_manager(request: Request) -> WalletKeyManager:
    """Dependency to generate and access the payment wallet manager from app state."""
    return request.app.state.wallet_manager

def get_arq_pool(request: Request):
    """Dependency to access the Arq connection pool from app state."""
    return request.app.state.arq_pool


async def require_admin(token: str = Security(_oauth2_scheme)) -> User:
    """Validates the Bearer JWT access token and returns the active User."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    subject = decode_token(token, expected_type="access")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async for session in get_async_db():
        result = await session.execute(
            select(User).where(User.username == subject)
        )
        user = result.scalars().first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user


async def require_api_key(key: str = Security(_api_key_scheme)) -> ApiKey:
    """Validates the X-Api-Key header against active API keys in the database."""

    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    prefix = key[:KEY_PREFIX_LENGTH]

    async for session in get_async_db():
        result = await session.execute(
            select(ApiKey).where(ApiKey.key_prefix == prefix)
        )
        candidates = result.scalars().all()

        matched: ApiKey | None = None
        for candidate in candidates:
            if verify_api_key(key, candidate.key_hash):
                matched = candidate
                break

        if not matched:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

        if not matched.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key has been revoked")

        # Lazy last_used_at — throttled to avoid write amplification (M5).
        if matched.should_refresh_last_used(now_utc()):
            matched.last_used_at = now_utc()
            await session.commit()

        return matched
