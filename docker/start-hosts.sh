#!/bin/bash

# Script to start Docker test hosts for Duck Monitoring

echo "🐳 Starting Docker test hosts for Duck Monitoring..."
echo ""

# Check if backend is running
echo "Checking if backend is running..."
if curl -s http://localhost:5001/api/health > /dev/null 2>&1; then
    echo "✅ Backend is running on port 5001"
else
    echo "❌ Backend is not running on port 5001"
    echo "   Please start the backend first: cd backend && python app.py"
    exit 1
fi

echo ""
echo "Starting Docker containers..."
cd "$(dirname "$0")"
docker-compose up -d

echo ""
echo "Waiting for containers to start..."
sleep 3

echo ""
echo "📊 Container Status:"
docker-compose ps

echo ""
echo "✅ Test hosts started!"
echo ""
echo "View logs: docker-compose logs -f"
echo "Stop hosts: docker-compose down"
echo ""
echo "Check your dashboard at http://localhost:3000"

