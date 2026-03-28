#!/bin/bash
set -e
echo "🐟 Starting Polisim..."

# Check for .env
if [ ! -f .env ]; then
  echo "⚠️  No .env found. Copying .env.example..."
  cp .env.example .env
  echo "✏️  Edit .env and add your OPENAI_API_KEY and TINYFISH_API_KEY"
fi

# Backend
echo "🔧 Starting backend..."
cd backend
pip install -r requirements.txt --quiet
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# Frontend
echo "🎨 Starting frontend..."
cd frontend
npm install --silent
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Backend:  http://localhost:8000"
echo "✅ Frontend: http://localhost:3000"
echo "✅ API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"

cleanup() {
  echo "\n🛑 Stopping servers..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
  exit 0
}

trap cleanup INT TERM
wait
