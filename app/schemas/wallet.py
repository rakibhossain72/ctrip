"""
Dataclass containers for derived wallets and signed messages.
"""

from dataclasses import dataclass


# Data containers
@dataclass(frozen=True)
class DerivedWallet:
    """Deterministically derived wallet (address, private key, metadata)."""
    private_key: str
    payment_id: str
    key_version: int

    def __repr__(self) -> str:
        return (
            f"DerivedWallet(address={self.address!r}, "
            f"payment_id={self.payment_id!r}, key_version={self.key_version})"
        )


@dataclass
class SignedMessage:
    """EIP-191 signed message with signature and signer address."""
    signature: str
    signer_address: str
    message_hash: str
