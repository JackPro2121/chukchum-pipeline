import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")
from apify_client import run_actor

name = sys.argv[1] if len(sys.argv) > 1 else "classicboy2659"
qs = "\n".join(
    f"site:{site} \"{name}\"" for site in ("tiktok.com", "facebook.com", "youtube.com")
)
items = run_actor(
    "apify~google-search-scraper",
    {"queries": qs, "maxPagesPerQuery": 1, "resultsPerPage": 5, "countryCode": "us"},
    timeout_sec=300,
)
for it in items:
    q = it.get("searchQuery")
    term = q.get("term") if isinstance(q, dict) else q
    print("QUERY:", term)
    for r in (it.get("organicResults") or [])[:3]:
        print("  ->", r.get("url"))
