from __future__ import annotations

from app.blockchain.chains import (
    ChainConfig,
    chain_by_id,
    chain_by_name,
    chain_id_for_name,
    chain_name_for_id,
    enabled_chain_ids,
    load_chains,
)

Chain = ChainConfig


def get_enabled_chains() -> list[ChainConfig]:
    """Return the configured chains as a list of ChainConfig."""
    return list(load_chains())


def get_enabled_chain_ids() -> list[int]:
    """Return the chain IDs of all enabled chains."""
    return sorted(enabled_chain_ids())


__all__ = [
    "Chain",
    "ChainConfig",
    "chain_by_id",
    "chain_by_name",
    "chain_id_for_name",
    "chain_name_for_id",
    "enabled_chain_ids",
    "get_enabled_chains",
    "get_enabled_chain_ids",
    "load_chains",
]
