#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$(dirname "$SCRIPT_DIR")"

LAN_PID_FILE="$(dirname "$SCRIPT_DIR")/data/lan/collector.pid"
if [ -f "$LAN_PID_FILE" ]; then
    LAN_PID="$(cat "$LAN_PID_FILE" 2>/dev/null || true)"
    if [ -n "$LAN_PID" ] && kill -0 "$LAN_PID" 2>/dev/null; then
        kill "$LAN_PID" 2>/dev/null || true
    fi
    rm -f "$LAN_PID_FILE"
fi

if [ "$1" = "--wipe" ]; then
    docker compose down -v
    echo "Stopped and removed volumes."
else
    docker compose down
    echo "Stopped. Data volumes were kept. Use --wipe to destroy them."
fi
