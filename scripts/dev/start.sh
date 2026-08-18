#!/usr/bin/env bash
# Starts everything needed to use NeuroSleep Twin locally: the FastAPI
# backend, the Celery ingestion worker, and the Vite frontend.
#
# Prerequisites (one-time, see README "Getting started"):
#   - Postgres running locally with the `neurosleep` role/database created
#   - Redis running locally (`brew services start redis` on macOS)
#   - backend/.venv with `pip install -r backend/requirements.txt`, migrated
#     with `alembic upgrade head`
#   - frontend/node_modules (`npm install` in frontend/)
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PIDS=()

cleanup() {
  echo "Stopping..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

echo "Starting backend (http://localhost:8000)..."
(cd "$ROOT_DIR/backend" && .venv/bin/uvicorn app.main:app --port 8000) &
PIDS+=($!)

echo "Starting Celery worker..."
(cd "$ROOT_DIR/backend" && .venv/bin/celery -A app.worker.celery_app worker --loglevel=info) &
PIDS+=($!)

echo "Starting frontend (http://localhost:5173)..."
(cd "$ROOT_DIR/frontend" && npm run dev) &
PIDS+=($!)

wait
