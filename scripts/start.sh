#!/bin/bash

# Duck Monitoring - Unified Startup Script
# Sets up dependencies (first run), starts Redis if needed, then backend, Celery, and frontend.
#
# Local/dev startup (venv + Redis + Django + Celery + Vite).
# For the supported deploy path use: ./scripts/docker-up.sh
#
# Usage:
#   ./scripts/start.sh              Normal startup (idempotent)
#   ./scripts/start.sh --reset      Wipe database and run fresh setup

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend_django"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
VENV_PATH="$BACKEND_DIR/venv"
DB_PATH="$PROJECT_ROOT/db.sqlite3"

REDIS_SELF_STARTED="/tmp/duck-monitoring-redis.self-started"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

RESET=false
FIRST_RUN=false
for arg in "$@"; do
    case "$arg" in
        --reset) RESET=true ;;
        -h|--help)
            echo "Usage: $0 [--reset]"
            echo "  --reset  Wipe the database and run a fresh setup"
            exit 0
            ;;
    esac
done

redis_running() {
    command -v redis-cli >/dev/null 2>&1 && redis-cli ping >/dev/null 2>&1
}

ensure_redis() {
    if redis_running; then
        echo -e "${GREEN}✓ Redis: already running${NC}"
        return 0
    fi

    echo -e "${YELLOW}Redis not running — attempting to start...${NC}"

    if [[ "$(uname)" == "Darwin" ]] && command -v brew >/dev/null 2>&1; then
        if brew services list 2>/dev/null | grep -E '^redis ' | grep -q started; then
            echo -e "${GREEN}✓ Redis: managed by Homebrew (already started)${NC}"
            return 0
        fi
        if brew list redis >/dev/null 2>&1; then
            brew services start redis >/dev/null 2>&1 || true
        fi
    elif command -v systemctl >/dev/null 2>&1; then
        sudo systemctl start redis 2>/dev/null || \
        sudo systemctl start redis-server 2>/dev/null || true
    fi

    if ! redis_running && command -v redis-server >/dev/null 2>&1; then
        redis-server --daemonize yes >/dev/null 2>&1 || true
        touch "$REDIS_SELF_STARTED"
    fi

    for _ in $(seq 1 10); do
        if redis_running; then
            echo -e "${GREEN}✓ Redis: started${NC}"
            return 0
        fi
        sleep 0.5
    done

    echo -e "${YELLOW}⚠ Redis unavailable — Celery and service checks will not run${NC}"
    return 1
}

setup_backend() {
    echo -e "${GREEN}Setting up backend...${NC}"
    cd "$BACKEND_DIR"

    if [ ! -d "$VENV_PATH" ]; then
        echo -e "${YELLOW}Creating Python virtual environment...${NC}"
        python3 -m venv "$VENV_PATH"
    fi

    source "$VENV_PATH/bin/activate"
    pip install -q -r requirements.txt

    echo -e "${YELLOW}Applying database migrations...${NC}"
    python manage.py migrate --noinput
}

setup_frontend() {
    echo -e "${GREEN}Setting up frontend...${NC}"
    cd "$FRONTEND_DIR"

    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}Installing Node.js dependencies...${NC}"
        npm install
    fi
}

factory_reset() {
    echo -e "${RED}${BOLD}WARNING: This will delete the existing Duck Monitoring database.${NC}"
    read -p "Are you sure you want to continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Aborting reset.${NC}"
        exit 1
    fi

    "$SCRIPT_DIR/stop.sh" || true

    if [ -f "$DB_PATH" ]; then
        echo -e "${YELLOW}Removing existing database...${NC}"
        rm "$DB_PATH"
    fi
}

start_backend() {
    if pgrep -f "manage.py runserver" >/dev/null; then
        echo -e "${YELLOW}Backend: already running${NC}"
        return 0
    fi

    echo -e "${GREEN}Starting backend (Django)...${NC}"
    cd "$BACKEND_DIR"
    source "$VENV_PATH/bin/activate"

    nohup python3 manage.py runserver 0.0.0.0:8000 > /tmp/duck-monitoring-backend.log 2>&1 &
    echo $! > /tmp/duck-monitoring-backend.pid
    echo -e "${GREEN}✓ Backend started (PID: $(cat /tmp/duck-monitoring-backend.pid))${NC}"
    echo -e "${YELLOW}  Logs: /tmp/duck-monitoring-backend.log${NC}"
    sleep 2
}

start_celery() {
    if ! redis_running; then
        return 0
    fi

    if pgrep -f "celery -A config worker" >/dev/null; then
        echo -e "${YELLOW}Celery worker: already running${NC}"
        return 0
    fi

    echo -e "${GREEN}Starting Celery worker...${NC}"
    cd "$BACKEND_DIR"
    source "$VENV_PATH/bin/activate"

    nohup celery -A config worker -l info > /tmp/duck-monitoring-celery.log 2>&1 &
    echo $! > /tmp/duck-monitoring-celery.pid
    echo -e "${GREEN}✓ Celery worker started (PID: $(cat /tmp/duck-monitoring-celery.pid))${NC}"
    echo -e "${YELLOW}  Logs: /tmp/duck-monitoring-celery.log${NC}"
}

start_frontend() {
    if pgrep -f "vite" >/dev/null; then
        echo -e "${YELLOW}Frontend: already running${NC}"
        return 0
    fi

    echo -e "${GREEN}Starting frontend (React)...${NC}"
    cd "$FRONTEND_DIR"

    HOST=0.0.0.0 BROWSER=none nohup npm start > /tmp/duck-monitoring-frontend.log 2>&1 &
    echo $! > /tmp/duck-monitoring-frontend.pid
    echo -e "${GREEN}✓ Frontend started (PID: $(cat /tmp/duck-monitoring-frontend.pid))${NC}"
    echo -e "${YELLOW}  Logs: /tmp/duck-monitoring-frontend.log${NC}"
}

# --- Main ---

echo -e "${GREEN}${BOLD}Starting Duck Monitoring...${NC}"
echo ""

if [ ! -f "$DB_PATH" ]; then
    FIRST_RUN=true
fi

if $RESET; then
    factory_reset
    FIRST_RUN=true
fi

setup_backend
setup_frontend
ensure_redis || true
start_backend
start_celery
start_frontend

echo ""
echo -e "${GREEN}${BOLD}✓ Duck Monitoring is up!${NC}"
echo -e "  Backend:  http://localhost:8000"
echo -e "  Frontend: http://localhost:3000"
echo -e "  Health:   http://localhost:8000/api/health/"
echo ""
echo -e "${YELLOW}Use './scripts/stop.sh' to stop all services${NC}"

if $FIRST_RUN; then
    echo ""
    echo -e "============================================================"
    echo -e "${GREEN}${BOLD}First-time setup complete!${NC}"
    echo -e "Open ${BOLD}http://localhost:3000${NC} to register your admin user."
    echo -e "============================================================"
fi
