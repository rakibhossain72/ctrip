"""
Utility for accessing the AsyncWeb3 instance for a given chain name.
"""
from web3 import AsyncWeb3
from app.blockchain.manager import get_blockchains

_blockchains = get_blockchains()


def get_w3(chain_name: str) -> AsyncWeb3:
    """Return the AsyncWeb3 instance for a configured chain."""
    if chain_name not in _blockchains:
        raise ValueError(f"Blockchain '{chain_name}' not configured")
    return _blockchains[chain_name].w3
