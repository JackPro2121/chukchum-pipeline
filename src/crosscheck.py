import csv
import sys
from config import GOOGLE_SEARCH_ACTOR, CREATORS_CSV
from apify_client import run_actor

PLATFORM_SITES = {
    "tiktok": "tiktok.com",
    "instagram": "instagram.com",
    "facebook": "facebook.com",
}





def _is_profile_url(platform: str, url: str) -> bool:
    if f"{PLATFORM_SITES[platform].split('.')[0]}" not in url:
        return False
    if any(bad in url for bad in ("/search", "/explore", "/popular", "/tag/", "/hashtag", "/videos/", "/posts/", "/video/", "/reel/", "/p/", "/watch")):
        return False
    if platform == "tiktok":
        path = url.split("tiktok.com")[-1].strip("/")
        return path.startswith("@") and "/" not in path
    if platform == "instagram":
        path = url.split("instagram.com/")[-1].strip("/")
        return bool(path) and "/" not in path
    if platform == "facebook":
        path = url.split("facebook.com/")[-1].strip("/")
        return bool(path)
    return False


def crosscheck(csv_path=CREATORS_CSV, limit=None):
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    targets = rows[:limit] if limit else rows
    queries = []
    q_index = {}
    for i, r in enumerate(targets):
        name = (r.get("channel_name") or "").strip()
        if not name:
            continue
        for platform, site in PLATFORM_SITES.items():
            if r.get(f"{platform}_url"):
                continue
            q = f'site:{site} "{name}"'
            queries.append(q)
            q_index[q] = (i, platform)
    if queries:
        items = run_actor(
            GOOGLE_SEARCH_ACTOR,
            {
                "queries": "\n".join(queries),
                "maxPagesPerQuery": 1,
                "resultsPerPage": 3,
                "countryCode": "us",
            },
            timeout_sec=600,
        )
        for it in items:
            key = it.get("searchQuery", "").get("term") or it.get("searchQuery", {}).get("query") or it.get("searchQuery")
            if isinstance(key, dict):
                key = key.get("term") or key.get("query") or ""
            if key not in q_index:
                for q in q_index:
                    if key and (key in q or q in key):
                        key = q
                        break
            if key not in q_index:
                continue
            i, platform = q_index[key]
            found = ""
            for res in it.get("organicResults", []) or []:
                url = (res.get("url") or "").lower()
                if not _is_profile_url(platform, url):
                    continue
                found = res.get("url")
                break
            targets[i][f"{platform}_url"] = found
            print(f"{targets[i]['channel_name']} -> {platform}: {found or 'NOT FOUND'}")
    for r in rows:
        r["missing_platforms"] = ",".join(
            p for p in PLATFORM_SITES if not r.get(f"{p}_url")
        )
    fields = list(rows[0].keys()) if rows else []
    for extra in ("tiktok_url", "instagram_url", "facebook_url", "missing_platforms"):
        if extra not in fields:
            fields.append(extra)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"Updated {csv_path}")


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else None
    crosscheck(limit=limit)
