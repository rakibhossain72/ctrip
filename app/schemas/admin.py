"""
Pydantic schemas for admin API request/response bodies.
"""

import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel


class SweepAddressRequest(BaseModel):
    """Request body for sweeping a specific address."""

    address: str
    chain_name: str


class ProcessPaymentRequest(BaseModel):
    """Request body for manually processing a payment."""

    payment_id: UUID
    chain_name: str


class CustomWebhookRequest(BaseModel):
    """Request body for sending a custom webhook."""

    url: str
    payload: Dict[str, Any]
    secret: Optional[str] = None


class JobResponse(BaseModel):
    """Generic response for enqueued background jobs."""

    job_id: str
    status: str
    message: str


class ApiKeyCreateRequest(BaseModel):
    """Request body for creating a new API key."""

    name: str


class ApiKeyResponse(BaseModel):
    """API key metadata returned in list responses (raw key never included)."""

    id: UUID
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime.datetime
    last_used_at: Optional[datetime.datetime] = None

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyResponse):
    """API key creation response that includes the raw key shown once."""

    raw_key: str
