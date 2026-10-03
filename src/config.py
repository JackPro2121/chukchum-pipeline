import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "")
BUFFER_API_KEY = os.environ.get("BUFFER_API_KEY", "")

CREATORS_CSV = str(ROOT / os.environ.get("CREATORS_CSV", "data/creators.csv"))
DB_PATH = str(ROOT / os.environ.get("DB_PATH", "data/state.db"))
DOWNLOAD_DIR = str(ROOT / os.environ.get("DOWNLOAD_DIR", "data/downloads"))
ENHANCED_DIR = str(ROOT / os.environ.get("ENHANCED_DIR", "data/enhanced"))

APIFY_BASE = "https://api.apify.com/v2"
BUFFER_API = "https://api.buffer.com"

R2_ENDPOINT = os.environ.get("R2_ENDPOINT", "")
R2_ACCESS_KEY = os.environ.get("R2_ACCESS_KEY", "")
R2_SECRET_KEY = os.environ.get("R2_SECRET_KEY", "")
R2_BUCKET = os.environ.get("R2_BUCKET", "")
R2_PUBLIC_BASE = os.environ.get("R2_PUBLIC_BASE", "").rstrip("/")

BRAND = os.environ.get("BRAND", "ChukChum")

MEDIA_REPO_DIR = os.environ.get("MEDIA_REPO_DIR", str(ROOT.parent / "chukchum-media"))
MEDIA_REPO = os.environ.get("MEDIA_REPO", "JackPro2121/chukchum-media")
ENABLED_SERVICES = [s.strip() for s in os.environ.get("ENABLED_SERVICES", "").split(",") if s.strip()]

YOUTUBE_ACTOR = "streamers~youtube-scraper"
GOOGLE_SEARCH_ACTOR = "apify~google-search-scraper"
INSTAGRAM_PROFILE_ACTOR = "apify~instagram-profile-scraper"
TIKTOK_SCRAPER_ACTOR = "clockworks~tiktok-scraper"
FACEBOOK_PAGES_ACTOR = "apify~facebook-pages-scraper"
YDOWNLOADER_ACTOR = "streamers~youtube-scraper"

DEFAULT_SEARCH_QUERIES = [
    "daily vlog day in my life",
    "vlog daily routine 2026",
    "lifestyle vlog daily uploads",
    "day in the life vlog",
    "travel vlog daily",
    "what i eat in a day vlog",
]
