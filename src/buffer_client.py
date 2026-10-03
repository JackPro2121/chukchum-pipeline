import json
import requests
from config import BUFFER_API_KEY, BUFFER_API

HEADERS = {"Content-Type": "application/json", "Authorization": f"Bearer {BUFFER_API_KEY}"}


def _gql(query: str) -> dict:
    r = requests.post(BUFFER_API, headers=HEADERS, json={"query": query}, timeout=60)
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(f"Buffer API error: {data['errors']}")
    return data["data"]


def list_channels() -> list[dict]:
    orgs = _gql("query { account { organizations { id name } } }")["account"]["organizations"]
    channels = []
    for org in orgs:
        data = _gql(
            f"query {{ channels(input: {{organizationId: \"{org['id']}\"}}) {{ id name service }} }}"
        )
        channels.extend(data.get("channels", []))
    return channels


def create_video_post(channel_id: str, text: str, video_url: str, service: str, mode: str = "addToQueue") -> dict:
    service_l = service.lower()
    if service_l == "facebook":
        metadata = 'metadata: {facebook: {type: reel}}'
    elif service_l == "instagram":
        metadata = 'metadata: {instagram: {type: reel}}'
    elif service_l == "tiktok":
        metadata = 'metadata: {tiktok: {type: "video"}}'
    elif service_l == "youtube":
        metadata = 'metadata: {youtube: {type: "shorts"}}'
    else:
        metadata = ''
    q = f"""
    mutation {{
      createPost(input: {{
        text: {json.dumps(text)}
        channelId: "{channel_id}"
        schedulingType: automatic
        mode: {mode}
        assets: [{{ video: {{ url: "{video_url}" }} }}]
        {metadata}
      }}) {{
        ... on PostActionSuccess {{ post {{ id text }} }}
        ... on MutationError {{ message }}
      }}
    }}
    """
    data = _gql(q)
    res = data["createPost"]
    if "message" in res:
        raise RuntimeError(res["message"])
    return res


def scheduled_count(service: str | None = None) -> int:
    total = 0
    for org in _gql("query { account { organizations { id } } }")["account"]["organizations"]:
        data = _gql(
            'query { posts(first: 50, input: { organizationId: "'
            + org["id"]
            + '", filter: { status: [scheduled, sending] } }) { edges { node { id status channel { service } } } } }'
        )
        for edge in (data.get("posts") or {}).get("edges", []):
            node = edge["node"]
            if service and (node.get("channel", {}).get("service") or "").lower() != service.lower():
                continue
            total += 1
    return total


def post_to_service(service: str, text: str, video_url: str) -> str:
    for ch in list_channels():
        if ch["service"].lower() == service.lower():
            res = create_video_post(ch["id"], text, video_url, ch["service"])
            return f"{ch['name']}: {res}"
    return f"No channel for {service}"
