# Development & Operations

This document outlines operations, developer guidelines, testing, migrations, and local testing configurations for the cTrip Payment Gateway.

---

## Setting Up a Local Blockchain Sandbox (Anvil)

For fast local testing, we recommend using [Anvil](https://book.getfoundry.sh/anvil/) (part of Foundry). Anvil spins up a rapid, local EVM-compatible node that is perfect for simulating WebSocket transactions.

1.  **Install Foundry**
    ```bash
    curl -L https://foundry.paradigm.xyz | bash
    foundryup
    ```

2.  **Start Anvil Instance**
    Start Anvil running on port `8545` with instantaneous mining:
    ```bash
    anvil --host 127.0.0.1 --port 8545
    ```

This local sandbox provides predefined test accounts loaded with simulated ETH, which matches the default local configuration entries in `chains.yaml`.

---

## Database Schema & Migrations (Alembic)

cTrip uses [Alembic](https://alembic.sqlalchemy.org/) inside the background layers to manage database schemas cleanly. We provide a helper wrapper called `migrate.py` to simplify schema synchronization.

### Common Migration Workflows

*   **Check Current Migration State**:
    ```bash
    python migrate.py current
    ```

*   **Upgrade Database to Latest Schema**:
    ```bash
    python migrate.py upgrade
    ```

*   **Rollback the Last Applied Schema Migration**:
    ```bash
    python migrate.py downgrade -1
    ```

*   **Generate a New Migration Script**:
    ```bash
    alembic revision --autogenerate -m "describe_changes_here"
    ```

---

## Running Automated Tests (`pytest`)

The codebase features comprehensive unit and integration tests covering multi-chain connections, cursor tracking, and state changes.

1.  **Install Development Testing Dependencies**
    Ensure testing frameworks are installed in your virtual environment:
    ```bash
    pip install pytest pytest-asyncio
    ```

2.  **Run Tests**
    Execute tests using the configured `PYTHONPATH` context:
    ```bash
    PYTHONPATH=. poetry run pytest
    ```

### Test Files Overview
*   `tests/test_chains.py`: Tests parsing of `chains.yaml` and client connectivity.
*   `tests/test_cursor.py`: Tests Redis tracking indices used during scan cycles.
*   `tests/test_matching.py`: Tests logic validating transactions matching expected amounts.
*   `tests/test_orchestrator.py`: Validates complete scanner state changes.

---

## Running Background Workers

The worker orchestrates background scans and sweep jobs. It is started by invoking:

```bash
python run_worker.py
```

### Worker Logging & Observability
At startup, the worker output logs network discovery details:
```text
INFO:app.core:Loading configuration...
INFO:app.blockchain.manager:Successfully connected to 3 blockchain networks.
INFO:app.workers.listener:Listening for real-time payments over WebSocket.
INFO:app.workers.sweeper:Scheduler initialized. Scanning sweeps every 30s.
```
To run workers in a daemonized production context, you can deploy using a standard process supervisor like `systemd` or standard Docker container orchestration.
