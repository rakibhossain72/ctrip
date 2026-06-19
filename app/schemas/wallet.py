from dataclasses import dataclass


# Data containers
@dataclass(frozen=True)
class DerivedWallet:
    address: str
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
    message: str
    signature: str
    signer_address: str
    message_hash: str
