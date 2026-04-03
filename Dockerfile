# Backend API — build from repo root so `data/` is available at ../data relative to backend/.
# Skips Railpack (avoids monorepo "build plan" errors); Railway auto-detects this Dockerfile.
FROM python:3.12-slim-bookworm

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY data/ ./data/

WORKDIR /app/backend

EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
