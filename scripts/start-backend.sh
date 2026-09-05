#!/bin/bash

# Duck Monitoring - Start Backend Only
# Delegates to the unified start script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend_django"
VENV_PATH="$BACKEND_DIR/venv"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Source helper functions from start.sh by running setup + backend only
source_helpers() {
    redis_running() {
        command -v redis-cli >/dev/null 2>&1 && redis-cli ping >/dev/null 2>&1
    }
}

source_helpers

if pgrep -f "manage.py runserver" >/dev/null; then
    echo -e "${YELLOW}Backend server is already running${NC}"
    exit 0
fi

if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}Error: Virtual environment not found. Run ./scripts/start.sh first.${NC}"
    exit 1
fi

cd "$BACKEND_DIR"
source "$VENV_PATH/bin/activate"
nohup python3 manage.py runserver 0.0.0.0:8000 > /tmp/duck-monitoring-backend.log 2>&1 &
echo $! > /tmp/duck-monitoring-backend.pid
echo -e "${GREEN}Backend started (PID: $(cat /tmp/duck-monitoring-backend.pid))${NC}"
echo -e "${GREEN}Backend: http://localhost:8000${NC}"
