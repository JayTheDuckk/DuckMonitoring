#!/bin/bash

# Script to stop Docker test hosts

echo "🛑 Stopping Docker test hosts..."

cd "$(dirname "$0")"
docker-compose down

echo "✅ All test hosts stopped"


