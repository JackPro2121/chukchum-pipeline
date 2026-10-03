import sys
sys.path.insert(0, ".")
import buffer_client as b

def fields(name):
    r = b._gql(f'query {{ __type(name:"{name}") {{ fields {{ name }} }} }}')["__type"]
    return [f["name"] for f in r["fields"]] if r and r.get("fields") else r

print("Post:", fields("Post"))
print("Assets:", fields("Assets"))
