#!/bin/bash

# Duck Monitoring - Start Frontend Only

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Duck Monitoring Frontend...${NC}"

# Check if frontend is already running
if pgrep -f "react-scripts start" > /dev/null; then
    echo -e "${YELLOW}Frontend server is already running${NC}"
    exit 0
fi

cd "$FRONTEND_DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    npm install
fi

# Start frontend
npm start > /tmp/duck-monitoring-frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > /tmp/duck-monitoring-frontend.pid
echo -e "${GREEN}Frontend started (PID: $FRONTEND_PID)${NC}"
echo -e "${YELLOW}Frontend logs: /tmp/duck-monitoring-frontend.log${NC}"
echo -e "${GREEN}Frontend: http://localhost:3000${NC}"


