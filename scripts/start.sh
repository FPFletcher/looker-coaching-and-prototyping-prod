#!/bin/bash
# Startup script for Looker MCP Chat Interface
# This script starts both the backend and frontend servers

cd "$(dirname "$0")/.."

echo "🚀 Starting Looker MCP Chat Interface..."

# Kill any existing instances
echo "Stopping existing servers..."
pkill -f "uvicorn main:app" 2>/dev/null
pkill -f "next dev" 2>/dev/null
sleep 2

# Start backend
echo "Starting backend on port 8000..."
cd apps/agent
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 > ../../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ../..

# Wait for backend to start
sleep 3

# Start frontend
echo "Starting frontend on port 3000..."
cd apps/web
npm run dev > ../../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ../..

# Wait for frontend to compile
echo "Waiting for servers to start..."
sleep 8

# Open browser
if command -v xdg-open > /dev/null; then
    xdg-open http://localhost:3000 2>/dev/null &
elif command -v open > /dev/null; then
    open http://localhost:3000 2>/dev/null &
fi

echo "✅ Servers started!"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo ""
echo "   Backend PID:  $BACKEND_PID"
echo "   Frontend PID: $FRONTEND_PID"
echo ""
echo "To stop: pkill -f 'uvicorn main:app' && pkill -f 'next dev'"
echo "Logs: tail -f logs/backend.log logs/frontend.log"
