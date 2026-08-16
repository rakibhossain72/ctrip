"""
Wallet key manager package.

Exports the ``WalletKeyManager`` class used for deterministic wallet
derivation, signing, and address generation.
"""

from .manager import WalletKeyManager

__all__ = ["WalletKeyManager"]
