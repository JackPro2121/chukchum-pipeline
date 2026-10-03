import time
import requests
from config import APIFY_TOKEN, APIFY_BASE

AUTH = {"Authorization": f"Bearer {APIFY_TOKEN}"}


def run_actor(actor_id: str, run_input: dict, timeout_sec: int = 600) -> list[dict]:
    run = requests.post(
        f"{APIFY_BASE}/acts/{actor_id}/runs",
        headers=AUTH,
        json=run_input,
        timeout=60,
    )
    run.raise_for_status()
    run_id = run.json()["data"]["id"]
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        time.sleep(5)
        r = requests.get(f"{APIFY_BASE}/actor-runs/{run_id}", headers=AUTH, timeout=60)
        r.raise_for_status()
        data = r.json()["data"]
        status = data["status"]
        if status == "SUCCEEDED":
            items = requests.get(
                f"{APIFY_BASE}/datasets/{data['defaultDatasetId']}/items",
                headers=AUTH,
                params={"format": "json", "clean": "true"},
                timeout=120,
            )
            items.raise_for_status()
            return items.json()
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise RuntimeError(f"Actor {actor_id} run {run_id} ended with status {status}")
    raise TimeoutError(f"Actor {actor_id} run {run_id} timed out")
