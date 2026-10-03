import csv
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config import CREATORS_CSV
from creators_state import eligible_creators, missing_platforms


def run(max_creators: int = 2, videos_per_creator: int = 1):
    import storage, downloader, enhancer, buffer_client, media_repo
    from config import ENABLED_SERVICES

    creators = eligible_creators()
    print(f"Eligible creators: {len(creators)}")
    for c in creators[:max_creators]:
        missing = missing_platforms(c)
        print(f"\n>>> {c['channel_name']} missing={missing}")
        if not missing:
            print("   skip (present everywhere)")
            continue
        source = c.get("sample_video_url") or c.get("channel_url")
        if not source:
            continue
        if storage.already_processed(source):
            print("   already processed, skip")
            continue
        local = downloader.download_video(source)
        if not local:
            print("   download failed")
            continue
        enhanced = enhancer.enhance(local)
        try:
            public_url = media_repo.add(enhanced)
        except Exception as e:
            print("MEDIA REPO ERROR:", e)
            storage.record_video(c["channel_url"], source, enhanced, "", [], status="failed-host", caption=video_caption(c))
            continue
        services = [s for s in missing if (not ENABLED_SERVICES or s in ENABLED_SERVICES)]
        posted = []
        for service in services:
            try:
                res = buffer_client.post_to_service(service, video_caption(c), public_url)
                posted.append(service)
                try:
                    print("  post:", res)
                except UnicodeError:
                    print("  post: success (caption contains non-ascii emoji)")
            except Exception as e:
                print(f"  {service} ERROR: {str(e)[:200]}")
        status = "done" if posted else "error"
        storage.record_video(c["channel_url"], source, enhanced, public_url, posted, status=status, caption=video_caption(c))


def video_caption(c: dict) -> str:
    return f"{c.get('video_title','New clip')} #shorts #viral #trending"


if __name__ == "__main__":
    max_c = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 2
    run(max_creators=max_c)
