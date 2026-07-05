from __future__ import annotations

import logging
import threading
from collections import defaultdict
from typing import Callable, DefaultDict, Iterator
from eth_utils import is_address

logger = logging.getLogger(__name__)

NATIVE_ASSET = "native"


def default_address_validator(address: str) -> bool:
    return is_address(address)


class PaymentRegistryError(ValueError):
    """Raised on invalid input to the registry (bad address, bad chain id, etc.)."""


class PaymentRegistry:
    """
    Thread-safe registry of payment addresses per chain/asset.

    Structure:
        {
            chain_id: {
                asset: {address1, address2, ...}
            }
        }

    asset:
        - "native"
        - token contract address (lowercase)

    All addresses are stored lowercase. Address format is validated on
    write (see `address_validator`); pass a custom validator if you need
    to support non-EVM address formats.
    """

    def __init__(
        self,
        *,
        address_validator: Callable[[str], bool] = default_address_validator,
    ) -> None:
        self._registry: DefaultDict[int, DefaultDict[str, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        self._validate_address = address_validator
        self._lock = threading.RLock()

    # Validation helpers
    @staticmethod
    def _normalize(address: str) -> str:
        return address.strip().lower()

    def _validate(self, *, chain_id: int, address: str, asset: str) -> tuple[str, str]:
        if not isinstance(chain_id, int) or isinstance(chain_id, bool) or chain_id < 0:
            raise PaymentRegistryError(f"Invalid chain_id: {chain_id!r}")

        if not isinstance(address, str) or not address:
            raise PaymentRegistryError(f"Invalid address: {address!r}")

        normalized_address = self._normalize(address)
        if not self._validate_address(normalized_address):
            raise PaymentRegistryError(f"Address failed validation: {address!r}")

        if not isinstance(asset, str) or not asset:
            raise PaymentRegistryError(f"Invalid asset: {asset!r}")

        normalized_asset = asset.strip().lower()
        if normalized_asset != NATIVE_ASSET and not self._validate_address(
            normalized_asset
        ):
            raise PaymentRegistryError(
                f"Asset must be 'native' or a valid address: {asset!r}"
            )

        return normalized_address, normalized_asset

    # Mutation
    def add(
        self,
        *,
        chain_id: int,
        address: str,
        asset: str = NATIVE_ASSET,
    ) -> bool:
        """Add an address. Returns True if newly added, False if it already existed."""
        normalized_address, normalized_asset = self._validate(
            chain_id=chain_id, address=address, asset=asset
        )
        with self._lock:
            bucket = self._registry[chain_id][normalized_asset]
            is_new = normalized_address not in bucket
            bucket.add(normalized_address)

        if is_new:
            logger.info(
                "payment_registry.add chain_id=%s asset=%s address=%s",
                chain_id,
                normalized_asset,
                normalized_address,
            )
        return is_new

    def add_many(
        self,
        *,
        chain_id: int,
        addresses: list[str],
        asset: str = NATIVE_ASSET,
    ) -> int:
        """Add multiple addresses at once. Returns count of newly added addresses."""
        added = 0
        with self._lock:
            for address in addresses:
                if self.add(chain_id=chain_id, address=address, asset=asset):
                    added += 1
        return added

    def remove(
        self,
        *,
        chain_id: int,
        address: str,
        asset: str = NATIVE_ASSET,
    ) -> bool:
        """Remove an address. Returns True if it was present and removed."""
        normalized_address = self._normalize(address)
        normalized_asset = asset.strip().lower()

        with self._lock:
            assets = self._registry.get(chain_id)
            if assets is None:
                return False

            bucket = assets.get(normalized_asset)
            if bucket is None or normalized_address not in bucket:
                return False

            bucket.discard(normalized_address)

            if not bucket:
                del assets[normalized_asset]
            if not assets:
                del self._registry[chain_id]

        logger.info(
            "payment_registry.remove chain_id=%s asset=%s address=%s",
            chain_id,
            normalized_asset,
            normalized_address,
        )
        return True

    def clear(self) -> None:
        with self._lock:
            count = len(self)
            self._registry.clear()
        logger.warning("payment_registry.clear removed_count=%s", count)

    # Queries (all read-only / return copies — safe to hand to callers)
    def contains(
        self,
        *,
        chain_id: int,
        address: str,
        asset: str = NATIVE_ASSET,
    ) -> bool:
        with self._lock:
            return self._normalize(address) in self._registry.get(chain_id, {}).get(
                asset.strip().lower(), set()
            )

    def addresses(
        self,
        *,
        chain_id: int,
        asset: str = NATIVE_ASSET,
    ) -> frozenset[str]:
        """Return an immutable snapshot — safe from external mutation."""
        with self._lock:
            return frozenset(
                self._registry.get(chain_id, {}).get(asset.strip().lower(), set())
            )

    def chains(self) -> frozenset[int]:
        with self._lock:
            return frozenset(self._registry.keys())

    def assets(self, *, chain_id: int) -> frozenset[str]:
        with self._lock:
            return frozenset(self._registry.get(chain_id, {}).keys())

    def to_dict(self) -> dict[int, dict[str, list[str]]]:
        """Serialize for persistence (JSON-friendly)."""
        with self._lock:
            return {
                chain_id: {asset: sorted(addrs) for asset, addrs in assets.items()}
                for chain_id, assets in self._registry.items()
            }

    @classmethod
    def from_dict(
        cls,
        data: dict[int, dict[str, list[str]]],
        *,
        address_validator: Callable[[str], bool] = default_address_validator,
    ) -> "PaymentRegistry":
        registry = cls(address_validator=address_validator)
        for chain_id, assets in data.items():
            for asset, addrs in assets.items():
                for address in addrs:
                    registry.add(chain_id=int(chain_id), address=address, asset=asset)
        return registry

    # Dunders
    def __contains__(self, item: tuple[int, str]) -> bool:
        """Supports `(chain_id, address) in registry` for the native asset."""
        chain_id, address = item
        return self.contains(chain_id=chain_id, address=address)

    def __iter__(self) -> Iterator[tuple[int, str, str]]:
        """Yields (chain_id, asset, address) triples."""
        with self._lock:
            for chain_id, assets in self._registry.items():
                for asset, addrs in assets.items():
                    for address in addrs:
                        yield chain_id, asset, address

    def __len__(self) -> int:
        with self._lock:
            return sum(
                len(addresses)
                for assets in self._registry.values()
                for addresses in assets.values()
            )

    def __repr__(self) -> str:
        return f"<PaymentRegistry addresses={len(self)}>"



if __name__ == "__main__":
    # Quick test
    registry = PaymentRegistry()
    registry.add(chain_id=1, address="0x7b79995e5f793A07Bc00c21412e50Ecae098E7f9")
    registry.add(
        chain_id=1,
        address="0x7b79995e5f793A07Bc00c21412e50Ecae098E7f9",
        asset="0x6B175474E89094C44Da98b954EedeAC495271d0F",
    )

    registry.add(chain_id=11155111, address="0x7b79995e5f793A07Bc00c21412e50Ecae098E7f9")
    
    
    valid_address = "0x6b175474e89094c44da98b954eedeac495271d0f"
    invalid_address = "0xINVALIDADDRESS00000000000000000000000000"

    print(f"Available chains: {registry.chains()}")

    print(f"Is {valid_address} valid? {default_address_validator(valid_address)}")
    print(f"Is {invalid_address} valid? {default_address_validator(invalid_address)}")

    print(f"Registry contains native address: {registry.contains(chain_id=1, address=invalid_address)}")
    print(f"Registry contains token address: {registry.contains(chain_id=1, address='0x7b79995e5f793A07Bc00c21412e50Ecae098E7f9', asset='0x6B175474E89094C44Da98b954EedeAC495271d0F')}")
    print(f"Registry addresses for chain 1, native asset: {registry.addresses(chain_id=1)}")
    print(f"Assests for chain 1: {registry.assets(chain_id=1)}")
    print(f"Addresses for chain 1, token asset: {registry.addresses(chain_id=1, asset='0x6B175474E89094C44Da98b954EedeAC495271d0F')}")
    print(f"Registry contains token address (invalid): {registry.contains(chain_id=1, address="0x7b79995e5f793a07bc00c21412e50ecae098e7f9", asset='0x6B175474E89094C44Da98b954EedeAC495271d0F')}")
    #  remove native address
    removed = registry.remove(chain_id=1, address="0x7b79995e5f793A07Bc00c21412e50Ecae098E7f9")
    print(f"Removed native address: {removed}")
    print(f"Registry addresses for chain 1, native asset: {registry.addresses(chain_id=1)}")
    
    # Remove token address
    removed_token = registry.remove(chain_id=1, address="0x7b79995e5f793A07Bc00c21412e50Ecae098E7f9", asset="0x6B175474E89094C44Da98b954EedeAC495271d0F")
    print(f"Removed token address: {removed_token}")
    print(f"Registry addresses for chain 1, token asset: {registry.addresses(chain_id=1, asset='0x6B175474E89094C44Da98b954EedeAC495271d0F')}")


    print(f"Assests for chain 1 after removals: {registry.assets(chain_id=1)}")