#!/usr/bin/env python3
import json
import sys
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(msg: str) -> None:
    print(f"[{utc_now_iso()}] {msg}", flush=True)


def load_config() -> dict:
    with open(ROOT / "config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def post_ntfy(url: str, message: str) -> None:
    data = message.encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        resp.read()


def main():
    if len(sys.argv) < 3:
        print("Usage: notifier.py <username> <message>", file=sys.stderr)
        sys.exit(2)

    username = sys.argv[1]
    text = " ".join(sys.argv[2:])

    cfg = load_config()
    ncfg = cfg.get("notifier", {})
    if ncfg.get("type") != "ntfy":
        sys.exit(0)

    url = ncfg.get("ntfy_url")
    if not url:
        log("ntfy_url missing; nothing to do.")
        sys.exit(0)

    msg = f"[WatchTok] [{username}] {text}"
    log(f"Sending ntfy: {msg}")
    post_ntfy(url, msg)
    log("Sent.")


if __name__ == "__main__":
    main()
