#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$ROOT_DIR/logs" "$ROOT_DIR/run" "$ROOT_DIR/recordings"

PIDFILE="$ROOT_DIR/run/main.pid"
LOGFILE="$ROOT_DIR/logs/main.log"

PYTHON_BIN="$ROOT_DIR/venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi

if [[ -f "$PIDFILE" ]]; then
  PID="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [[ -n "${PID:-}" ]] && kill -0 "$PID" 2>/dev/null; then
    echo "WatchTok already running (PID $PID)"
    echo "Log: $LOGFILE"
    exit 0
  fi
fi

nohup "$PYTHON_BIN" "$ROOT_DIR/main.py" >> "$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"

echo "WatchTok started (PID $(cat "$PIDFILE"))"
echo "Python: $PYTHON_BIN"
echo "Log: $LOGFILE"
