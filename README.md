WatchTok is an OSINT tool that automatically and autonomously detects and records when a TikTok user goes live.

# Features
- Monitors multiple TikTok users simultaneously
- Automatically records live streams using yt-dlp
- Push notifications via [ntfy.sh](https://ntfy.sh)
- Rapid polling after a stream ends to catch restarts
- Runs headless on any Linux server — no browser required

# Installation:

``git clone https://github.com/RC-92/WatchTok.git ``
``cd WatchTok ``
``chmod +x *.sh ./install.sh``
## Configuration
1. Edit `config.json`
```json
{
    "users": ["user1", "user2"],
    "poll_interval_seconds": 12,
    "rapid_watch_seconds": 600,
    "rapid_poll_interval_seconds": 5,
    "recordings_dir": "./recordings",
    "notifier": {
        "type": "ntfy",
        "ntfy_url": "https://ntfy.sh/your-topic-here"
    }
}
```

| Field                         | Description                                                      |
| ----------------------------- | ---------------------------------------------------------------- |
| `users`                       | TikTok usernames to monitor (without `@`)                        |
| `poll_interval_seconds`       | How often to check if a user is live                             |
| `rapid_watch_seconds`         | Duration of rapid polling after a stream ends                    |
| `rapid_poll_interval_seconds` | Poll interval during rapid watch period                          |
| `recordings_dir`              | Where recordings are saved                                       |
| `notifier.ntfy_url`           | Your [ntfy.sh](https://ntfy.sh) topic URL for push notifications |
# Usage
## Start monitoring
./start.sh
## Check logs
tail -f logs/main.log
## Stop monitoring
./stop.sh

# Recordings
Recordings are saved to the `recordings/` directory as `.mp4` files with the format:

```
username_YYYYMMDD_HHMMSS_roomid.mp4
```

Note: You can change the output directory in the Config.json file

# Backend:
- **Poller** periodically checks each user's TikTok live page for active room IDs
- **Verifier** confirms the stream is live via TikTok's `check_alive` API
- **Recorder** uses `yt-dlp` to capture the live stream directly
- **Notifier** sends push notifications on stream start/end via ntfy
- When a stream ends, rapid polling kicks in to catch quick restarts
