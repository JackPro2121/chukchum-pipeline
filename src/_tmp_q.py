import sys
sys.path.insert(0, ".")
import requests
from config import BUFFER_API_KEY, BUFFER_API

r = requests.post(
    BUFFER_API,
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {BUFFER_API_KEY}"},
    json={"query": "query GetOrganizations { account { organizations { id name } } }"},
    timeout=60,
)
print(r.json())
