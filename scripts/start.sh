#!/bin/bash

# Duck Monitoring - Start Script
# Starts both backend and frontend servers

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend_django"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Duck Monitoring...${NC}"

# Check if backend is already running
if pgrep -f "manage.py runserver" > /dev/null; then
    echo -e "${YELLOW}Backend server is already running${NC}"
else
    echo -e "${GREEN}Starting backend server (Django)...${NC}"
    cd "$PROJECT_ROOT/backend_django"
    
    # Check if virtual environment exists (assuming it's in the root or backend folder - let's assume it's where the user had it, or we use the system python if configured, but better to check for venv in backend_django or root)
    # The previous script looked for venv in `backend/venv`. The new structure might have it elsewhere.
    
    VENV_PATH="$PROJECT_ROOT/backend_django/venv"
    
    if [ ! -d "$VENV_PATH" ]; then
        echo -e "${RED}Error: Virtual environment not found at $VENV_PATH. Please run setup first.${NC}"
        exit 1
    fi
    
    # Activate virtual environment and start backend
    source "$VENV_PATH/bin/activate"
    
    # Install dependencies if needed (optional, but good for first run)
    # pip install -r requirements.txt > /dev/null
    
    # Start Django
    nohup python3 manage.py runserver 0.0.0.0:8000 > /tmp/duck-monitoring-backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > /tmp/duck-monitoring-backend.pid
    echo -e "${GREEN}Backend started (PID: $BACKEND_PID)${NC}"
    echo -e "${YELLOW}Backend logs: /tmp/duck-monitoring-backend.log${NC}"
    
    # Wait a moment for backend to start
    sleep 2
fi

# Check if frontend is already running
if pgrep -f "react-scripts start" > /dev/null; then
    echo -e "${YELLOW}Frontend server is already running${NC}"
else
    echo -e "${GREEN}Starting frontend server...${NC}"
    cd "$FRONTEND_DIR"
    
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}Installing frontend dependencies...${NC}"
        npm install
    fi
    
    # Start frontend
    HOST=0.0.0.0 BROWSER=none nohup npm start > /tmp/duck-monitoring-frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > /tmp/duck-monitoring-frontend.pid
    echo -e "${GREEN}Frontend started (PID: $FRONTEND_PID)${NC}"
    echo -e "${YELLOW}Frontend logs: /tmp/duck-monitoring-frontend.log${NC}"
fi

echo -e "${GREEN}✓ Duck Monitoring is starting up!${NC}"
echo -e "${GREEN}Backend: http://localhost:8000${NC}"
echo -e "${GREEN}Frontend: http://localhost:3000${NC}"
echo -e "${YELLOW}Use './stop.sh' to stop the servers${NC}"


