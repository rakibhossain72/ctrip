# cTrip Payment Gateway

cTrip is a high-performance, multi-chain cryptocurrency payment gateway built with FastAPI. It supports automated payment detection, confirmation monitoring, and funds sweeping across multiple EVM-compatible blockchains.

## Features

- **Multi-Chain Support**: Native support for BSC, Ethereum, and local testing environments (Anvil).
- **Automated Detection**: Real-time scanning of blockchain blocks to detect incoming payments.
- **Async Architecture**: Fully asynchronous API and database operations using SQLAlchemy and FastAPI.
- **Background Workers**: Distributed task processing using Dramatiq and Redis for reliable background operations.
- **Secure Address Management**: HD Wallet integration for generating unique payment addresses.
- **Webhooks**: Automated notifications for payment status changes.
- **Migration System**: Robust database migrations using Alembic with a custom helper script.

## Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Database**: [PostgreSQL](https://www.postgresql.org/) / [SQLite](https://www.sqlite.org/) (Dev)
- **ORM**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
- **Task Queue**: [Dramatiq](https://dramatiq.io/) with Redis
- **Blockchain**: [Web3.py](https://web3py.readthedocs.io/)
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/)

## Prerequisites

- Python 3.10+
- Docker & Docker Compose
- Redis (for background workers)
- PostgreSQL (for production)

## Configuration

1. Create a `.env` file from the environment template.
2. Configure your chains in `chains.yaml`.
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
   dramatiq app.workers.listener app.workers.sweeper app.workers.webhook
   ```

## Project Structure

- `app/api/`: API endpoints and routes.
- `app/blockchain/`: Multi-chain implementation and Web3 logic.
- `app/db/`: Database models, schemas, and session management.
- `app/workers/`: Dramatiq actors for background tasks.
- `app/services/`: Core business logic for scanning and sweeping.
- `migrate.py`: Helper script for managing database migrations.

## Documentation

For detailed information on database migrations, see [MIGRATIONS.md](MIGRATIONS.md).

## License

This project is licensed under the terms included in the [LICENSE.txt](LICENSE.txt) file.
