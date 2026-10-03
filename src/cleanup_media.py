import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import buffer_client
import media_repo
import storage


def buffer_queued_texts() -> set[str]:
    texts: set[str] = set()
    for org in buffer_client._gql("query { account { organizations { id } } }")["account"]["organizations"]:
        data = buffer_client._gql(
            "query { posts(first: 50, input: { organizationId: \""
            + org["id"]
            + "\", filter: { status: [\"draft\", \"scheduled\", \"sending\", \"needs_approval\", \"error\"] } }) { edges { node { text } } } }"
        )
        for edge in data.get("posts", {}).get("edges", []):
            texts.add((edge["node"].get("text") or "").strip())
    return texts


def main():
    queued = buffer_queued_texts()
    cutoff = datetime.now(timezone.utc) - timedelta(days=10)
    removed = kept = 0
    for row in storage.all_videos():
        try:
            created = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        except Exception:
            continue
        if created > cutoff:
            continue
        if row.get("caption") and row["caption"].strip() in queued:
            print("KEEP (still queued):", row["public_url"])
            kept += 1
            continue
        name = Path(row["public_url"]).name if row.get("public_url") else None
        if not name:
            continue
        media_repo.remove(name)
        print("REMOVED:", name)
        removed += 1
    print(f"removed={removed} kept={kept}")


if __name__ == "__main__":
    main()
