#!/bin/bash

# Kill existing processes
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null

echo "Starting KPUW Tracker in Production Mode..."

# Navigate to backend
cd backend

# Start Uvicorn (FastAPI)
# --host 0.0.0.0 allows external access
# --port 8000
# Background process
nohup uvicorn api:app --host 0.0.0.0 --port 8000 > ../app.log 2>&1 &
PID=$!

echo "App started with PID $PID"
echo "Logs available in app.log"
echo "Access at http://localhost:8000"
