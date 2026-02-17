#!/bin/bash

# Entrypoint script for agent container
# This allows environment variables to be passed to the agent

exec python -u /app/agent.py \
    --server "${SERVER_URL:-http://host.docker.internal:5001}" \
    --hostname "${HOSTNAME:-docker-host}" \
    --agent-id "${AGENT_ID:-docker-agent-$(hostname)}" \
    --interval "${INTERVAL:-30}"


