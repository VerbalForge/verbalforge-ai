#!/bin/bash
#
# VerbalForge Server Production Startup Script
#
# This script starts the VerbalForge question generation server in production mode.
#

set -e  # Exit on any error

# Get the script directory (project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
    exit 1
}

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    error "Virtual environment not found. Please run 'make install' first."
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    warn ".env file not found. Make sure to configure environment variables."
fi

# Verify Python executable
PYTHON_EXEC=".venv/bin/python"
if [ ! -x "$PYTHON_EXEC" ]; then
    error "Python executable not found at $PYTHON_EXEC"
fi

# Check Python version
PYTHON_VERSION=$($PYTHON_EXEC --version 2>&1)
log "Using $PYTHON_VERSION"

# Set environment variables
export ENVIRONMENT=production
export LOG_LEVEL=${LOG_LEVEL:-INFO}
export PYTHONPATH=src

# Verify server module can be imported
log "Validating server module..."
if ! $PYTHON_EXEC -c "import server.main" 2>/dev/null; then
    error "Failed to import server module. Please check dependencies."
fi

log "Starting VerbalForge Server (Production Mode)..."
log "Press Ctrl+C to stop the server"
log "Logs will be written to logs/verbalforge.log"

# Create logs directory if it doesn't exist
mkdir -p logs

# Get absolute path to Python executable
PYTHON_EXEC_ABS="$PROJECT_ROOT/$PYTHON_EXEC"

# Start the server with proper error handling
cd src
exec "$PYTHON_EXEC_ABS" -m server.main