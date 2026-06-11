"""
FastAPI dependencies: app state helpers, admin JWT auth, and merchant API key auth.
"""
import datetime

from fastapi import Request, HTTPException, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy import select

from app.core.security import decode_token, verify_api_key
from app.db.models.api_key import ApiKey
from app.db.async_session import get_async_db
from app.utils.crypto import HDWalletManager

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
_api_key_scheme = APIKeyHeader(name="X-Api-Key", auto_error=False)


def get_blockchains(request: Request):
    """Dependency to access initialized blockchains from app state."""
    return request.app.state.blockchains  # pylint: disable=no-member


def get_hdwallet(request: Request) -> HDWalletManager:
    """Dependency to access the HD wallet manager from app state."""
    return request.app.state.hdwallet  # pylint: disable=no-member


async def require_admin(token: str = Security(_oauth2_scheme)) -> str:
    """Validates the Bearer JWT access token. Returns the admin username."""
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
    return subject


async def require_api_key(key: str = Security(_api_key_scheme)) -> ApiKey:
    """Validates the X-Api-Key header against active API keys in the database."""

    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    prefix = key[:8]

    async for session in get_async_db():
        result = await session.execute(
            select(ApiKey).where(ApiKey.key_prefix == prefix)
        )
        candidates = result.scalars().all()

        matched: ApiKey | None = None
        for candidate in candidates:
            if verify_api_key(key, candidate.hashed_key):
                matched = candidate
                break

        if not matched:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

        if not matched.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key has been revoked")

        matched.last_used_at = datetime.datetime.now(datetime.timezone.utc)
        await session.commit()

        return matched
