"""
Re-export ABI loaders for ERC-20 and Multicall3 contracts.
"""

from app.blockchain.ABI.abis import get_erc20_abi, get_multicall_abi

__all__ = ["get_erc20_abi", "get_multicall_abi"]
