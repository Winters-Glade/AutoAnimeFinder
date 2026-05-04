#!/bin/bash
# Start both backend and frontend for AutoAnimeFinder

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$SKILL_DIR/assets/backend"
FRONTEND_DIR="$SKILL_DIR/assets/frontend"

echo "🌟 Starting AutoAnimeFinder..."
echo ""

# Start backend
echo "🚀 Starting backend (FastAPI on :8000)..."
cd "$BACKEND_DIR"
. venv/bin/activate 2>/dev/null
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Start frontend
echo "🚀 Starting frontend (Vite on :5173)..."
cd "$FRONTEND_DIR"
npx vite --port 5173 &
FRONTEND_PID=$!

echo ""
echo "✅ AutoAnimeFinder is running!"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:8000"
echo "   API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM
wait