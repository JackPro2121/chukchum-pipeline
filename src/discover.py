import csv
import sys
from config import YOUTUBE_ACTOR, DEFAULT_SEARCH_QUERIES, CREATORS_CSV
from apify_client import run_actor


def _is_english(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return True
    ascii_letters = sum(1 for c in letters if ord(c) < 128)
    return ascii_letters / len(letters) > 0.8


TIER1 = {"united states", "usa", "us", "united kingdom", "uk", "great britain", "england"}
TIER2 = {"canada", "australia", "new zealand", "ireland", "south africa", "germany", "netherlands", "singapore"}
INDIA = {"india"}


def region_tier(location: str | None) -> int:
    loc = (location or "").lower()
    if any(t in loc for t in TIER1):
        return 1
    if any(t in loc for t in INDIA):
        return 3
    if any(t in loc for t in TIER2):
        return 2
    return 2


def niche(title: str | None, hashtags) -> str:
    text = f"{title or ''} {' '.join(hashtags or [])}".lower()
    for key, tag in [
        ("vlog", "vlog"), ("day in", "vlog"), ("routine", "vlog"), ("what i eat", "vlog"),
        ("comedy", "comedy"), ("funny", "comedy"), ("dance", "dance"),
        ("cook", "cooking"), ("recipe", "cooking"), ("food", "food"),
        ("motivat", "motivation"), ("gym", "fitness"), ("workout", "fitness"),
        ("travel", "travel"), ("music", "music"), ("prank", "prank"),
        ("fashion", "fashion"), ("life hack", "lifestyle"), ("gaming", "gaming"),
        ("cricket", "cricket"), ("news", "news"),
    ]:
        if key in text:
            return tag
    return "general"


def discover(queries=None, max_results=15):
    items = run_actor(
        YOUTUBE_ACTOR,
        {
            "searchQueries": queries or DEFAULT_SEARCH_QUERIES,
            "maxResults": max_results,
            "maxResultsShorts": 5,
            "sortingOrder": "views",
            "dateFilter": "month",
        },
    )
    seen = {}
    for it in items:
        cid = it.get("channelId")
        if not cid or cid in seen:
            continue
        title = it.get("title") or ""
        if not _is_english(title):
            continue
        if (it.get("numberOfSubscribers") or 0) < 10000:
            continue
        date = str(it.get("date") or "")[:10]
        if date:
            from datetime import datetime, timezone
            try:
                dt = datetime.fromisoformat(date.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                age_days = (datetime.now(timezone.utc) - dt).days
                if age_days > 30:
                    continue
            except ValueError:
                pass
        seen[cid] = {
            "channel_name": it.get("channelName"),
            "channel_url": it.get("channelUrl"),
            "channel_username": it.get("channelUsername"),
            "location": it.get("location") or it.get("channelLocation"),
            "region_tier": region_tier(it.get("location") or it.get("channelLocation")),
            "subscribers": it.get("numberOfSubscribers"),
            "sample_video_url": it.get("url"),
            "video_title": it.get("title"),
            "video_views": it.get("viewCount"),
            "niche": niche(it.get("title"), it.get("hashtags")),
        }
    rows = list(seen.values())
    rows.sort(key=lambda r: (r["region_tier"], -(r["video_views"] or 0)))
    with open(CREATORS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        w.writeheader()
        w.writerows(rows)
    print(f"Found {len(rows)} unique creators -> {CREATORS_CSV}")


if __name__ == "__main__":
    args = sys.argv[1:]
    max_results = 15
    if args and args[0].isdigit():
        max_results = int(args.pop(0))
    discover(args or None, max_results)
