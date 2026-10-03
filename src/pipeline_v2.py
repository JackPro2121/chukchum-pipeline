import csv
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config import ENABLED_SERVICES, TARGETS_CSV, MAX_QUEUE_PER_CHANNEL, MAX_POSTS_PER_RUN
import storage, enhancer, buffer_client, media_repo


def video_caption(row: dict) -> str:
    return row["fb_caption"]


def run():
    services = ENABLED_SERVICES or ["facebook"]
    for service in services:
        queued = buffer_client.scheduled_count(service)
        print(f"{service}: {queued} scheduled in queue")
        if queued >= MAX_QUEUE_PER_CHANNEL:
            print(f"  queue guard: {queued}/{MAX_QUEUE_PER_CHANNEL}, skipping {service} this run")

    with open(TARGETS_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"rows: {len(rows)}")
    posted_this_run = 0
    for r in rows:
        if posted_this_run >= MAX_POSTS_PER_RUN:
            print(f">>> {r['username']}: per-run cap reached ({MAX_POSTS_PER_RUN}), deferred")
            continue
        blocked = [s for s in services if buffer_client.scheduled_count(s) >= MAX_QUEUE_PER_CHANNEL]
        if blocked:
            print(f">>> {r['username']}: skipped, queue full on {blocked}")
            continue
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
        if posted:
            posted_this_run += 1


if __name__ == "__main__":
    run()
