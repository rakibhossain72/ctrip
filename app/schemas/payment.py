from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Optional

from pydantic import Field

from schemas.base import BaseSchema
from db.models.payment import PaymentStatus


class PaymentBase(BaseSchema):
    chain: str = Field(..., min_length=3, max_length=20, description="Blockchain identifier e.g. ethereum, bsc, base")
    token_id: Optional[UUID] = Field(None, description="UUID of the token record")
    address: str = Field(..., min_length=30, max_length=120)
    amount: int = Field(..., gt=0, description="Amount in Wei (smallest unit, integer)")
    expires_at: datetime


class PaymentCreate(BaseSchema):
    amount: int = Field(..., gt=0, description="Amount in Wei or token base unit")
    chain: str = Field(..., min_length=3, max_length=20, description="Blockchain identifier")
    token_id: Optional[UUID] = Field(None, description="UUID of the token if ERC20")

class PaymentCreateInternal(PaymentBase):
    """Internal version — used when service layer creates the record"""
    pass

class PaymentUpdate(BaseSchema):
    """Very limited — most fields should NOT be updatable by client"""
    status: Optional[PaymentStatus] = None
    confirmations: Optional[int] = Field(None, ge=0)


class PaymentRead(PaymentBase):
    """What you return to the client (public view)"""
    id: UUID
    status: PaymentStatus
    confirmations: int
    created_at: datetime
    expires_at: datetime

    # Optional: hide sensitive/internal fields
    # merchant_id is usually hidden from public API


class PaymentInDB(PaymentRead):
    """Full database representation — used internally only"""
    # Nothing extra needed if you use from_attributes=True
    pass

class PaymentResponse(BaseSchema):
    data: PaymentRead


class PaymentListResponse(BaseSchema):
    data: list[PaymentRead]
    total: int
    page: int = 1
    size: int = 20

