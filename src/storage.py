import sqlite3
from datetime import datetime, timezone
from config import DB_PATH
from pathlib import Path

Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS creators (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  channel_name TEXT,
  channel_url TEXT UNIQUE,
  instagram_url TEXT,
  tiktok_url TEXT,
  facebook_url TEXT,
  niche TEXT,
  last_verified TEXT
);
CREATE TABLE IF NOT EXISTS processed_videos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  creator_url TEXT,
  video_source_url TEXT UNIQUE,
  video_file TEXT,
  public_url TEXT,
  platforms_posted TEXT,
  status TEXT,
  created_at TEXT
);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        try:
            conn.execute("ALTER TABLE processed_videos ADD COLUMN caption TEXT")
        except sqlite3.OperationalError:
            pass


def upsert_creator(row: dict):
    init()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO creators (channel_name, channel_url, instagram_url, tiktok_url, facebook_url, niche, last_verified)"
            " VALUES (?,?,?,?,?,?,?)"
            " ON CONFLICT(channel_url) DO UPDATE SET"
            " instagram_url=excluded.instagram_url, tiktok_url=excluded.tiktok_url,"
            " facebook_url=excluded.facebook_url, niche=excluded.niche, last_verified=excluded.last_verified",
            (row["channel_name"], row["channel_url"], row.get("instagram_url", ""),
             row.get("tiktok_url", ""), row.get("facebook_url", ""), row.get("niche", ""),
             datetime.now(timezone.utc).isoformat()),
        )


def record_video(creator_url, source, file, public_url, platforms, status="done", caption=None):
    init()
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO processed_videos"
            " (creator_url, video_source_url, video_file, public_url, platforms_posted, status, created_at, caption)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (creator_url, source, file, public_url, ",".join(platforms), status,
             datetime.now(timezone.utc).isoformat(), caption),
        )


def all_videos() -> list[dict]:
    init()
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute("SELECT * FROM processed_videos")]


def already_processed(source_url: str) -> bool:
    init()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM processed_videos WHERE video_source_url=? AND status='done'",
            (source_url,),
        ).fetchone()
    return bool(row)
