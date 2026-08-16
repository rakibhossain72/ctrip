"""
Initializes EVMClient instances from the canonical chain configuration.

See `app/blockchain/chains.py` for the supported chains.yaml schema.
"""

import os
from typing import Dict

from web3 import AsyncWeb3

from app.blockchain.chains import load_chains
from app.blockchain.client import EVMClient
from app.core.logger import logger


def get_blockchains() -> Dict[str, EVMClient]:
    """
    Build an EVMClient for every chain defined in chains.yaml,
    keyed by lowercase chain name.
    """
    clients: Dict[str, EVMClient] = {}

    for chain in load_chains():
        clients[chain.name] = EVMClient(
            rpc_urls=list(chain.http_urls),
            chain_id=chain.chain_id,
            poa=chain.poa,
        )
        logger.info(
            "Registered chain '%s' (id=%s) with %d endpoint(s): %s",
            chain.name,
            chain.chain_id,
            len(chain.http_urls),
            chain.http_urls[0] if len(chain.http_urls) == 1 else chain.http_urls,
        )

    if not clients:  # pragma: no cover - loader always returns a fallback chain
        fallback_url = (
            "http://host.docker.internal:8545"
            if os.path.exists("/.dockerenv")
            else "http://localhost:8545"
        )
        logger.warning(
            "No chains configured — falling back to local node at %s", fallback_url
        )
        clients["anvil"] = EVMClient(rpc_urls=[fallback_url], chain_id=31337)

    return clients


def get_w3(chain_name: str) -> AsyncWeb3:
    """Return the AsyncWeb3 instance for a configured chain."""
    _blockchains = get_blockchains()

    if chain_name not in _blockchains:
        raise ValueError(f"Blockchain '{chain_name}' not configured")
    return _blockchains[chain_name].w3
