import subprocess
import uuid
from pathlib import Path
from config import DOWNLOAD_DIR

Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)


def get_latest_video_url(profile_url: str) -> str | None:
    import yt_dlp
    opts = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist", "playlist_items": "1", "extractor_args": {"youtube": {"player_client": ["mweb", "android"]}}}
    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(profile_url, download=False)
        except Exception:
            return None
    if info and "entries" in info:
        for entry in info.get("entries") or []:
            if entry and entry.get("url"):
                return entry["url"]
    if info and info.get("url"):
        return info["url"]
    return None


def download_video(url: str) -> str | None:
    out = Path(DOWNLOAD_DIR) / f"{uuid.uuid4().hex}.mp4"
    cmd = ["yt-dlp", "-f", "best[ext=mp4]/best", "--no-progress", "--extractor-args", "youtube:player_client=mweb,android", "-o", str(out), url]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0 or not out.exists():
        print("yt-dlp error:", proc.stderr[-500:])
        return None
    return str(out)
