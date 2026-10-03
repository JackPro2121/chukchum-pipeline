import csv
import sys
import requests
import subprocess
import sys
from pathlib import Path

from apify_client import run_actor
import storage
from config import OLLAMA_API_KEY, OLLAMA_API, OLLAMA_MODEL

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TARGETS = [
    {"username": "classicboy2659", "category": "comedy"},
    {"username": "bade__chote_", "category": "comedy"},
]

CATEGORIES = {
    "comedy": ["funny", "laugh", "comedy", "joke", "prank", "😂", "🤣", "khilna", "maza"],
    "relationship": ["relationship", "love", "pyaar", "wife", "husband", "pati", "patidevi", "life partner", "रिश्ते", "प्यार"],
}

PROFILE_ACTOR = "apify~instagram-profile-scraper"


def fetch_recent_videos(username: str, limit: int = 12) -> list[dict]:
    items = run_actor(
        PROFILE_ACTOR,
        {"usernames": [username], "resultsLimit": 12},
        timeout_sec=300,
    )
    if not items:
        return []
    it = items[0]
    posts = it.get("latestPosts") or []
    vids = [p for p in posts if p.get("type") == "Video" and p.get("videoUrl")]
    vids.sort(key=lambda p: p.get("timestamp") or "", reverse=True)
    return vids[:limit]


def pick_next_unprocessed(username: str, category: str) -> dict | None:
    for v in fetch_recent_videos(username):
        if storage.already_processed(v["url"]):
            print(f"  skip (already posted): {v['url']} | {(v.get('caption') or '')[:40]}")
            continue
        return v
    return None


def generate_fb_caption(caption: str, category: str, title_hint: str = "") -> str:
    if not OLLAMA_API_KEY:
        raise RuntimeError("OLLAMA_API_KEY missing. Set it in .env or GitHub secrets.")
    prompt = (
        "You are a viral Facebook Reels content creator. Read the source caption of a reel and write a "
        "fresh Facebook caption: 1 short hook line + 1 line of context + 3 to 5 hashtags. "
        f"Rules: keep the original language (do not translate), no credit to the original creator, "
        f"no watermark text, do not copy the source caption word for word. Category: {category}\n\n"
        f"Source caption:\n{caption}\n\n"
        "Return ONLY the final caption text."
    )
    body = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    r = requests.post(
        f"{OLLAMA_API}/api/chat",
        headers={"Authorization": f"Bearer {OLLAMA_API_KEY}", "Content-Type": "application/json"},
        json=body,
        timeout=90,
    )
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


def curl_download(url: str, out: str):
    cmd = ["curl", "-L", "-o", out, "-H", "User-Agent: Mozilla/5.0", url]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)
    return out


def main():
    from config import DOWNLOAD_DIR, TARGETS_CSV
    Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
    rows = []
    for t in TARGETS:
        top = pick_next_unprocessed(t["username"], t["category"])
        if not top:
            print(f"{t['username']}: nothing new to post")
            continue
        print(f"{t['username']} -> reel: {top['url']} | likes={top.get('likesCount')}")
        fb_caption = generate_fb_caption(top.get("caption", ""), t["category"])
        print("  FB caption:", fb_caption[:80].replace("\n", " "))
        out = str(Path(DOWNLOAD_DIR) / f"{t['username']}_top.mp4")
        curl_download(top["videoUrl"], out)
        rows.append(
            {
                "username": t["username"],
                "category": t["category"],
                "reel_url": top["url"],
                "video_file": out,
                "fb_caption": fb_caption,
                "likes": top.get("likesCount"),
            }
        )
    with open(TARGETS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        w.writeheader()
        w.writerows(rows)
    print("Saved ->", TARGETS_CSV)


if __name__ == "__main__":
    main()
