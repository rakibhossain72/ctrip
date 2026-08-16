"""
Pydantic schemas for authentication request/response bodies.
"""

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Credentials for the login endpoint."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """OAuth2-style access/refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Request body for exchanging a refresh token."""

    refresh_token: str
