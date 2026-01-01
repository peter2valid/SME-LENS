#!/bin/bash

# Start Backend
echo "Starting Backend..."
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# Start Frontend
echo "Starting Frontend..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo "SMELens is running!"
echo "Backend: http://localhost:8000/docs"
echo "Frontend: http://localhost:5173"

trap "kill $BACKEND_PID $FRONTEND_PID; exit" SIGINT SIGTERM

wait
