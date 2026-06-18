#!/usr/bin/env python3
"""
Start the ARQ worker process.

Usage:
    python run_worker.py
"""
import asyncio

from arq import run_worker
from app.workers.worker import WorkerSettings

if __name__ == '__main__':
    # Python 3.10+ no longer implicitly creates an event loop outside async
    # context, so we create one explicitly before handing off to ARQ.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        run_worker(WorkerSettings)
    finally:
        loop.close()
