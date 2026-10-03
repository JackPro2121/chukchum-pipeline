import sys
sys.path.insert(0, ".")
import buffer_client as b

orgs = b._gql("query { account { organizations { id } } }")["account"]["organizations"]
print("orgs:", orgs)
for o in orgs:
    q = (
        'query { posts(first: 10, input: { organizationId: "'
        + o["id"]
        + '" }) { edges { node { id status dueAt channel { service name } } } } }'
    )
    r = b._gql(q)
    for e in r["posts"]["edges"]:
        n = e["node"]
        print(n["id"], n["status"], n["dueAt"], n["channel"]["service"])
