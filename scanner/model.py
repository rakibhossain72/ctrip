from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

_WATCH_TTL_MINUTES = 10


def _default_expires_at() -> str:
    return (
        datetime.now(timezone.utc) + timedelta(minutes=_WATCH_TTL_MINUTES)
    ).isoformat()


@dataclass
class WatchedAddress:
    address: str
    min_amount_wei: int
    chain_id: int
    confirmations: int = 1
    token_filter: Optional[str] = None
    expires_at: str = field(default_factory=_default_expires_at)

    def is_expired(self) -> bool:
        try:
            expiry = datetime.fromisoformat(self.expires_at)
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) >= expiry
        except ValueError:
            return False


@dataclass
class PaymentAddress:
    address: str
    min_amount_wei: int
    chain_id: int
    confirmations: int = 1
    token_contract: Optional[str] = None
    expires_at: str = field(default_factory=_default_expires_at)

    def is_expired(self) -> bool:
        try:
            expiry = datetime.fromisoformat(self.expires_at)
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) >= expiry
        except ValueError:
            return False


@dataclass
class TransferEvent:
    type: str
    token: Optional[str]
    from_address: str
    to_address: str
    value_raw: int
    tx_hash: str
    chain_id: int
    block_number: Optional[int]
    log_index: Optional[int] = None
    valid: bool = False
    rejection_reason: Optional[str] = None

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass
class PendingConfirmation:
    event: TransferEvent
    watched: WatchedAddress
    detected_block: int
    required_confirmations: int
    current_confirmations: int = 0

    @property
    def is_confirmed(self) -> bool:
        return self.current_confirmations >= self.required_confirmations


@dataclass(frozen=True, slots=True)
class Erc20Transfer:
    """A decoded ERC20 `Transfer` event, read from a transaction's logs."""
    method: str  # always "Transfer" - the event name
    token: str
    to: str
    amount: int
    tx_hash: str
    chain_id: int
    log_index: Optional[int] = None
    from_: Optional[str] = None
