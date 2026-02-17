#!/bin/bash

# Duck Monitoring - Status Script
# Checks if backend and frontend servers are running

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Duck Monitoring Status${NC}"
echo "======================"
echo ""

# Check backend
if pgrep -f "manage.py runserver" > /dev/null; then
    BACKEND_PID=$(pgrep -f "manage.py runserver" | head -n 1)
    echo -e "${GREEN}✓ Backend: Running (PID: $BACKEND_PID)${NC}"
    echo "  URL: http://localhost:8000"
    if [ -f /tmp/duck-monitoring-backend.log ]; then
        echo "  Logs: /tmp/duck-monitoring-backend.log"
    fi
else
    echo -e "${RED}✗ Backend: Not running${NC}"
fi

echo ""

# Check frontend
if pgrep -f "react-scripts start" > /dev/null; then
    FRONTEND_PID=$(pgrep -f "react-scripts start" | head -n 1)
    echo -e "${GREEN}✓ Frontend: Running (PID: $FRONTEND_PID)${NC}"
    echo "  URL: http://localhost:3000"
    if [ -f /tmp/duck-monitoring-frontend.log ]; then
        echo "  Logs: /tmp/duck-monitoring-frontend.log"
    fi
else
    echo -e "${RED}✗ Frontend: Not running${NC}"
fi

echo ""
echo "Use './start.sh' to start servers"
echo "Use './stop.sh' to stop servers"


