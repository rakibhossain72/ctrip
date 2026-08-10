from __future__ import annotations

NATIVE_ASSET = "native"

# keccak256("Transfer(address,address,uint256)")
ERC20_TRANSFER_TOPIC = (
    "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
)

# Redis cursor key per chain
CURSOR_KEY = "last_scanned_block:{chain_id}"

# Safety cap so one tick never tries to enqueue an unbounded block range
MAX_BLOCKS_PER_TICK = 500

# Block depth required before a detected payment is promoted to CONFIRMED
CONFIRMATIONS_REQUIRED = 1
