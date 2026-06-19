"""
API initialization and routing.
"""
from .health import health_router
from .dependencies import get_blockchains, get_wallet_manager

__all__ = ["health_router", "get_blockchains","get_wallet_manager"]
