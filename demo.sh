#!/bin/bash
echo "Starting Polisim..."

# Backend
cd backend
pip install -r requirements.txt --quiet
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# Frontend
cd frontend
npm install --silent
npm run dev &
FRONTEND_PID=$!
cd ..

echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "Press Ctrl+C to stop"

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
