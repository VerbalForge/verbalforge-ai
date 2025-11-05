#!/bin/bash

# VerbalForge Server Startup Script
# Starts the question generation runners

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=================================================="
echo "VerbalForge Question Generation Server"
echo "=================================================="
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Creating..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check if config file exists
if [ ! -f "runner_config.yaml" ]; then
    echo "⚠️  runner_config.yaml not found. Using default configuration."
    echo "💡 Create runner_config.yaml to customize runner behavior."
fi

# Create logs directory if it doesn't exist
mkdir -p logs

echo ""
echo "🚀 Starting Server..."
echo ""

# Run the server
python -m src.server.main "$@"
