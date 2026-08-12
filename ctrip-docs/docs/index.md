# Getting Started

Welcome to the **cTrip Payment Gateway** documentation. cTrip is a premium, high-performance, asynchronous multi-chain cryptocurrency payment gateway designed to make crypto payment acceptance reliable, real-time, and developer-friendly.

---

## Overview

cTrip sits securely between client applications (like merchant checkouts or web stores) and multiple EVM-compatible blockchains. It abstracts the highly complex realities of real-time block scanning, confirmation monitoring, and funds routing.

### Key Capabilities

*   **Multi-Chain EVM Native**: Built-in support for Binance Smart Chain (BSC), Ethereum, and custom local development environments (Anvil).
*   **Real-Time WebSocket Detection**: Instant block-by-block and event-by-event transaction snipes via `chain-sniper`. No high-latency, expensive polling required.
*   **Async-First Engine**: Engineered from the ground up using **FastAPI**, **SQLAlchemy 2.0 (Async)**, and **ARQ** for low-latency non-blocking performance.
*   **Secure Address Management**: Built-in Hierarchical Deterministic (HD) Wallet support to generate unique, secure payment addresses per customer order.
*   **Enterprise-Grade Webhooks**: Automatically broadcasts highly reliable payment status changes (using robust HMAC-SHA256 signatures).
*   **Database Migration Integrity**: Managed by Alembic with an optimized wrapper utility.
*   **Operations & Admin Interface**: Full control over configurations, payment flows, and operations via a secure admin portal.

---

## Prerequisites

Before starting your installation, ensure your host machine is equipped with the following dependencies:

| Prerequisite | Minimum Version | Required For |
| :--- | :--- | :--- |
| **Python** | 3.10+ | Local development and server execution |
| **Docker** | 20.10+ | Containerized multi-service deployment |
| **Redis** | 6.2+ | Background worker queue, caching, and scheduling |
| **PostgreSQL** | 13+ | Production relational data persistence |

---

## Quick Start

You can deploy and run cTrip using either Docker (recommended for local testing/deployment) or a native local virtual environment.

### Option A: Using Docker (Recommended)

Docker Compose automatically spins up the PostgreSQL database, Redis instance, FastAPI server, and ARQ background workers in a secure, isolated network.

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/rakibhossain72/ctrip.git
    cd ctrip
    ```

2.  **Set Up Local Environments**
    Create a `.env` file based on the environment template:
    ```bash
    cp .env.example .env
    ```

3.  **Run Services**
    ```bash
    docker-compose up --build
    ```

    *   The API server will be available at: `http://localhost:8000`
    *   The Admin UI panel will be accessible at: `http://localhost:8000/admin`

---

### Option B: Local Development Setup

To run a development server locally without Docker:

1.  **Create and Activate Virtual Environment**
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Initialize the Database**
    Apply database migrations using our custom migration wrapper:
    ```bash
    python migrate.py upgrade
    ```

4.  **Launch the Core API Server**
    ```bash
    uvicorn server:app --reload
    ```

5.  **Launch the Background Workers**
    ```bash
    python run_worker.py
    ```

---

## High-Level Verification

Ensure your environment is running perfectly by hitting the integrated health endpoint:

```bash
curl -i http://localhost:8000/health
```

Expected HTTP Response:
```json
HTTP/1.1 200 OK
Content-Type: application/json

{"status": "ok"}
```
