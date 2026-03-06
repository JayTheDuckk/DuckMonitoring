#!/bin/bash

# Duck Monitoring - Initial Startup & Factory Reset Script
# WARNING: This script will WIPE your existing database and reset the application to factory defaults.
# It is intended for first-time installation or completely resetting the environment.

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
BOLD='\033[1m'

echo -e "${RED}${BOLD}WARNING: This script will delete the existing Duck Monitoring database.${NC}"
read -p "Are you sure you want to continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo -e "${YELLOW}Aborting initial setup.${NC}"
    exit 1
fi

echo -e "${GREEN}Starting Duck Monitoring Initial Setup...${NC}"

# 1. Stop any currently running servers
echo -e "${YELLOW}Stopping any running servers...${NC}"
"$SCRIPT_DIR/stop.sh" || true  # Ignore errors if they aren't running

# 2. Reset the database
DB_PATH="$BACKEND_DIR/db.sqlite3"
if [ -f "$DB_PATH" ]; then
    echo -e "${YELLOW}Removing existing database at $DB_PATH...${NC}"
    rm "$DB_PATH"
fi

# 3. Setup Backend Environment
echo -e "${GREEN}Setting up the Django Backend...${NC}"
cd "$BACKEND_DIR"

VENV_PATH="$BACKEND_DIR/venv"
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv "$VENV_PATH"
fi

echo -e "${YELLOW}Activating virtual environment & installing dependencies...${NC}"
source "$VENV_PATH/bin/activate"
pip install -r requirements.txt

echo -e "${YELLOW}Applying fresh database migrations...${NC}"
python manage.py migrate

# 4. Setup Frontend Environment
echo -e "${GREEN}Setting up the React Frontend...${NC}"
cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing Node.js dependencies...${NC}"
    npm install
fi

# 5. Start the Application
echo -e "${GREEN}Starting the application...${NC}"
cd "$PROJECT_ROOT"
"$SCRIPT_DIR/start.sh"

echo -e "============================================================"
echo -e "${GREEN}${BOLD}Setup Complete!${NC}"
echo -e "To finish installing Duck Monitoring, please open your browser to:"
echo -e "                 ${BOLD}http://localhost:3000${NC}"
echo -e "You will be prompted to register your first Admin user."
echo -e "============================================================"
