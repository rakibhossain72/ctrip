"""
Initializes EVMClient instances from chains.yaml configuration.

Each chain entry supports a single endpoint or a prioritised fallback list:

  # single endpoint
  - name: ethereum
    rpc_url: https://mainnet.infura.io/v3/KEY

  # multiple endpoints — tried in order on failure
  - name: ethereum
    rpc_urls:
      - https://mainnet.infura.io/v3/KEY
      - https://eth-mainnet.g.alchemy.com/v2/KEY
      - https://rpc.ankr.com/eth
    chain_id: 1
    poa: false
"""
import logging
import os
from typing import Dict, List

from app.core.config import settings
from app.blockchain.client import EVMClient

logger = logging.getLogger(__name__)


def _resolve_urls(chain_cfg: dict) -> List[str]:
    """
    Return the ordered list of RPC URLs for a chain config entry.
    Accepts either:
      - rpc_urls: [url, url, …]   (list — preferred)
      - rpc_url: url              (single string — backward-compatible)
    Both keys may coexist; rpc_urls takes priority and rpc_url is appended
    if not already present, so users can mix them freely.
    """
    urls: List[str] = []

    # List form
    for entry in chain_cfg.get("rpc_urls") or []:
        if entry and entry not in urls:
            urls.append(entry)

    # Single-URL form (backward-compatible)
    single = chain_cfg.get("rpc_url")
    if single and single not in urls:
        urls.append(single)

    return urls


def get_blockchains() -> Dict[str, EVMClient]:
    """
    Build an EVMClient for every chain defined in chains.yaml.
    """
    clients: Dict[str, EVMClient] = {}

    for chain_cfg in settings.chains:
        name = (chain_cfg.get("name") or "").lower().strip()
        urls = _resolve_urls(chain_cfg)

        if not name:
            logger.warning("Skipping chain entry with missing name: %s", chain_cfg)
            continue
        if not urls:
            logger.warning("Skipping chain '%s' — no rpc_url / rpc_urls provided", name)
            continue

        clients[name] = EVMClient(
            rpc_urls=urls,
            chain_id=chain_cfg.get("chain_id"),   # None -> fetched lazily
            poa=bool(chain_cfg.get("poa", False)),
        )
        logger.info(
            "Registered chain '%s' with %d endpoint(s): %s",
            name, len(urls), urls[0] if len(urls) == 1 else urls,
        )

    if not clients:
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
