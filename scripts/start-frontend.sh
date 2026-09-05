#!/bin/bash

# Duck Monitoring - Start Frontend Only

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if pgrep -f "vite" >/dev/null; then
    echo -e "${YELLOW}Frontend server is already running${NC}"
    exit 0
fi

cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    npm install
fi

HOST=0.0.0.0 BROWSER=none nohup npm start > /tmp/duck-monitoring-frontend.log 2>&1 &
echo $! > /tmp/duck-monitoring-frontend.pid
echo -e "${GREEN}Frontend started (PID: $(cat /tmp/duck-monitoring-frontend.pid))${NC}"
echo -e "${GREEN}Frontend: http://localhost:3000${NC}"
