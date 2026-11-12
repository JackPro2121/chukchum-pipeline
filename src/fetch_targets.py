import csv
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
import requests

from apify_client import run_actor
import storage
from config import (
    GROQ_API,
    GROQ_API_KEY,
    GROQ_MODEL,
    MAX_POSTS_PER_RUN,
    OLLAMA_API,
    OLLAMA_API_KEY,
    OLLAMA_MODEL,
)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TARGETS = [
    {"username": "classicboy2659", "category": "comedy"},
    {"username": "bade__chote_", "category": "comedy"},
    {"username": "anyongphet", "category": "pets comedy"},
]

PROFILE_ACTOR = "apify~instagram-profile-scraper"
MIN_PREFERRED_LIKES = 1500
MAX_VIDEO_SECONDS = 75


def _rotated_targets() -> list[dict]:
    """Rotate targets deterministically per run slot so no single creator hogs every run."""
    now = datetime.now(timezone.utc)
    slot = now.timetuple().tm_yday * 12 + (now.hour // 2)
    offset = slot % len(TARGETS)
    return TARGETS[offset:] + TARGETS[:offset]


def fetch_recent_videos(username: str, limit: int = 24) -> list[dict]:
    items = run_actor(
        PROFILE_ACTOR,
        {"usernames": [username], "resultsLimit": limit},
        timeout_sec=300,
    )
    if not items:
        return []
    posts = items[0].get("latestPosts") or []
    vids = []
    for p in posts:
        if p.get("type") != "Video" or not p.get("videoUrl"):
            continue
        dur = p.get("videoDuration")
        if isinstance(dur, (int, float)) and dur > MAX_VIDEO_SECONDS:
            continue
        vids.append(p)
    # Viral-first ranking: prefer proven high-engagement reels over untested newest uploads.
    vids.sort(key=lambda p: (p.get("likesCount") or 0, p.get("videoViewCount") or 0), reverse=True)
    return vids[:limit]


def pick_next_unprocessed(username: str, category: str) -> dict | None:
    candidates = []
    for v in fetch_recent_videos(username):
        if storage.already_processed(v["url"]):
            continue
        candidates.append(v)
    if not candidates:
        return None
    strong = [v for v in candidates if (v.get("likesCount") or 0) >= MIN_PREFERRED_LIKES]
    chosen = strong[0] if strong else candidates[0]
    print(
        f"  picked viral candidate ({chosen.get('likesCount', 0)} likes, "
        f"{chosen.get('videoDuration', '?')}s): {chosen['url']}"
    )
    return chosen


def _call_groq(prompt: str) -> str:
    """Call Groq OpenAI-compatible chat completions endpoint."""
    body: dict = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.75,
        "max_completion_tokens": 450,
    }
    model_lower = GROQ_MODEL.lower()
    if "qwen" in model_lower:
        body["reasoning_effort"] = "none"
    elif "gpt-oss" in model_lower:
        body["reasoning_effort"] = "low"
        body["max_completion_tokens"] = 650

    r = requests.post(
        f"{GROQ_API.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json=body,
        timeout=60,
    )
    r.raise_for_status()
    text = (r.json()["choices"][0]["message"].get("content") or "").strip()
    if not text:
        raise RuntimeError(f"Groq returned empty content for model {GROQ_MODEL}")
    return text


def _call_ollama(prompt: str) -> str:
    """Call Ollama Cloud chat endpoint."""
    body = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    r = requests.post(
        f"{OLLAMA_API.rstrip('/')}/api/chat",
        headers={"Authorization": f"Bearer {OLLAMA_API_KEY}", "Content-Type": "application/json"},
        json=body,
        timeout=90,
    )
    r.raise_for_status()
    text = (r.json()["message"].get("content") or "").strip()
    if not text:
        raise RuntimeError(f"Ollama returned empty content for model {OLLAMA_MODEL}")
    return text


def _clean_ascii_hook(raw: str) -> str:
    """Ensure hook banner text renders cleanly in FFmpeg drawtext without emoji tofu boxes."""
    ascii_only = re.sub(r"[^\x20-\x7E]", " ", raw or "")
    ascii_only = re.sub(r"[\"'`]+", "", ascii_only)
    ascii_only = re.sub(r"\s+", " ", ascii_only).strip()
    words = ascii_only.split()[:7]
    hook = " ".join(words).upper()
    return hook or "THIS TWIST WAS UNREAL"


