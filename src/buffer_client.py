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


def create_video_post(channel_id: str, text: str, video_url: str, mode: str = "addToQueue") -> dict:
    q = f"""
    mutation {{
      createPost(input: {{
        text: {json.dumps(text)}
        channelId: "{channel_id}"
        schedulingType: automatic
        mode: {mode}
        assets: [{{ video: {{ url: "{video_url}" }} }}]
      }}) {{
        ... on PostActionSuccess {{ post {{ id text }} }}
        ... on MutationError {{ message }}
      }}
    }}
    """
    data = _gql(q)
    return data["createPost"]


def post_to_service(service: str, text: str, video_url: str) -> str:
    for ch in list_channels():
        if ch["service"].lower() == service.lower():
            res = create_video_post(ch["id"], text, video_url)
            return f"{ch['name']}: {res}"
    return f"No channel for {service}"
