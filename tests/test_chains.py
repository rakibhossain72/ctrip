"""Unit tests for app/blockchain/chains.py config loader."""

import pytest

from app.blockchain import chains


@pytest.fixture
def yaml_chains(tmp_path, monkeypatch):
    """Point the loader at a temp chains.yaml with mixed key forms."""
    yaml_file = tmp_path / "chains.yaml"
    yaml_file.write_text("""
- name: ethereum
  rpc_urls:
    - https://eth.example/1
    - https://eth.example/2
  ws_url: wss://eth.example/ws
  chain_id: 1
  poa: false
- name: BSC
  rpc_url: https://bsc.example
  chain_id: 56
- name: no_url
  chain_id: 99
- name: disabled
  rpc_urls: []
  chain_id: 123
""")
    monkeypatch.setattr(chains.settings, "chains_yaml_path", str(yaml_file))
    chains.load_chains.cache_clear()
    try:
        yield
    finally:
        chains.load_chains.cache_clear()


def test_load_chains_normalizes_forms(yaml_chains):
    loaded = chains.load_chains()
    names = {c.name for c in loaded}
    assert names == {"ethereum", "bsc"}

    eth = next(c for c in loaded if c.name == "ethereum")
    assert eth.chain_id == 1
    assert eth.http_urls == ("https://eth.example/1", "https://eth.example/2")
    assert eth.ws_urls == ("wss://eth.example/ws",)
    assert eth.poa is False

    bsc = next(c for c in loaded if c.name == "bsc")
    assert bsc.chain_id == 56
    assert bsc.http_urls == ("https://bsc.example",)
    assert bsc.ws_urls == ()


def test_lookups(yaml_chains):
    assert chains.chain_by_id(1).name == "ethereum"
    assert chains.chain_by_name("BSC").chain_id == 56
    assert chains.chain_by_name("bsc").chain_id == 56  # case-insensitive
    assert chains.chain_by_id(999) is None
    assert chains.chain_name_for_id(1) == "ethereum"
    assert chains.chain_name_for_id(999) == "999"
    assert chains.chain_id_for_name("ethereum") == 1
    assert chains.enabled_chain_ids() == frozenset({1, 56})


def test_default_fallback_when_no_yaml(tmp_path, monkeypatch):
    monkeypatch.setattr(
        chains.settings, "chains_yaml_path", str(tmp_path / "missing.yaml")
    )
    chains.load_chains.cache_clear()
    try:
        loaded = chains.load_chains()
        assert len(loaded) == 1
        assert loaded[0].name == "anvil"
        assert loaded[0].chain_id == 31337
    finally:
        chains.load_chains.cache_clear()
