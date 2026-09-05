#!/bin/bash

# Duck Monitoring - Factory Reset Wrapper
# Delegates to the unified start script with --reset

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/start.sh" --reset "$@"
