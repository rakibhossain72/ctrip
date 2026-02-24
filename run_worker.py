#!/usr/bin/env python3
"""
Start the ARQ worker process.

Usage:
    python run_worker.py
"""
from arq import run_worker
from app.workers.worker import WorkerSettings

if __name__ == '__main__':
    run_worker(WorkerSettings)
