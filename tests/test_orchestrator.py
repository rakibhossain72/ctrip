"""Unit tests for scanner/orchestrator.py range/cursor logic (no I/O)."""

from scanner.orchestrator import _scan_chain


class FakeCursor:
    def __init__(self):
        self.values: dict[int, int] = {}
        self.deleted: list[int] = []

    async def get(self, chain_id):
        return self.values.get(chain_id)

    async def set(self, chain_id, block):
        self.values[chain_id] = block

    async def all_chain_ids(self):
        return set(self.values)

    async def delete(self, chain_id):
        self.deleted.append(chain_id)
        self.values.pop(chain_id, None)


class FakeBlockchain:
    def __init__(self, current: int):
        self.current = current
        self.calls = 0

    async def get_current_block(self, chain_id: int) -> int:
        self.calls += 1
        return self.current


class FakeArqPool:
    def __init__(self):
        self.jobs: list[tuple] = []

    async def enqueue_job(self, name, *args):
        self.jobs.append((name, args))


def _ctx(cursor, blockchain, pool) -> dict:
    return {"cursor": cursor, "blockchain_service": blockchain, "arq_pool": pool}


async def test_seeds_cursor_on_first_run():
    cursor = FakeCursor()
    pool = FakeArqPool()
    blockchain = FakeBlockchain(current=1000)
    await _scan_chain(
        _ctx(cursor, blockchain, pool), 1, {"native": True, "tokens": set()}
    )
    assert cursor.values == {1: 999}
    assert pool.jobs == []


async def test_queues_native_and_token_jobs():
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
    from scanner.constants import MAX_BLOCKS_PER_TICK

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
    cursor = FakeCursor()
    cursor.values[1] = 1000
    pool = FakeArqPool()
    blockchain = FakeBlockchain(current=1000)
    await _scan_chain(
        _ctx(cursor, blockchain, pool), 1, {"native": True, "tokens": set()}
    )
    assert pool.jobs == []
    assert cursor.values[1] == 1000


async def test_noop_when_no_targets():
    cursor = FakeCursor()
    pool = FakeArqPool()
    blockchain = FakeBlockchain(current=100)
    await _scan_chain(
        _ctx(cursor, blockchain, pool), 1, {"native": False, "tokens": set()}
    )
    assert pool.jobs == []
    assert cursor.values == {1: 99}  # cursor still seeded
