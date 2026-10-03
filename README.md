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
| `storage.py` | sqlite state (`creators`, `processed_videos`) |
| `apify_client.py` | run Apify actors |
| `discover.py` | YouTube creator discovery (niche/region tiering) |
| `crosscheck.py` | Google-site search presence check per platform |
| `verify.py` | last-post age per platform |
| `search.py` | YT/IG/X/FB keyword search via Apify |
| `lookup.py` | site:-search a name on TikTok/FB/YT |
| `downloader.py` | latest video URL + download (yt-dlp) |
| `enhancer.py` | ffmpeg uniquify: crop/scale, speed, pitch, brand overlay |
| `media_host.py` | upload to Cloudflare R2, return public URL |
| `buffer_client.py` | Buffer GraphQL: channels, createPost |
| `pipeline.py` | orchestrator (CLI entry) |

## Setup

```powershell
pip install -r requirements.txt
copy .env.example .env   # fill secrets
```

## Usage

```powershell
cd src
python discover.py 10        # refresh creator list
python crosscheck.py 10      # fill in per-platform URLs
python verify.py 10          # compute last-post age
python pipeline.py 2         # process up to 2 creators
```

## GitHub Actions

`.github/workflows/daily.yml` runs the pipeline on a 6-hour schedule.
Required repo secrets: `APIFY_TOKEN`, `BUFFER_API_KEY`, `R2_ENDPOINT`,
`R2_ACCESS_KEY`, `R2_SECRET_KEY`, `R2_BUCKET`, `R2_PUBLIC_BASE`.

## Legal note

Re-publishing creators' content requires permission or transformative/licensed use.
Prefer creators you have permission from, or your own library.
