import csv
import re
import sys
from datetime import datetime, timezone
from config import CREATORS_CSV
from apify_client import run_actor

ACTIVE_DAYS = 45


def _days_old(ts) -> float | None:
    if not ts:
        return None
    try:
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        else:
            t = str(ts).replace("Z", "+00:00")
            dt = datetime.fromisoformat(t)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).days
    except (ValueError, OSError, OverflowError):
        return None


def _latest_youtube(url):
    items = run_actor("streamers~youtube-scraper", {"startUrls": [{"url": url}], "maxResults": 3}, timeout_sec=300)
    ages = [a for a in (_days_old(it.get("date")) for it in items) if a is not None]
    return min(ages) if ages else None


def _latest_tiktok(url):
    items = run_actor("clockworks~tiktok-scraper", {"profiles": [url], "resultsPerPage": 3}, timeout_sec=300)
    ages = [a for a in (_days_old(it.get("createTimeISO") or it.get("createTime")) for it in items) if a is not None]
    return min(ages) if ages else None


def _latest_instagram(url):
    m = re.search(r"instagram\.com/([^/?]+)", url)
    if not m:
        return None
    items = run_actor("apify~instagram-profile-scraper", {"usernames": [m.group(1)], "resultsLimit": 3}, timeout_sec=300)
    for it in items:
        for key in ("latestPosts", "latestIgtvVideos", "reels"):
            for post in it.get(key) or []:
                a = _days_old(post.get("timestamp") or post.get("takenAtTimestamp"))
                if a is not None:
                    return a
    return None


def _latest_facebook(url):
    items = run_actor("apify~facebook-pages-scraper", {"startUrls": [{"url": url}], "maxPosts": 3}, timeout_sec=300)
    ages = []
    for it in items:
        for post in it.get("latestPosts") or it.get("posts") or []:
            a = _days_old(post.get("time") or post.get("date"))
            if a is not None:
                ages.append(a)
        if not ages:
            a = _days_old(it.get("time") or it.get("date"))
            if a is not None:
                ages.append(a)
    return min(ages) if ages else None


CHECKS = {
    "youtube_days": ("channel_url", _latest_youtube),
    "tiktok_days": ("tiktok_url", _latest_tiktok),
    "instagram_days": ("instagram_url", _latest_instagram),
    "facebook_days": ("facebook_url", _latest_facebook),
}


def verify(csv_path=CREATORS_CSV, limit=None):
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    targets = rows[:limit] if limit else rows
    for r in targets:
        for col, (src_col, fn) in CHECKS.items():
            if r.get(col) not in (None, ""):
                continue
            url = r.get(src_col, "")
            if not url:
                continue
            try:
                days = fn(url)
            except Exception as e:
                print(f"{r['channel_name']} {src_col} ERROR: {e}")
                continue
            r[col] = "" if days is None else str(round(days, 1))
            print(f"{r['channel_name']} {src_col}: {r[col] or 'no data'} days ago")
        active = [p for p, c in CHECKS.items() if r.get(c) not in (None, "") and float(r[c]) <= ACTIVE_DAYS]
        r["active_platforms"] = ",".join(p.replace("_days", "") for p in active)
    fields = list(rows[0].keys()) if rows else []
    for extra in list(CHECKS) + ["active_platforms"]:
        if extra not in fields:
            fields.append(extra)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"Updated {csv_path}")


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else None
    verify(limit=limit)
