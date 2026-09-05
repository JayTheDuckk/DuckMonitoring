#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$(dirname "$SCRIPT_DIR")"

if [ "$1" = "--wipe" ]; then
    docker compose down -v
    echo "Stopped and removed volumes."
else
    docker compose down
    echo "Stopped. Data volumes were kept. Use --wipe to destroy them."
fi
