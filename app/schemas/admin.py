import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel


class SweepAddressRequest(BaseModel):
    address: str
    chain_name: str


class ProcessPaymentRequest(BaseModel):
    payment_id: int
    chain_name: str


class CustomWebhookRequest(BaseModel):
    url: str
    payload: Dict[str, Any]
    secret: Optional[str] = None


class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class ApiKeyCreateRequest(BaseModel):
    name: str


class ApiKeyResponse(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime.datetime
    last_used_at: Optional[datetime.datetime] = None

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyResponse):
    raw_key: str
