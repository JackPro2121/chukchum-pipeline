import csv
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config import ENABLED_SERVICES, TARGETS_CSV
import storage, enhancer, buffer_client, media_repo


def video_caption(row: dict) -> str:
    return row["fb_caption"]


def run():
    with open(TARGETS_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"rows: {len(rows)}")
    for r in rows:
        print(f">>> {r['username']} :: {r['category']}")
        if storage.already_processed(r["reel_url"]):
            print("  already posted, skip")
            continue
        source_file = r["video_file"]
        enhanced = enhancer.enhance(source_file)
        try:
            public_url = media_repo.add(enhanced)
        except Exception as e:
            print("MEDIA REPO ERROR:", e)
            storage.record_video(r["reel_url"], r["reel_url"], enhanced, "", [], status="failed-host", caption=video_caption(r))
            continue
        posted = []
        services = ENABLED_SERVICES or ["facebook"]
        for service in services:
            try:
                res = buffer_client.post_to_service(service, video_caption(r), public_url)
                posted.append(service)
                try:
                    print("  post:", res)
                except UnicodeError:
                    print(f"  {service}: post success")
            except Exception as e:
                print(f"  {service} ERROR: {str(e)[:200]}")
        status = "done" if posted else "error"
        storage.record_video(r["reel_url"], r["reel_url"], enhanced, public_url, posted, status=status, caption=video_caption(r))


if __name__ == "__main__":
    run()
