#!/bin/bash

# Duck Monitoring - Start Backend Only

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend_django"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Duck Monitoring Backend...${NC}"

# Check if backend is already running
if pgrep -f "manage.py runserver" > /dev/null; then
    echo -e "${YELLOW}Backend server is already running${NC}"
    exit 0
fi

cd "$PROJECT_ROOT/backend_django"

# Check for venv in backend_django
if [ -d "$PROJECT_ROOT/backend_django/venv" ]; then
    VENV_PATH="$PROJECT_ROOT/backend_django/venv"
else
    echo -e "${RED}Error: Virtual environment not found. Please run setup first.${NC}"
    exit 1
fi

# Activate virtual environment and start backend
source "$VENV_PATH/bin/activate"
python3 manage.py runserver 0.0.0.0:8000 > /tmp/duck-monitoring-backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > /tmp/duck-monitoring-backend.pid
echo -e "${GREEN}Backend started (PID: $BACKEND_PID)${NC}"
echo -e "${YELLOW}Backend logs: /tmp/duck-monitoring-backend.log${NC}"
echo -e "${GREEN}Backend: http://localhost:8000${NC}"


