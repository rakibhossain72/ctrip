from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Optional, TypeVar

from app.core.logger import listener_logger as log

T = TypeVar("T")


class RetryPolicy:
    """Handles retrying async operations with exponential backoff."""

    def __init__(self, max_retries: int, backoff: float) -> None:
        self.max_retries = max_retries
        self.backoff = backoff

    async def run(
        self,
        description: str,
        coro_fn: Callable[..., Awaitable[T]],
        *args,
    ) -> Optional[T]:
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return await coro_fn(*args)
            except Exception as e:
                last_exc = e
                if attempt < self.max_retries:
                    delay = self.backoff**attempt
                    log.warning(
                        f"{description} failed (attempt {attempt}/{self.max_retries}): {e}. "
                        f"Retrying in {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
        log.error(f"{description} failed after {self.max_retries} attempts: {last_exc}")
        return None
