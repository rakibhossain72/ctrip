"""
API initialization and routing.
"""
from .dependencies import get_blockchains, get_wallet_manager
from .health import health_router

__all__ = ["health_router", "get_blockchains","get_wallet_manager"]
