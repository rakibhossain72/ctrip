"""Unit tests for scanner/matching.py — pure decode/match logic, no I/O."""

from scanner.matching import (
    addresses_to_topics,
    decode_erc20_transfer,
    decode_topic_address,
    match_native_tx,
    normalize_address,
    topic_from_address,
)

TOKEN = "0x6b175474e89094c44da98b954eedeac495271d0f"
FROM = "0x5a1b98fdff44a56f1fcf7cc9b14b259f59de3734"
TO = "0x7b79995e5f793a07bc00c21412e50ecae098e7f9"
AMOUNT = 1_000_000_000_000_000_000
TOPIC0 = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def _bytes_log() -> dict:
    return {
        "address": bytes.fromhex(TOKEN[2:]),
        "topics": [
            bytes.fromhex(TOPIC0[2:]),
            bytes.fromhex(topic_from_address(FROM)[2:]),
            bytes.fromhex(topic_from_address(TO)[2:]),
        ],
        "data": AMOUNT.to_bytes(32, "big"),
        "transactionHash": bytes.fromhex("ab" * 32),
        "blockNumber": 42,
        "logIndex": 3,
    }


def _hex_log() -> dict:
    log = _bytes_log()
    return {
        "address": "0x" + log["address"].hex(),
        "topics": ["0x" + t.hex() for t in log["topics"]],
        "data": "0x" + log["data"].hex(),
        "transactionHash": "0x" + log["transactionHash"].hex(),
        "blockNumber": 42,
        "logIndex": 3,
    }


def test_decode_erc20_bytes_form():
    """Decode an ERC-20 Transfer log with bytes-typed fields."""
    ev = decode_erc20_transfer(_bytes_log(), 11155111)
    assert ev is not None
    assert ev.token == TOKEN
    assert ev.to == TO
    assert ev.from_ == FROM
    assert ev.amount == AMOUNT
    assert ev.tx_hash == "0x" + "ab" * 32
    assert ev.log_index == 3
    assert ev.block_number == 42
    assert ev.chain_id == 11155111


def test_decode_erc20_hex_str_form():
    """Decode an ERC-20 Transfer log with hex-string fields."""
    ev = decode_erc20_transfer(_hex_log(), 1)
    assert ev is not None
    assert ev.to == TO and ev.amount == AMOUNT


def test_decode_rejects_malformed():
    """Malformed logs should return None."""
    assert decode_erc20_transfer({"topics": []}, 1) is None
    assert decode_erc20_transfer({"topics": ["0x" + "0" * 66]}, 1) is None
    assert (
        decode_erc20_transfer({"topics": [TOPIC0, "0x" + "0" * 64, "0x" + "0" * 64]}, 1)
        is None
    )


def test_topic_helpers_roundtrip():
    """Topic encoding/decoding should be reversible."""
    assert topic_from_address(TO) == "0x" + "0" * 24 + TO[2:]
    assert addresses_to_topics([TO]) == [topic_from_address(TO)]
    assert addresses_to_topics([]) is None
    assert addresses_to_topics(None) is None
    decoded = decode_topic_address(_bytes_log()["topics"][2])
    assert decoded == TO
    assert decode_topic_address("0xzz") is None
    assert decode_topic_address(None) is None


def test_match_native_tx():
    """Native tx matching should find watched recipient addresses."""
    watched = {TO}
    assert match_native_tx({"to": TO, "value": 1}, watched) == TO
    assert match_native_tx({"to": TO.upper()}, watched) == TO
    assert match_native_tx({"to": "0xdead", "value": 1}, watched) is None
    assert match_native_tx({"to": None, "value": 1}, watched) is None
    assert match_native_tx({}, set()) is None


def test_normalize_address():
    """Address normalization should lowercase and strip prefixes."""
    assert normalize_address(TO) == TO
    assert normalize_address(TO.upper()) == TO
    assert normalize_address(bytes.fromhex(TO[2:])) == TO
    assert normalize_address(None) == ""
