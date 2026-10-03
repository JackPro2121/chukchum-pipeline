"""Daily entrypoint: queue gate first, then fetch (Apify) only when there is room.

Order matters: Apify runs cost money, so the Buffer queue is checked before any
Apify call is made. If the target channel already has pending posts, the run
exits without spending credits.
"""

import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(SRC))

import buffer_client
from config import ENABLED_SERVICES, MAX_QUEUE_PER_CHANNEL, FETCH_ONLY_IF_QUEUE_EMPTY


def queue_snapshot() -> dict:
    return {s: buffer_client.scheduled_count(s) for s in (ENABLED_SERVICES or ["facebook"])}


def run_step(script: str) -> int:
    print(f"\n=== {script} ===")
    proc = subprocess.run([sys.executable, str(SRC / script)], cwd=SRC.parent)
    return proc.returncode


def main():
    services = ENABLED_SERVICES or ["facebook"]
    snapshot = queue_snapshot()
    print(f"queue check (no Apify credits used): {snapshot}")

    full = [s for s in services if snapshot.get(s, 0) >= MAX_QUEUE_PER_CHANNEL]
    if full:
        print(f"queue guard: {full} at/over {MAX_QUEUE_PER_CHANNEL} scheduled, run skipped")
        return 0

    if FETCH_ONLY_IF_QUEUE_EMPTY:
        busy = [s for s in services if snapshot.get(s, 0) > 0]
        if busy:
            print(f"queue gate: {busy} still has pending posts, skipping fetch (saves Apify credits)")
            return 0

    if run_step("fetch_targets.py") != 0:
        print("fetch failed, aborting before publishing")
        return 1
    return run_step("pipeline_v2.py")


if __name__ == "__main__":
    sys.exit(main())