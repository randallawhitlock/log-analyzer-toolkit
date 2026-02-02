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
python3 -m uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!

# Start Frontend
echo "js: Starting Vue Frontend..."
cd frontend
npm run dev -- --port 5173 &
FRONTEND_PID=$!

# Wait for both processes
wait
