"""
FastAPI dependencies for shared components like blockchains and HD wallet.
"""
from fastapi import Request
from app.utils.crypto import HDWalletManager


def get_blockchains(request: Request):
    """Dependency to access initialized blockchains from app state."""
    # pylint: disable=no-member
    return request.app.state.blockchains


def get_hdwallet(request: Request) -> HDWalletManager:
    """Dependency to access the HD wallet manager from app state."""
    # pylint: disable=no-member
    return request.app.state.hdwallet
