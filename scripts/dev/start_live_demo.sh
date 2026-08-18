#!/usr/bin/env bash
# Starts the Live Replay pitch demo — NOT the full app. No Postgres, no
# Redis, no Celery, no frontend build. Just this one process streaming a
# real MIT-BIH PSG recording through the actual detection/feature code
# in backend/app/services/, at adjustable speed, over a WebSocket.
#
# The chosen record downloads from PhysioNet once and is cached under
# data/datasets/mitbih-psg/raw/ — run this at least once *before* the
# pitch, on a real connection, so the room's wifi is never a dependency.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [ ! -x "$ROOT_DIR/backend/.venv/bin/python" ]; then
  echo "backend/.venv not found — set it up first (see README 'Getting started'):"
  echo "  cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

echo "Starting Live Replay demo on http://localhost:8090 ..."
exec "$ROOT_DIR/backend/.venv/bin/python" "$ROOT_DIR/scripts/dev/live_replay_demo.py"
