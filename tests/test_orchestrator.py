"""Unit tests for scanner/orchestrator.py range/cursor logic (no I/O)."""

from scanner.constants import MAX_BLOCKS_PER_TICK
from scanner.orchestrator import _scan_chain


class FakeCursor:
    """In-memory stand-in for RedisCursor."""

    def __init__(self):
        self.values: dict[int, int] = {}
        self.deleted: list[int] = []

    async def get(self, chain_id):
        """Return the last scanned block for a chain."""
        return self.values.get(chain_id)

    async def set(self, chain_id, block):
        """Store the last scanned block for a chain."""
        self.values[chain_id] = block

    async def all_chain_ids(self):
        """Return all chain IDs that have a stored cursor."""
        return set(self.values)

    async def delete(self, chain_id):
        """Delete the stored cursor for a chain."""
        self.deleted.append(chain_id)
        self.values.pop(chain_id, None)


class FakeBlockchain:
    """Stand-in for the blockchain service with a fixed current block."""

    def __init__(self, current: int):
        self.current = current
        self.calls = 0

    async def get_current_block(self, _chain_id: int) -> int:
        """Return the fixed current block."""
        self.calls += 1
        return self.current


class FakeArqPool:
    """Stand-in for the ARQ job pool that records enqueued jobs."""

    def __init__(self):
        self.jobs: list[tuple] = []

    async def enqueue_job(self, name, *_args):
        """Record a job for later assertions."""
        self.jobs.append((name, _args))


def _ctx(cursor, blockchain, pool) -> dict:
    return {"cursor": cursor, "blockchain_service": blockchain, "arq_pool": pool}


async def test_seeds_cursor_on_first_run():
    """On first run the cursor should be seeded at current_block - 1."""
    cursor = FakeCursor()
    pool = FakeArqPool()
    blockchain = FakeBlockchain(current=1000)
    await _scan_chain(
        _ctx(cursor, blockchain, pool), 1, {"native": True, "tokens": set()}
    )
    assert cursor.values == {1: 999}
    assert not pool.jobs


async def test_queues_native_and_token_jobs():
    """Should enqueue both native and ERC-20 jobs for the block range."""
    cursor = FakeCursor()
    cursor.values[1] = 500
    pool = FakeArqPool()
    blockchain = FakeBlockchain(current=520)
    spec = {"native": True, "tokens": {"0xabc"}}
    await _scan_chain(_ctx(cursor, blockchain, pool), 1, spec)
    assert pool.jobs == [
        ("check_native_transactions", (1, list(range(501, 521)))),
        ("check_erc20_transfer_logs", (1, "0xabc", 501, 520)),
    ]
    assert cursor.values[1] == 520


async def test_respects_max_blocks_per_tick():
    """Scan range should be capped at MAX_BLOCKS_PER_TICK."""
    cursor = FakeCursor()
    cursor.values[1] = 1000
    pool = FakeArqPool()
    blockchain = FakeBlockchain(current=1000 + MAX_BLOCKS_PER_TICK + 100)
    await _scan_chain(
        _ctx(cursor, blockchain, pool), 1, {"native": True, "tokens": set()}
    )
    assert pool.jobs == [
        (
            "check_native_transactions",
            (1, list(range(1001, 1001 + MAX_BLOCKS_PER_TICK))),
        )
    ]
    assert cursor.values[1] == 1000 + MAX_BLOCKS_PER_TICK


async def test_noop_when_cursor_is_current():
    """Should do nothing when cursor already matches current block."""
    cursor = FakeCursor()
    cursor.values[1] = 1000
    pool = FakeArqPool()
    blockchain = FakeBlockchain(current=1000)
    await _scan_chain(
        _ctx(cursor, blockchain, pool), 1, {"native": True, "tokens": set()}
    )
    assert not pool.jobs
    assert cursor.values[1] == 1000


async def test_noop_when_no_targets():
    """Should seed cursor but enqueue no jobs when spec is empty."""
    cursor = FakeCursor()
    pool = FakeArqPool()
    blockchain = FakeBlockchain(current=100)
    await _scan_chain(
        _ctx(cursor, blockchain, pool), 1, {"native": False, "tokens": set()}
    )
    assert not pool.jobs
    assert cursor.values == {1: 99}  # cursor still seeded
