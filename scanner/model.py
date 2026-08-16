"""
Dataclass models for decoded on-chain transfer events.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class Erc20Transfer:
    """A decoded ERC-20 `Transfer` event read from a block's logs."""

    method: str  # always "Transfer" - the event name
    token: str
    to: str
    amount: int
    tx_hash: str
    chain_id: int
    log_index: Optional[int] = None
    block_number: Optional[int] = None
    from_: Optional[str] = None


@dataclass
class TransferEvent:
    """A native-currency transfer that matched a watched payment address."""

    type: str  # "native"
    token: Optional[str]
    from_address: str
    to_address: str
    value_raw: int
    tx_hash: str
    chain_id: int
    block_number: Optional[int]

    def as_dict(self) -> dict:
        """Return the event as a plain dictionary."""
