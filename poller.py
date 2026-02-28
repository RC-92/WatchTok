#!/usr/bin/env python3
import json
import re
import time
import urllib.request
import urllib.error
from typing import List, Optional, Dict, Tuple

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

ROOM_ID_PATTERNS = [
    re.compile(r'"roomId"\s*:\s*"?(?P<id>\d+)"?', re.IGNORECASE),
    re.compile(r'"room_id"\s*:\s*"?(?P<id>\d+)"?', re.IGNORECASE),
    re.compile(r'"liveRoomId"\s*:\s*"?(?P<id>\d+)"?', re.IGNORECASE),
]

CHECK_ALIVE_URL = "https://webcast.tiktok.com/webcast/room/check_alive/?aid=1988&room_ids={room_ids}"


def _normalize_username(u: str) -> str:
    u = u.strip()
    return u[1:] if u.startswith("@") else u


def _http_get(url: str, accept: str, timeout: int = 12) -> Tuple[int, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": accept,
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = resp.getcode()
        body = resp.read().decode("utf-8", errors="ignore")
        return status, body


def _extract_room_ids(html: str) -> List[str]:
    ids: List[str] = []
    for pat in ROOM_ID_PATTERNS:
        for m in pat.finditer(html):
            ids.append(m.group("id"))

    # De-dupe preserving order
    seen = set()
    out = []
    for rid in ids:
        if rid not in seen:
            out.append(rid)
            seen.add(rid)
    return out


def _check_alive(room_ids: List[str], timeout: int = 12) -> Optional[str]:
    """
    Returns the first room_id that is alive, else None.
    """
    if not room_ids:
        return None

    url = CHECK_ALIVE_URL.format(room_ids=",".join(room_ids))
    status, body = _http_get(url, accept="application/json,text/plain,*/*", timeout=timeout)
    if status != 200 or not body:
        return None

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return None

    for item in data.get("data", []):
        if item.get("alive") is True:
            return str(item.get("room_id_str") or item.get("room_id"))
    return None


def is_user_live(username: str) -> Dict:
    """
    Accurate LIVE check without login:
      - Extract room_ids from /@user/live
      - Verify using webcast room/check_alive
    Returns:
      {"is_live": bool, "session_id": str|None}
    session_id = alive room_id
    """
    u = _normalize_username(username)
    live_page = f"https://www.tiktok.com/@{u}/live"

    # Try twice to smooth transient issues
    for attempt in range(2):
        try:
            status, html = _http_get(live_page, accept="text/html,*/*", timeout=12)
            if status != 200 or not html:
                return {"is_live": False, "session_id": None}

            room_ids = _extract_room_ids(html)
            alive_room = _check_alive(room_ids, timeout=12)

            if alive_room:
                return {"is_live": True, "session_id": alive_room}
            return {"is_live": False, "session_id": None}

        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            if attempt == 0:
                time.sleep(0.75)
                continue
            return {"is_live": False, "session_id": None}

    return {"is_live": False, "session_id": None
            }
