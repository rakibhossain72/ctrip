"""
Blockchain service facade for the scanner.

Wraps EVMClient instances so the scanner can query blocks, transactions,
and logs without knowing about RPC failover details.
"""

from .service import BlockchainService

__all__ = ["BlockchainService"]
