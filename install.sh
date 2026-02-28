#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== WatchTok Installer ==="

# --- Check Python3 ---
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install Python 3.8+ first."
    exit 1
fi

echo "Python: $(python3 --version)"

# --- Python venv ---
echo "[1/3] Setting up Python virtual environment..."
if [[ ! -d "$ROOT_DIR/venv" ]]; then
    python3 -m venv "$ROOT_DIR/venv"
fi
source "$ROOT_DIR/venv/bin/activate"

echo "[2/3] Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r "$ROOT_DIR/requirements.txt" -q

# --- Directory structure ---
echo "[3/3] Creating directories..."
mkdir -p "$ROOT_DIR/logs" "$ROOT_DIR/run" "$ROOT_DIR/recordings"

# --- Config check ---
if [[ ! -f "$ROOT_DIR/config.json" ]]; then
    cat > "$ROOT_DIR/config.json" << 'EOF'
{
    "users": [],
    "poll_interval_seconds": 12,
    "rapid_watch_seconds": 600,
    "rapid_poll_interval_seconds": 5,
    "recordings_dir": "./recordings",
    "notifier": {
        "type": "ntfy",
        "ntfy_url": "https://ntfy.sh/your-topic-here"
    }
}
EOF
    echo ""
    echo "NOTE: Created default config.json"
    echo "  -> Add TikTok usernames to the 'users' array"
    echo "  -> Set your ntfy topic URL in notifier.ntfy_url"
fi

echo ""
echo "=== Installation complete ==="
echo "Venv:   $ROOT_DIR/venv"
echo "yt-dlp: $ROOT_DIR/venv/bin/yt-dlp"
echo ""
echo "Usage:"
echo "  1. Edit config.json and add usernames"
echo "  2. ./start.sh        # start monitoring"
echo "  3. ./stop.sh         # stop monitoring"
echo "  4. tail -f logs/main.log  # watch logs"
