"""
Initializes EVMClient instances from chains.yaml configuration.
"""

import logging
import os
from typing import Dict

from app.core.config import settings
from app.blockchain.client import EVMClient

logger = logging.getLogger(__name__)


def get_blockchains() -> Dict[str, EVMClient]:
    """
    Build an EVMClient for every chain defined in chains.yaml.

    Each chain entry may include:
      - name     (required) — used as the dict key
      - rpc_url  (required) — HTTP or WebSocket RPC endpoint
      - chain_id (optional) — override; auto-fetched from the node if omitted
      - poa      (optional) — set true for PoA networks (BSC, Polygon, …)
    """
    clients: Dict[str, EVMClient] = {}

    for chain_cfg in settings.chains:
        name = (chain_cfg.get("name") or "").lower().strip()
        rpc_url = chain_cfg.get("rpc_url")

        if not name or not rpc_url:
            logger.warning(
                "Skipping chain entry with missing name or rpc_url: %s", chain_cfg
            )
            continue

        clients[name] = EVMClient(
            provider_url=rpc_url,
            chain_id=chain_cfg.get("chain_id"),  # None → fetched lazily
            poa=bool(chain_cfg.get("poa", False)),
        )
        logger.info("Registered chain '%s' → %s", name, rpc_url)

    if not clients:
        fallback_url = (
            "http://host.docker.internal:8545"
            if os.path.exists("/.dockerenv")
            else "http://localhost:8545"
        )
        logger.warning(
            "No chains configured — falling back to local node at %s", fallback_url
        )
        clients["anvil"] = EVMClient(provider_url=fallback_url, chain_id=31337)

    return clients
