#!/usr/bin/env sh
set -eu

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-10000}"
WORKERS="${WEB_CONCURRENCY:-1}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

echo "Starting MediProfit API on ${HOST}:${PORT} with ${WORKERS} worker(s)"
exec "${PYTHON_BIN}" -m uvicorn app.main:app --host "${HOST}" --port "${PORT}" --workers "${WORKERS}"
