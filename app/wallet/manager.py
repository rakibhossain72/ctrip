import hashlib
import hmac
import secrets

from typing import Optional

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_account.signers.local import LocalAccount
from app.schemas.wallet import DerivedWallet, SignedMessage


class WalletKeyManager:
    """
    Manages deterministic Ethereum wallet derivation and key operations.

    Wallets are derived deterministically from a user subject identifier (`sub`),
    a key version, and an optional recovery key — using HKDF over a server secret.

    Usage:
        manager = WalletKeyManager("secret_a", "secret_b")
        wallet  = manager.derive_wallet("user-123")
        signed  = manager.sign_message("user-123", "Hello, world")
        ok      = manager.verify_signature("Hello, world", signed.signature, wallet.address)
    """

    def __init__(self, server_secret_a: str, server_secret_b: str) -> None:
        self._hash_algo = "sha256"
        self._master_secret: bytes = (f"{server_secret_a}{server_secret_b}").encode()

    # Public API
    def derive_wallet(
        self,
        payment_id: str,
        key_version: int = 1,
        recovery_key: str = "",
    ) -> DerivedWallet:
        """
        Derive a complete wallet (address + private key) for a given user subject.

        Args:
            payment_id:          Unique payment id to claim.
            key_version:  Increment to rotate the wallet for this user.
            recovery_key: Optional extra entropy supplied by the user.

        Returns:
            A frozen DerivedWallet dataclass.
        """
        seed = self._derive_seed(payment_id, key_version, recovery_key)
        private_key = self._derive_private_key(seed)
        address = self._derive_address(private_key)
        return DerivedWallet(
            address=address,
            private_key=private_key,
            payment_id=payment_id,
            key_version=key_version,
        )

    def derive_address(
        self,
        payment_id: str,
        key_version: int = 1,
        recovery_key: str = "",
    ) -> str:
        """Return only the Ethereum address for a subject (no private key exposed)."""
        return self.derive_wallet(payment_id, key_version, recovery_key).address

    def sign_message(
        self,
        payment_id: str,
        message: str,
        key_version: int = 1,
        recovery_key: str = "",
    ) -> SignedMessage:
        """
        Sign an arbitrary text message with the user's derived private key.

        Returns a SignedMessage containing the EIP-191 signature and message hash.
        """
        wallet = self.derive_wallet(payment_id, key_version, recovery_key)
        account: LocalAccount = Account.from_key(wallet.private_key)
        signable = encode_defunct(text=message)
        signed = account.sign_message(signable)
        return SignedMessage(
            message=message,
            signature=signed.signature.hex(),
            signer_address=account.address,
            message_hash=signed.message_hash.hex(),
        )

    def verify_signature(
        self,
        message: str,
        signature: str,
        expected_address: str,
    ) -> bool:
        """
        Verify an EIP-191 signed message against an expected Ethereum address.

        Args:
            message:          The original plaintext message.
            signature:        Hex-encoded signature string (with or without 0x prefix).
            expected_address: Ethereum address the signature should recover to.

        Returns:
            True if the signature was produced by expected_address, False otherwise.
        """
        try:
            signable = encode_defunct(text=message)
            recovered = Account.recover_message(signable, signature=signature)
            return recovered.lower() == expected_address.lower()
        except Exception:
            return False

    def rotate_wallet(
        self,
        payment_id: str,
        current_version: int,
        recovery_key: str = "",
    ) -> DerivedWallet:
        """
        Derive the next key version for a user (key rotation).

        Returns the new wallet; callers are responsible for migrating funds.
        """
        return self.derive_wallet(payment_id, current_version + 1, recovery_key)

    @staticmethod
    def generate_recovery_key(nbytes: int = 32) -> str:
        """
        Generate a cryptographically secure random recovery key.

        The caller must store this securely; it is not persisted here.
        """
        return secrets.token_hex(nbytes)

    def batch_derive_addresses(
        self,
        payment_ids: list[str],
        key_version: int = 1,
    ) -> dict[str, str]:
        """
        Derive addresses for multiple subjects at once.

        Returns:
            A dict mapping each payment_id → Ethereum address.
        """
        return {
            payment_id: self.derive_address(payment_id, key_version)
            for payment_id in payment_ids
        }

    # Private helper
    def _derive_seed(
        self,
        payment_id: str,
        key_version: int = 1,
        recovery_key: str = "",
    ) -> bytes:
        """Produce a deterministic seed via HKDF for the given subject."""
        info = f"{str(payment_id)}:v{key_version}:{recovery_key}".encode()
        return self._hkdf(ikm=self._master_secret, info=info)

    @staticmethod
    def _derive_private_key(seed: bytes) -> str:
        """Derive a 32-byte Ethereum private key from a seed."""
        return hashlib.sha256(seed).hexdigest()

    @staticmethod
    def _derive_address(private_key: str) -> str:
        """Return the checksummed Ethereum address for a private key."""
        account: LocalAccount = Account.from_key(private_key)
        return account.address

    def _hkdf(
        self,
        ikm: bytes,
        info: bytes = b"",
        salt: Optional[bytes] = None,
        length: int = 32,
    ) -> bytes:
        """
        RFC 5869 HKDF — Extract-then-Expand key derivation.

        Args:
            ikm:    Input Key Material.
            info:   Binding context (sub, version, recovery key).
            salt:   Optional random salt; defaults to zero-filled bytes per RFC.
            length: Output length in bytes.
        """
        if length <= 0:
            raise ValueError("length must be a positive integer")

        hash_func = getattr(hashlib, self._hash_algo)
        hash_len: int = hash_func().digest_size

        if length > 255 * hash_len:
            raise ValueError(
                f"Requested length {length} exceeds HKDF max "
                f"({255 * hash_len} bytes for {self._hash_algo})"
            )

        # Extract
        if salt is None:
            salt = b"\x00" * hash_len
        prk = hmac.new(salt, ikm, hash_func).digest()

        # Expand
        t = b""
        okm = b""
        counter = 1
        while len(okm) < length:
            t = hmac.new(prk, t + info + bytes([counter]), hash_func).digest()
            okm += t
            counter += 1

        return okm[:length]
