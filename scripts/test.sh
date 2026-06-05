#!/bin/bash
echo "=== Testing PM Assistant ==="

echo "1. Health check..."
curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "Backend ne dostupen"

echo ""
echo "2. API status..."
curl -s http://localhost:8000/ | python3 -m json.tool 2>/dev/null || echo "API ne dostupen"

echo ""
echo "3. Tasks endpoint..."
curl -s http://localhost:8000/api/tasks | python3 -m json.tool 2>/dev/null || echo "Tasks API ne dostupen"

echo ""
echo "4. Stats endpoint..."
curl -s http://localhost:8000/api/stats | python3 -m json.tool 2>/dev/null || echo "Stats API ne dostupen"

echo ""
echo "5. Docker status..."
docker-compose ps

echo ""
echo "=== Test Complete ==="
