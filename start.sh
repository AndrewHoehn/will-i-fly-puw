#!/bin/bash

# Kill existing processes on ports 8000 and 5173
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null

# Start Backend
echo "Starting Backend..."
# Start Backend
echo "Starting Backend..."
# Run from root so 'backend' is treated as a package
uvicorn backend.api:app --reload --port 8000 &
BACKEND_PID=$!

# Start Frontend
echo "Starting Frontend..."
cd frontend
npm run dev -- --port 5173 &
FRONTEND_PID=$!
cd ..

echo "App running at http://localhost:5173"
echo "API running at http://localhost:8000"

# Wait for both
wait $BACKEND_PID $FRONTEND_PID
