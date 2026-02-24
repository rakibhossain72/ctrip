#!/bin/bash
# Start ARQ worker for crypto payment processing

set -e

echo "🚀 Starting ARQ Worker..."
echo "================================"

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis is not running!"
    echo "Start Redis with: docker-compose up redis -d"
    exit 1
fi

echo "✅ Redis is running"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo "Copy .env.example to .env and configure it"
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
fi

# Check if arq is installed
if ! python -c "import arq" 2>/dev/null; then
    echo "❌ ARQ is not installed!"
    echo "Install dependencies with: pip install -r requirements.txt"
    exit 1
fi

echo "✅ ARQ is installed"
echo "================================"
echo ""

# Start the worker
python run_worker.py
