"""
Pydantic models for payment-related API operations.

The API surface is kept backward-compatible with the frontend (``amount``,
``chain``, ``token_contract_address``) even though the underlying database now
stores ``amount_raw`` and ``token_contract`` per the redesigned schema.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import Field

from app.blockchain.chains import chain_name_for_id
from app.db.models.payment import Payment, PaymentStatus
from app.schemas.base import BaseSchema
from app.utils.helpers import wei_to_eth_str


class PaymentCreate(BaseSchema):
    """Schema for creating a new payment."""
    amount: int = Field(..., gt=0, description="Amount in Wei or token base unit")
    chain_id: int = Field(..., gt=0, description="Blockchain identifier")
    token_contract_address: Optional[str] = Field(
        None, max_length=120,
        description="ERC20 token contract address; omit for native token payments"
    )


class PaymentRead(BaseSchema):
    """What you return to the client (public view)."""
    id: UUID
    chain_id: int
    chain: Optional[str] = None
    token_contract_address: Optional[str] = None
    address: str
    amount: str
    status: PaymentStatus
    confirmations: int
    api_key_id: Optional[UUID] = Field(None, description="API key that created this payment")
    api_key_name: Optional[str] = Field(None, description="Name of the API key (for attribution)")
    created_at: datetime
    expires_at: datetime

    @classmethod
    def from_payment(
        cls,
        payment: Payment,
        api_key_name: Optional[str] = None,
        chain_name: Optional[str] = None,
    ) -> "PaymentRead":
        """Build the public view from a Payment row, resolving derived fields."""
        return cls(
            id=payment.id,
            chain_id=payment.chain_id,
            chain=chain_name or chain_name_for_id(payment.chain_id),
            token_contract_address=payment.token_contract,
            address=payment.address,
            amount=wei_to_eth_str(payment.amount_raw),
            status=payment.status,
            confirmations=payment.confirmations,
            api_key_id=payment.api_key_id,
            api_key_name=api_key_name,
            created_at=payment.created_at,
            expires_at=payment.expires_at,
        )


class PaymentResponse(BaseSchema):
    """Standard response wrapper for a single payment."""
    data: PaymentRead

    model_config = {
        "ser_json_timedelta": "iso8601"
    }


class PaymentListResponse(BaseSchema):
    """Standard response wrapper for a list of payments."""
    data: List[PaymentRead]
    total: int
    page: int = 1
    size: int = 20
