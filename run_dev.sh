#!/bin/bash

# Function to kill processes on exit
cleanup() {
    echo "Stopping services..."
    kill $BACKEND_PID
    kill $FRONTEND_PID
    exit
}

# Trap interrupt signals
trap cleanup SIGINT SIGTERM

echo "🚀 Starting Log Analyzer Toolkit..."

# Start Backend
echo "py: Starting FastAPI Backend on port 8000..."
if [ -d "venv" ]; then
    PYTHON_CMD="./venv/bin/python"
else
    PYTHON_CMD="python3"
fi

$PYTHON_CMD -m uvicorn backend.main:app --reload --reload-dir backend --reload-dir log_analyzer --port 8000 &
BACKEND_PID=$!

# Start Frontend
echo "js: Starting Vue Frontend..."
cd frontend
npm run dev -- --port 5173 &
FRONTEND_PID=$!

# Wait for both processes
wait
