#!/bin/bash

# Duck Monitoring - Stop Script
# Stops both backend and frontend servers

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping Duck Monitoring...${NC}"

# Stop backend
if [ -f /tmp/duck-monitoring-backend.pid ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    BACKEND_PID=$(cat /tmp/duck-monitoring-backend.pid)
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        kill $BACKEND_PID 2>/dev/null || true
        echo -e "${GREEN}Backend stopped (PID: $BACKEND_PID)${NC}"
    else
        echo -e "${YELLOW}Backend process not found${NC}"
    fi
    rm -f /tmp/duck-monitoring-backend.pid
else
    # Try to kill by process name if PID file doesn't exist
    if pgrep -f "manage.py runserver" > /dev/null; then
        pkill -f "manage.py runserver"
        echo -e "${GREEN}Backend stopped${NC}"
    else
        echo -e "${YELLOW}Backend was not running${NC}"
    fi
fi

# Stop frontend
if [ -f /tmp/duck-monitoring-frontend.pid ]; then
    FRONTEND_PID=$(cat /tmp/duck-monitoring-frontend.pid)
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        kill $FRONTEND_PID 2>/dev/null || true
        echo -e "${GREEN}Frontend stopped (PID: $FRONTEND_PID)${NC}"
    else
        echo -e "${YELLOW}Frontend process not found${NC}"
    fi
    rm -f /tmp/duck-monitoring-frontend.pid
else
    # Try to kill by process name if PID file doesn't exist
    if pgrep -f "react-scripts start" > /dev/null; then
        pkill -f "react-scripts start"
        echo -e "${GREEN}Frontend stopped${NC}"
    else
        echo -e "${YELLOW}Frontend was not running${NC}"
    fi
fi

# Also kill any node processes that might be related (more aggressive cleanup)
if pgrep -f "node.*react-scripts" > /dev/null; then
    pkill -f "node.*react-scripts" 2>/dev/null || true
fi

echo -e "${GREEN}✓ Duck Monitoring stopped${NC}"


