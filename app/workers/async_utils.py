"""
Asynchronous utilities for background workers.
"""
import asyncio
import threading
from typing import Any, Coroutine, TypeVar

T = TypeVar("T")

class _AsyncWorker:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def run_sync(self, coro: Coroutine[Any, Any, T]) -> T:
        """Run a coroutine in the background thread's event loop and wait for result."""
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result()

def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """
    Helper to run async code from a synchronous context (like a Dramatiq actor).
    Uses a single background event loop per process to avoid 'different event loop' issues
    with shared objects like SQLAlchemy engines.
    """
    return _AsyncWorker.get_instance().run_sync(coro)
