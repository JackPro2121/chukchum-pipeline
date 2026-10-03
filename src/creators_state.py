import csv
from config import CREATORS_CSV


def load_creators() -> list[dict]:
    try:
        with open(CREATORS_CSV, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        return []


def missing_platforms(row: dict) -> list[str]:
    return [p for p in ("tiktok", "instagram", "facebook") if not (row.get(f"{p}_url") or "")]


def eligible_creators() -> list[dict]:
    rows = load_creators()
    return [r for r in rows if (r.get("channel_url") and r.get("sample_video_url"))]