def _invoke_llm(prompt: str) -> str:
    providers = []
    if GROQ_API_KEY:
        providers.append(("groq", _call_groq))
    if OLLAMA_API_KEY:
        providers.append(("ollama", _call_ollama))
    if not providers:
        raise RuntimeError("Neither GROQ_API_KEY nor OLLAMA_API_KEY is set. Configure one in .env or GitHub secrets.")

    last_err: Exception | None = None
    for name, fn in providers:
        try:
            return fn(prompt)
        except Exception as e:
            print(f"  [warn] caption provider '{name}' failed: {e}")
            last_err = e
    raise last_err  # type: ignore[misc]


def generate_caption_and_hook(caption: str, category: str) -> tuple[str, str]:
    prompt = (
        "You are an expert viral Facebook Reels editor and meme page manager.\n"
        "From the source Instagram reel caption below, generate JSON with two fields:\n"
        '1) "hook_text": A short 3 to 6 word punchy on-screen meme header to burn at the top of the video. '
        "Rules for hook_text: STRICTLY ASCII characters only (no emojis, no quotes), high curiosity, "
        "Roman Urdu/Hinglish or simple English depending on source, DO NOT say 'wait for the end' or 'wait till you see'.\n"
        '2) "fb_caption": A fresh Facebook Reel post caption: 1 punchy relatable/funny hook line + '
        "1 crisp reaction line + 3 to 5 specific relevant hashtags (avoid generic spam tags). "
        "Rules: keep the original Hinglish/English/Thai vibe (do not awkwardly translate), no credit to creator, "
        "DO NOT copy the source caption word for word, NEVER start with 'Wait for the end' or 'Wait till you see'.\n"
        f"Category: {category}\n"
        f"Source caption:\n{caption}\n\n"
        "Return ONLY valid JSON: {\"hook_text\": \"...\", \"fb_caption\": \"...\"}"
    )
    raw = _invoke_llm(prompt)
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.S).strip()
    m = re.search(r"\{.*\}", cleaned, flags=re.S)
    if m:
        cleaned = m.group(0)
    try:
        parsed = json.loads(cleaned)
        fb_caption = str(parsed.get("fb_caption") or "").strip()
        hook_text = _clean_ascii_hook(str(parsed.get("hook_text") or ""))
        if fb_caption:
            return fb_caption, hook_text
    except Exception:
        pass
    # Graceful fallback if model returned plain text instead of JSON.
    return raw.strip(), "YOU DID NOT EXPECT THAT"


def generate_fb_caption(caption: str, category: str, title_hint: str = "") -> str:
    fb_caption, _ = generate_caption_and_hook(caption, category)
    return fb_caption


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
    # Collect just enough candidates for this run (+1 spare) so Apify credits aren't wasted.
    desired = max(2, MAX_POSTS_PER_RUN + 1)
    for t in _rotated_targets():
        if len(rows) >= desired:
            break
        top = pick_next_unprocessed(t["username"], t["category"])
        if not top:
            print(f"{t['username']}: nothing new to post")
            continue
        print(f"{t['username']} -> reel: {top['url']} | likes={top.get('likesCount')}")
        fb_caption, hook_text = generate_caption_and_hook(top.get("caption", ""), t["category"])
        print("  Hook banner:", hook_text)
        print("  FB caption :", fb_caption[:80].replace("\n", " "))
        out = str(Path(DOWNLOAD_DIR) / f"{t['username']}_top.mp4")
        curl_download(top["videoUrl"], out)
        rows.append(
            {
                "username": t["username"],
                "category": t["category"],
                "reel_url": top["url"],
                "video_file": out,
                "fb_caption": fb_caption,
                "hook_text": hook_text,
                "likes": top.get("likesCount"),
            }
        )
    fieldnames = ["username", "category", "reel_url", "video_file", "fb_caption", "hook_text", "likes"]
    with open(TARGETS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print("Saved ->", TARGETS_CSV)


if __name__ == "__main__":
    main()
