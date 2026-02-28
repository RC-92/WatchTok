#!/usr/bin/env python3
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from poller import is_user_live

ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / "state.json"
LOGS_DIR = ROOT / "logs"

RUNNING = True


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(msg: str) -> None:
    print(f"[{utc_now_iso()}] {msg}", flush=True)


def load_config() -> dict:
    with open(ROOT / "config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_state() -> dict:
    if not STATE_FILE.exists() or STATE_FILE.stat().st_size == 0:
        return {"users": {}}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict) -> None:
    tmp = str(STATE_FILE) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, STATE_FILE)


def spawn_notifier(username: str, text: str) -> None:
    logfile = LOGS_DIR / "notifier.log"
    with open(logfile, "a") as out:
        subprocess.Popen(
            [sys.executable, str(ROOT / "notifier.py"), username, text],
            stdout=out,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )


def spawn_recorder(username: str, output_path: str, room_id: str) -> subprocess.Popen:
    logfile = LOGS_DIR / "recorder.log"
    out = open(logfile, "a")
    return subprocess.Popen(
        [sys.executable, str(ROOT / "recorder.py"), username, output_path, room_id],
        stdout=out,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )


def handle_signal(signum, frame):
    global RUNNING
    RUNNING = False


def main():
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    users = cfg.get("users", [])
    if not users:
        log("No users configured in config.json. Exiting.")
        return

    poll_interval = int(cfg.get("poll_interval_seconds", 15))
    rapid_watch_seconds = int(cfg.get("rapid_watch_seconds", 600))
    rapid_poll_interval = int(cfg.get("rapid_poll_interval_seconds", 5))

    recordings_dir = Path(cfg.get("recordings_dir", str(ROOT / "recordings"))).resolve()
    recordings_dir.mkdir(parents=True, exist_ok=True)

    state = load_state()
    state.setdefault("users", {})

    # Track recorder processes
    recorders: dict[str, subprocess.Popen] = {}

    log(f"Starting WatchTok for users: {', '.join(users)}")
    log(f"Normal poll={poll_interval}s | Rapid poll={rapid_poll_interval}s for {rapid_watch_seconds}s")

    while RUNNING:
        state_changed = False
        now_epoch = time.time()

        for username in users:
            ustate = state["users"].setdefault(username, {})
            prev_live = bool(ustate.get("is_live", False))

            rapid_until = float(ustate.get("rapid_until_epoch", 0.0))
            in_rapid = now_epoch < rapid_until
            interval = rapid_poll_interval if in_rapid else poll_interval

            next_check = float(ustate.get("next_check_epoch", 0.0))
            if now_epoch < next_check:
                continue

            info = is_user_live(username)
            now_live = bool(info.get("is_live"))
            session_id = info.get("session_id")  # room_id when live

            ustate["last_checked_at"] = utc_now_iso()
            ustate["next_check_epoch"] = now_epoch + interval

            if not prev_live and now_live:
                # LIVE STARTED
                if not session_id:
                    session_id = "unknown"

                ustate["is_live"] = True
                ustate["session_id"] = session_id
                ustate["live_started_at"] = utc_now_iso()
                ustate["rapid_until_epoch"] = 0.0
                state_changed = True

                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                outpath = recordings_dir / f"{username}_{ts}_{session_id}.mp4"

                log(f"{username}: LIVE STARTED (room_id={session_id}) -> {outpath}")
                spawn_notifier(username, f"LIVE started. Recording to {outpath.name}")

                proc = spawn_recorder(username, str(outpath), session_id)
                recorders[username] = proc

            elif prev_live and not now_live:
                # LIVE ENDED
                ustate["is_live"] = False
                ustate["live_ended_at"] = utc_now_iso()
                ustate["rapid_until_epoch"] = now_epoch + rapid_watch_seconds
                state_changed = True

                log(f"{username}: LIVE ENDED. Rapid-watch for {rapid_watch_seconds}s.")
                spawn_notifier(username, "LIVE ended.")

            # Recorder health check (notify once, then stop tracking to prevent spam)
            if now_live and username in recorders:
                proc = recorders[username]
                if proc.poll() is not None:
                    log(f"{username}: recorder exited early (code={proc.returncode})")
                    spawn_notifier(username, f"Recorder exited early (code={proc.returncode}).")
                    del recorders[username]

        if state_changed:
            save_state(state)

        time.sleep(0.25)

    log("Stopping WatchTok...")
    for username, proc in list(recorders.items()):
        if proc.poll() is None:
            log(f"Terminating recorder for {username} (pid={proc.pid})")
            try:
                proc.terminate()
            except Exception:
                pass

    log("Bye.")


if __name__ == "__main__":
    main()
