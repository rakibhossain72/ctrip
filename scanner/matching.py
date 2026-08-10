from __future__ import annotations

from typing import Iterable, Optional, Union

from web3.types import TxReceipt

from scanner.constants import ERC20_TRANSFER_TOPIC
from scanner.model import Erc20Transfer

# A valid topic is "0x" + 64 hex chars (32 bytes)
_TOPIC_LENGTH = 66


def _to_hex_str(value: Union[bytes, str, None]) -> Optional[str]:
    """Coerce bytes/HexBytes/str/None into a lower-case hex string."""
    if value is None:
        return None
    if isinstance(value, str):
        return value.lower()
    return "0x" + value.hex()


def normalize_address(address) -> str:
    """Return the lower-case hex form of *address* (bytes or str)."""
    if isinstance(address, (bytes, bytearray)):
        return "0x" + bytes(address).hex()
    return (address or "").strip().lower()


def decode_topic_address(topic: Union[bytes, str, None]) -> Optional[str]:
    """
    Extract the lower-case address from a 32-byte ABI-encoded log topic.

    ABI encoding pads addresses to 32 bytes by left-zero-filling, so the
    address lives in the rightmost 20 bytes (last 40 hex chars).
    Returns None if the topic is malformed.
    """
    topic_str = _to_hex_str(topic)
    if topic_str is None or not topic_str.startswith("0x"):
        return None
    if len(topic_str) != _TOPIC_LENGTH:
        return None
    try:
        bytes.fromhex(topic_str[2:])
    except ValueError:
        return None
    return "0x" + topic_str[-40:]


def topic_from_address(address: str) -> str:
    """Convert an address to its 32-byte ABI-encoded topic form for filters."""
    addr = address.lower()
    if addr.startswith("0x"):
        addr = addr[2:]
    return "0x" + addr.rjust(64, "0")


def addresses_to_topics(addresses: Optional[Iterable[str]]) -> Optional[list[str]]:
    """Turn addresses into a topic filter entry (OR semantics), or None to
    match anything in that slot."""
    addresses = list(addresses) if addresses else None
    if not addresses:
        return None
    return [topic_from_address(a) for a in addresses]


def hex_to_int(value: Union[str, int, bytes, None]) -> Optional[int]:
    """Safely coerce a hex string, bytes value, or integer to int."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, (bytes, bytearray)):
        return int.from_bytes(bytes(value), "big")
    try:
        return int(value, 16)
    except (ValueError, TypeError):
        return None


def decode_erc20_transfer(log: dict, chain_id: int) -> Optional[Erc20Transfer]:
    """
    Decode an ERC-20 ``Transfer(address,address,uint256)`` log.

    Works with web3 AttributeDicts (HexBytes values) or plain dicts
    (bytes/str values, as they arrive after arq serialization).
    Returns None if the log is not a valid Transfer event.
    """
    topics = log.get("topics") or []
    if len(topics) < 3:
        return None
    if _to_hex_str(topics[0]) != ERC20_TRANSFER_TOPIC:
        return None

    from_address = decode_topic_address(topics[1])
    to_address = decode_topic_address(topics[2])
    if from_address is None or to_address is None:
        return None

    amount = hex_to_int(log.get("data"))
    if amount is None:
        return None

    tx_hash = _to_hex_str(log.get("transactionHash")) or ""
    token = normalize_address(log.get("address") or "")
    if not token:
        return None

    return Erc20Transfer(
        method="Transfer",
        token=token,
        to=to_address,
        amount=amount,
        tx_hash=tx_hash,
        chain_id=chain_id,
        log_index=log.get("logIndex"),
        block_number=log.get("blockNumber"),
        from_=from_address,
    )


def match_native_tx(tx: TxReceipt, watched: set[str]) -> Optional[str]:
    """
    If the transaction pays one of the watched addresses, return the matched
    (lower-cased) recipient; otherwise return None. Deposits only.
    """
    if not watched:
        return None
    to_addr = normalize_address(tx.get("to") or "")
    if to_addr and to_addr in watched:
        return to_addr
    return None
