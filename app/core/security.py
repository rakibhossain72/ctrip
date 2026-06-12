"""
Security utilities: password hashing, JWT creation/verification, API key management.
"""
import hashlib
import secrets
import datetime
from typing import Optional

from jose import JWTError, jwt

from app.core.config import settings

import bcrypt

from app.utils.helpers import now_utc

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))


def create_access_token(subject: str) -> str:
    """Create a short-lived JWT access token (30 min)."""
    expire = now_utc() + datetime.timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "type": "access", "exp": expire}
    return jwt.encode(payload, settings.secret_key.get_secret_value(), algorithm=ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """Create a long-lived JWT refresh token (7 days)."""
    expire = now_utc() + datetime.timedelta(
        days=REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {"sub": subject, "type": "refresh", "exp": expire}
    return jwt.encode(payload, settings.secret_key.get_secret_value(), algorithm=ALGORITHM)


def decode_token(token: str, expected_type: str) -> Optional[str]:
    """
    Decode and validate a JWT token.
    Returns the subject (username) or None if invalid/expired/wrong type.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[ALGORITHM],
        )
        if payload.get("type") != expected_type:
            return None
        return payload.get("sub")
    except JWTError:
        return None


def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a new API key. Returns (raw_key, prefix, hashed_key).
    The raw key is shown once; only the hash is stored.
    """
    raw_key = f"ck_{secrets.token_urlsafe(32)}"
    prefix = raw_key[:8]
    hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, prefix, hashed_key


def verify_api_key(raw_key: str, hashed_key: str) -> bool:
    """Constant-time comparison of a raw key against its stored hash."""
    return secrets.compare_digest(
        hashlib.sha256(raw_key.encode()).hexdigest(),
        hashed_key,
    )
