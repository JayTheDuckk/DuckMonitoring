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

# Stop Celery worker
if [ -f /tmp/duck-monitoring-celery.pid ]; then
    CELERY_PID=$(cat /tmp/duck-monitoring-celery.pid)
    if ps -p $CELERY_PID > /dev/null 2>&1; then
        kill $CELERY_PID 2>/dev/null || true
        echo -e "${GREEN}Celery worker stopped (PID: $CELERY_PID)${NC}"
    else
        echo -e "${YELLOW}Celery worker process not found${NC}"
    fi
    rm -f /tmp/duck-monitoring-celery.pid
else
    if pgrep -f "celery -A config worker" > /dev/null; then
        pkill -f "celery -A config worker"
        echo -e "${GREEN}Celery worker stopped${NC}"
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
    if pgrep -f "vite" > /dev/null; then
        pkill -f "vite"
        echo -e "${GREEN}Frontend stopped${NC}"
    else
        echo -e "${YELLOW}Frontend was not running${NC}"
    fi
fi

# Stop Redis only if this script started it (not Homebrew/system-managed)
REDIS_SELF_STARTED="/tmp/duck-monitoring-redis.self-started"
if [ -f "$REDIS_SELF_STARTED" ]; then
    if command -v redis-cli >/dev/null 2>&1; then
        redis-cli shutdown nosave >/dev/null 2>&1 || true
        echo -e "${GREEN}Redis stopped (started by Duck Monitoring)${NC}"
    fi
    rm -f "$REDIS_SELF_STARTED"
fi

echo -e "${GREEN}✓ Duck Monitoring stopped${NC}"


