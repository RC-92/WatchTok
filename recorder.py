#!/usr/bin/env python3
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNNING = True


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(msg: str) -> None:
    print(f"[{utc_now_iso()}] {msg}", flush=True)


def normalize_username(u: str) -> str:
    u = u.strip()
    return u[1:] if u.startswith("@") else u


def check_alive(room_id: str, timeout: int = 10) -> bool:
    url = f"https://webcast.tiktok.com/webcast/room/check_alive/?aid=1988&room_ids={room_id}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120 Safari/537.36"
            ),
            "Accept": "application/json,text/plain,*/*",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
        data = json.loads(raw)
        items = data.get("data", [])
        if not items:
            return False
        return bool(items[0].get("alive"))
    except Exception:
        return True


def which_ytdlp() -> str:
    p = shutil.which("yt-dlp")
    if p:
        return p
    # Check venv
    venv_path = ROOT / "venv" / "bin" / "yt-dlp"
    if venv_path.exists():
        return str(venv_path)
    raise RuntimeError("yt-dlp not found. Install: pip install yt-dlp")


def handle_signal(signum, frame):
    global RUNNING
    RUNNING = False


def main():
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    if len(sys.argv) != 4:
        print("Usage: recorder.py <username> <output_path> <room_id>", file=sys.stderr)
        sys.exit(2)

    username = normalize_username(sys.argv[1])
    output_path = sys.argv[2]
    room_id = sys.argv[3]
    alive_poll = int(os.environ.get("WATCHTOK_ALIVE_POLL", "5"))

    live_url = f"https://www.tiktok.com/@{username}/live"
    ytdlp = which_ytdlp()

    log(f"Recorder starting for {username}")
    log(f"room_id={room_id}")
    log(f"url={live_url}")
    log(f"output={output_path}")

    ytdlp_cmd = [
        ytdlp,
        "--no-part",
        "--no-warnings",
        "-o", output_path,
        "--fixup", "never",
        # Prefer best combined format
        "-f", "best",
        # Add cookies if needed for geo-restricted content
        # "--cookies", str(ROOT / "cookies.txt"),
        live_url,
    ]

    log(f"Starting yt-dlp: {' '.join(ytdlp_cmd)}")

    ytdlp_log = ROOT / "logs" / "ytdlp.log"
    ytdlp_log.parent.mkdir(parents=True, exist_ok=True)
    logf = open(ytdlp_log, "a")

    proc = subprocess.Popen(ytdlp_cmd, stdout=logf, stderr=logf)

    log("yt-dlp running. Monitoring check_alive...")

    while RUNNING:
        if not check_alive(room_id):
            log("LIVE ended (check_alive=false). Stopping.")
            break

        if proc.poll() is not None:
            log(f"yt-dlp exited (code={proc.returncode}). See logs/ytdlp.log")
            break

        time.sleep(alive_poll)

    # Cleanup
    if proc.poll() is None:
        log(f"Terminating yt-dlp (pid={proc.pid})...")
        proc.terminate()
        time.sleep(2)
        if proc.poll() is None:
            proc.kill()

    rc = proc.returncode if proc.returncode is not None else 0
    log(f"Recorder finished (exit_code={rc}).")
    sys.exit(0)


if __name__ == "__main__":
    main()
