from typing import Iterable, Optional





def _address_to_topic(address: str) -> str:
    """Left-pad a 20-byte address into the 32-byte topic form eth_getLogs expects."""
    addr = address.lower()
    if addr.startswith("0x"):
        addr = addr[2:]
    return "0x" + addr.rjust(64, "0")


def addresses_to_topics(addresses: Optional[Iterable[str]]) -> Optional[list[str]]:
    """Turn a list of addresses into a topic filter entry (OR semantics), or
    None if no addresses were given (meaning "match anything" for that slot)."""
    addresses = list(addresses) if addresses else None
    if not addresses:
        return None
    return [_address_to_topic(a) for a in addresses]