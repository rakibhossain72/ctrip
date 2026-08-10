"""
Canonical chain configuration loader.

All consumers (API, worker, scanner) read chain config through this module so
the `chains.yaml` schema is defined once. Accepted YAML forms:

  - name: ethereum                (required)
    rpc_urls: [url, ...]          (ordered HTTP RPC endpoints; preferred)
    rpc_url: url                  (single HTTP endpoint; backward-compatible)
    ws_urls: [url, ...]           (WebSocket endpoints for real-time use)
    ws_url: url                   (single WebSocket endpoint)
    chain_id: 1                   (auto-fetched from node if omitted)
    poa: false                    (set true for PoA networks)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional, Sequence

import yaml

from app.core.config import settings


@dataclass(frozen=True)
class ChainConfig:
    """Normalized, validated chain configuration."""

    name: str
    chain_id: int
    http_urls: tuple[str, ...]
    ws_urls: tuple[str, ...]
    poa: bool

    @property
    def primary_http_url(self) -> str:
        return self.http_urls[0]


def _normalize_urls(
    url: Optional[str], urls: Optional[Sequence[str]]
) -> tuple[str, ...]:
    """Merge the single-URL and list forms into one ordered tuple."""
    merged: list[str] = []
    for entry in urls or []:
        if entry and entry not in merged:
            merged.append(entry)
    if url and url not in merged:
        merged.append(url)
    return tuple(merged)


def _rewrite_for_docker(url: str) -> str:
    """Rewrite localhost RPC hosts when running inside a container."""
    if not os.path.exists("/.dockerenv"):
        return url
    return url.replace("localhost", "host.docker.internal").replace(
        "127.0.0.1", "host.docker.internal"
    )


@lru_cache(maxsize=1)
def load_chains() -> tuple[ChainConfig, ...]:
    """Parse chains.yaml into a cached tuple of ChainConfig."""
    path = settings.chains_yaml_path
    if not os.path.exists(path):
        return _default_chain()

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or []
    except Exception:  # pragma: no cover - defensive
        return _default_chain()

    chains: list[ChainConfig] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = (entry.get("name") or "").lower().strip()
        if not name:
            continue

        http_urls = tuple(
            _rewrite_for_docker(u)
            for u in _normalize_urls(
                entry.get("http_url") or entry.get("rpc_url"),
                entry.get("http_urls") or entry.get("rpc_urls"),
            )
        )
        ws_urls = tuple(
            _rewrite_for_docker(u)
            for u in _normalize_urls(entry.get("ws_url"), entry.get("ws_urls"))
        )
        if not http_urls:
            continue

        chain_id = entry.get("chain_id")
        if chain_id is None:
            chain_id = name  # placeholder; resolved at connect time
        chains.append(
            ChainConfig(
                name=name,
                chain_id=int(chain_id),
                http_urls=http_urls,
                ws_urls=ws_urls,
                poa=bool(entry.get("poa", False)),
            )
        )

    if not chains:
        return _default_chain()
    return tuple(chains)


def _default_chain() -> tuple[ChainConfig, ...]:
    """Fallback local node (Anvil) when nothing is configured."""
    host = "host.docker.internal" if os.path.exists("/.dockerenv") else "localhost"
    return (
        ChainConfig(
            name="anvil",
            chain_id=31337,
            http_urls=(f"http://{host}:8545",),
            ws_urls=(),
            poa=False,
        ),
    )


def chain_by_id(chain_id: int) -> Optional[ChainConfig]:
    for chain in load_chains():
        if chain.chain_id == chain_id:
            return chain
    return None


def chain_by_name(name: str) -> Optional[ChainConfig]:
    lowered = name.lower()
    for chain in load_chains():
        if chain.name == lowered:
            return chain
    return None


def enabled_chain_ids() -> frozenset[int]:
    return frozenset(c.chain_id for c in load_chains())


def chain_name_for_id(chain_id: int) -> str:
    chain = chain_by_id(chain_id)
    return chain.name if chain else str(chain_id)


def chain_id_for_name(name: str) -> Optional[int]:
    chain = chain_by_name(name)
    return chain.chain_id if chain else None
