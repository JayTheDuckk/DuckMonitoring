#!/bin/bash

# Blessed install path: docker compose up
# Usage: ./scripts/docker-up.sh [--rebuild] [--reset]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

REBUILD=false
RESET=false
for arg in "$@"; do
    case "$arg" in
        --rebuild) REBUILD=true ;;
        --reset) RESET=true ;;
        -h|--help)
            echo "Usage: $0 [--rebuild] [--reset]"
            echo "  --rebuild  Force image rebuild"
            echo "  --reset    Wipe Postgres/Redis volumes (destroys data)"
            exit 0
            ;;
    esac
done

if ! command -v docker >/dev/null 2>&1; then
    echo -e "${RED}Docker is required. Install Docker Desktop or the Docker Engine.${NC}"
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    echo -e "${RED}Docker Compose V2 is required (docker compose).${NC}"
    exit 1
fi

if [ ! -f .env ]; then
    echo -e "${YELLOW}No .env found — creating one from .env.example${NC}"
    cp .env.example .env
    GENERATED="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))' 2>/dev/null || openssl rand -base64 48 | tr -d '\n')"
    if [ -n "$GENERATED" ]; then
        if [[ "$(uname)" == "Darwin" ]]; then
            sed -i '' "s|^SECRET_KEY=.*|SECRET_KEY=${GENERATED}|" .env
        else
            sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${GENERATED}|" .env
        fi
        echo -e "${GREEN}✓ Generated SECRET_KEY in .env${NC}"
    fi
fi

if $RESET; then
    echo -e "${YELLOW}Removing containers and volumes...${NC}"
    docker compose down -v
fi

UP_ARGS=(up -d)
if $REBUILD || $RESET; then
    UP_ARGS+=(--build)
fi

echo -e "${BOLD}Starting Duck Monitoring...${NC}"
docker compose "${UP_ARGS[@]}"

HTTP_PORT="$(grep -E '^HTTP_PORT=' .env 2>/dev/null | cut -d= -f2- || true)"
HTTP_PORT="${HTTP_PORT:-3000}"

echo ""
echo -e "${GREEN}${BOLD}✓ Duck Monitoring is up${NC}"
echo -e "  UI:     http://localhost:${HTTP_PORT}"
echo -e "  Health: http://localhost:${HTTP_PORT}/api/health/"
echo ""
echo -e "  Logs:   docker compose logs -f"
echo -e "  Stop:   ./scripts/docker-down.sh"
echo ""
echo -e "Open ${BOLD}http://localhost:${HTTP_PORT}${NC} to create your admin user."
echo -e "${YELLOW}LAN discovery from Docker is limited on macOS. Use ./scripts/start.sh on the host if you need mDNS/ARP.${NC}"
