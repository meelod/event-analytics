#!/bin/bash
# Start both backend and frontend dev servers

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Starting Event Analytics Platform..."
echo "===================================="

# Kill existing processes on our ports
lsof -ti :8000 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti :5173 2>/dev/null | xargs kill -9 2>/dev/null || true

# Start backend
echo "Starting backend on http://localhost:8000..."
cd "$PROJECT_ROOT/backend"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend on http://localhost:5173..."
cd "$PROJECT_ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "Backend:  http://localhost:8000 (API docs: http://localhost:8000/docs)"
echo "Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both servers."

# Trap Ctrl+C to kill both
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

# Wait for either to exit
wait
