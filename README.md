# ChukChum — Cross-Platform Creator Content Pipeline

Finds creators already active on one platform, verifies which platforms they are **missing**
from, then downloads their latest video, enhances it lightly (re-encode + watermark +
speed/pitch tweak), uploads to a public bucket, and schedules it via Buffer to the
missing platforms (TikTok / YouTube Shorts / Facebook Reels).

## Architecture

```
Apify (discover, cross-check, verify) -> creators.csv
       |
pipeline.py -> downloader (yt-dlp) -> enhancer (ffmpeg)
                                   -> media_host (Cloudflare R2)
                                   -> buffer_client (GraphQL createPost)
                                   -> storage (sqlite state)
```

## Modules (src/)

| File | Role |
|---|---|
| `config.py` | env-driven settings |
| `storage.py` | sqlite state (`creators`, `processed_videos`, `processed_sources`) |
| `apify_client.py` | run Apify actors |
| `fetch_targets.py` | latest unposted reel per target creator + Ollama caption |
| `discover.py` | YouTube creator discovery (niche/region tiering) |
| `crosscheck.py` | Google-site search presence check per platform |
| `verify.py` | last-post age per platform |
| `search.py` / `lookup.py` | YT/IG/X/FB keyword search via Apify |
| `creators_state.py` | eligible creator selector |
| `downloader.py` | latest video URL + download (yt-dlp) |
| `enhancer.py` | ffmpeg: 9:16 crop/scale, color and sharpness correction, subtitles-ready safe layout, loudness-normalized audio, subtle brand watermark, faststart |
| `media_repo.py` | commit video to `chukchum-media`, return public raw URL |
| `buffer_client.py` | Buffer GraphQL: channels, createPost |
| `pipeline_v2.py` | orchestrator for the target list (CLI entry) |
| `cleanup_media.py` | prune media older than 10 days once posts are sent |

## Setup

```powershell
pip install -r requirements.txt
copy .env.example .env   # fill secrets
```

## Usage

```powershell
cd src
python fetch_targets.py   # latest unposted reel per creator + Ollama caption
python pipeline_v2.py     # enhance, host, queue to Buffer
python cleanup_media.py   # prune media older than 10 days (only if posts are sent)
```

Targets live in `src/fetch_targets.py` (`TARGETS`). Dedup state lives in
`data/state.db` (`processed_videos`), so a reel is never queued twice.

## Queue safety

Buffer free plan allows a limited number of scheduled posts per channel, and a brand-new
Facebook page should not suddenly publish a burst of content. Two guards are enforced in
`pipeline_v2.py`:

| Guard | Default | Meaning |
|---|---|---|
| `MAX_QUEUE_PER_CHANNEL` | `8` | skip posting if the channel already has this many scheduled/sending posts |
| `MAX_POSTS_PER_RUN` | `2` | cap how many posts a single run may create |

Schedule is once per day (`20 6 * * *`) with `MAX_POSTS_PER_RUN=1`, so a fresh page ramps up
at ~1 reel/day instead of 3.

## GitHub Actions

`.github/workflows/daily.yml` runs daily at 06:20 UTC and on manual dispatch:

1. checks out the pipeline and `JackPro2121/chukchum-media`
2. installs ffmpeg + deps
3. `fetch_targets.py` → newest reel per creator that is not already queued
4. `pipeline_v2.py` → enhance → commit media → Buffer `createPost`
5. commits `data/state.db` + `data/targets.csv` back to the repo

Required repository secrets:

| Secret | Purpose |
|---|---|
| `APIFY_TOKEN` | Apify actors (IG profile scraper) |
| `OLLAMA_API_KEY` | Ollama Cloud caption generation |
| `BUFFER_API_KEY` | Buffer GraphQL API |
| `MEDIA_REPO_TOKEN` | PAT with `repo` scope, to push media into `chukchum-media` |

## Legal note

Re-publishing creators' content requires permission or transformative/licensed use.
Prefer creators you have permission from, or your own library.
