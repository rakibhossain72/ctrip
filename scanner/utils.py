from __future__ import annotations

from typing import Optional, Union

from eth_utils import to_checksum_address
from web3 import Web3

# keccak256("Transfer(address,address,uint256)")
ERC20_TRANSFER_TOPIC = (
    "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
)

# A valid topic is "0x" + 64 hex chars (32 bytes)
_TOPIC_LENGTH = 66


def decode_topic_address(topic: str) -> Optional[str]:
    """
    Extract a checksummed Ethereum address from a 32-byte ABI-encoded topic.

    ABI-encodes pad addresses to 32 bytes by left-zero-filling, so the
    address lives in the rightmost 20 bytes (last 40 hex chars).

    Returns None if the topic is malformed.
    """
    if not isinstance(topic, str):
        return None
    if not topic.startswith("0x") or len(topic) != _TOPIC_LENGTH:
        return None
    try:
        return to_checksum_address("0x" + topic[-40:])
    except ValueError:
        return None


def normalize(address: str) -> str:
    """Return the EIP-55 checksum form of *address*."""
    return Web3.to_checksum_address(address)


def topic_from_address(address: str) -> str:
    """
    Convert a checksummed address to its 32-byte ABI-encoded topic form,
    suitable for use as a log filter topic.
    """
    return "0x" + address[2:].lower().zfill(64)


def hex_to_int(value: Union[str, int, None]) -> Optional[int]:
    """
    Safely coerce a hex string or integer to int.

    Returns None instead of raising on bad input.
    """
    if value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value, 16)
    except (ValueError, TypeError):
        return None
