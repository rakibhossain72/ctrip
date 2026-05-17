# cTrip Payment Gateway

cTrip is a high-performance, multi-chain cryptocurrency payment gateway built with FastAPI. It supports automated payment detection, confirmation monitoring, and funds sweeping across multiple EVM-compatible blockchains.

## Features

- **Multi-Chain Support**: Native support for BSC, Ethereum, and local testing environments (Anvil).
- **Real-Time Detection**: WebSocket-based payment detection via chain-sniper, with no block polling required.
- **Async Architecture**: Fully asynchronous API and database operations using SQLAlchemy and FastAPI.
- **Background Workers**: Async task processing using ARQ and Redis with built-in cron scheduling.
- **Secure Address Management**: HD Wallet integration for generating unique payment addresses.
- **Webhooks**: Automated notifications for payment status changes (HMAC-SHA256 signed).
- **Migration System**: Robust database migrations using Alembic with a custom helper script.
- **Admin API**: Manual task triggering via `/admin/*` endpoints.

## Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Database**: [PostgreSQL](https://www.postgresql.org/) / [SQLite](https://www.sqlite.org/) (Dev)
- **ORM**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
- **Task Queue**: [ARQ](https://arq-docs.helpmanual.io/) with Redis
- **Blockchain**: [Web3.py](https://web3py.readthedocs.io/) + [chain-sniper](https://pypi.org/project/chain-sniper/) (WebSocket detection)
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/)

## Prerequisites

- Python 3.10+
- Docker & Docker Compose
- Redis (for background workers)
- PostgreSQL (for production)

## Configuration

1. Create a `.env` file from the environment template.
2. Configure your chains in `chains.yaml` — use WebSocket URLs (`ws://` or `wss://`) for real-time payment detection.
3. Set your HD Wallet mnemonic in the environment variables.

## Quick Start

### Using Docker (Recommended)

```bash
docker-compose up --build
```

This will start the API, PostgreSQL, Redis, and background workers.

### Local Development

1. **Install Dependencies**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run Migrations**:
   ```bash
   python migrate.py upgrade
   ```

3. **Start the API**:
   ```bash
   uvicorn server:app --reload
   ```

4. **Start Workers**:
   ```bash
   python run_worker.py
   ```

## Project Structure

- `app/api/`: API endpoints and routes.
- `app/blockchain/`: Multi-chain implementation and Web3 logic.
- `app/db/`: Database models, schemas, and session management.
- `app/workers/`: ARQ tasks and worker configuration for background processing.
- `app/services/`: Core business logic for scanning and sweeping.
- `migrate.py`: Helper script for managing database migrations.

## Documentation

For more detailed information, see [Documentation](https://ctrip-docs.readthedocs.io/).

## License

This project is licensed under the terms included in the [LICENSE.txt](LICENSE.txt) file.
