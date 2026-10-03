import sys
from apify_client import run_actor

QUERY = sys.argv[1] if len(sys.argv) > 1 else "funny shorts"
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 5

searches = [
    ("YouTube", "streamers~youtube-scraper", {"searchQueries": [QUERY], "maxResults": LIMIT, "maxResultsShorts": 3}),
    ("Instagram", "apify~instagram-hashtag-scraper", {"hashtags": [QUERY.replace(" ", "")], "resultsLimit": LIMIT}),
    ("Twitter/X", "apidojo~tweet-scraper", {"searchTerms": [QUERY], "maxResults": LIMIT}),
    ("Facebook", "scraper_one~facebook-posts-search", {"query": QUERY, "resultsCount": LIMIT}),
]

import re
from urllib.parse import urlparse

for platform, actor, inp in searches:
    print(f"\n=== {platform} ===")
    try:
        items = run_actor(actor, inp, timeout_sec=400)
        creators = {}
        for it in items:
            if platform == "YouTube":
                key = it.get("channelName"); url = it.get("channelUrl")
            elif platform == "Instagram":
                owner = it.get("ownerUsername") or it.get("ownerFullName"); url = f"https://instagram.com/{owner}" if it.get('ownerUsername') else None
                key = owner
            elif platform == "Twitter/X":
                au = it.get("author", {}); key = au.get("userName"); url = f"https://x.com/{key}" if key else None
            else:
                a = it.get("author") or {}
                key = a.get("name") or it.get("pageName") or it.get("userName")
                url = a.get("profileUrl") or it.get("url")
            if key and key not in creators:
                creators[key] = url
        for k, v in list(creators.items())[:10]:
            print(f"  {k} {v or ''}")
    except Exception as e:
        print("  ERROR:", str(e)[:200])
