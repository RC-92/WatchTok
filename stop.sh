#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PIDFILE="$ROOT_DIR/run/main.pid"

if [[ ! -f "$PIDFILE" ]]; then
  echo "WatchTok is not running (no PID file)."
  exit 0
fi

PID="$(cat "$PIDFILE" 2>/dev/null || true)"

if [[ -z "${PID:-}" ]]; then
  echo "PID file exists but is empty. Removing it."
  rm -f "$PIDFILE"
  exit 0
fi

if kill -0 "$PID" 2>/dev/null; then
  echo "Stopping WatchTok (PID $PID)..."
  kill "$PID"

  # Wait up to ~8 seconds for clean exit
  for _ in {1..16}; do
    if ! kill -0 "$PID" 2>/dev/null; then
      break
    fi
    sleep 0.5
  done

  # If still alive, force kill
  if kill -0 "$PID" 2>/dev/null; then
    echo "Still running, force killing (SIGKILL)..."
    kill -9 "$PID" || true
  fi

  echo "Stopped."
else
  echo "PID $PID is not running. Cleaning up PID file."
fi

rm -f "$PIDFILE"
