from typing import Dict, List
from urllib.parse import urlparse

from app.core.config import settings


def get_ws_url(chain_name: str) -> str | None:
    """Return the first WebSocket RPC URL configured for a chain."""
    for chain in settings.chains:
        if chain.get("name", "").lower() != chain_name.lower():
            continue
        # rpc_urls list takes priority
        for url in chain.get("rpc_urls") or []:
            if url.startswith("ws://") or url.startswith("wss://"):
                return url
        # fall back to single rpc_url
        url = chain.get("rpc_url", "")
        if url.startswith("ws://") or url.startswith("wss://"):
            return url
    return None


def get_chains() -> Dict[str, Dict[str, List[str]]]:
    """
    Parses configured chains and categorizes their RPC URLs into HTTP and WebSocket endpoints,
    mapped by their unique chain identifier.

    Returns:
        Dict[str, Dict[str, List[str]]]: A dictionary mapping chain IDs to their 'https' and 'wss' URLs.
        Example:
            {
                "1": {"https": ["https://eth.rpc..."], "wss": ["wss://eth.rpc..."]},
                "137": {"https": ["https://polygon.rpc..."], "wss": []}
            }
    """
    # Key: chain_name (str), Value: {"https": [...], "wss": [...]}
    chain_mapping: Dict[str, Dict[str, List[str]]] = {}
    
    if not hasattr(settings, "chains") or not settings.chains:
        return chain_mapping

    for chain in settings.chains:
        if not isinstance(chain, dict):
            continue

        # Extract the chain identifier (fallback to "name" or stringified chain_name)
        chain_name = str(chain.get("name"))
        if not chain_name:
            continue  # Skip if we can't identify the chain

        # Initialize the structure for this specific chain if not already present
        if chain_name not in chain_mapping:
            chain_mapping[chain_name] = {"https": [], "wss": []}

        rpc_urls = chain.get("rpc_urls") or []
        for url in rpc_urls:
            if not isinstance(url, str):
                continue

            url_lower = url.lower().strip()
            try:
                parsed_url = urlparse(url_lower)
                if parsed_url.scheme in ("ws", "wss"):
                    chain_mapping[chain_name]["wss"].append(url.strip())
                elif parsed_url.scheme in ("http", "https"):
                    chain_mapping[chain_name]["https"].append(url.strip())
            except Exception:
                # Log error or pass; continuing is safer than returning a completely empty dict
                continue

    return chain_mapping
