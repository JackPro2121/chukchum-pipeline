import sys
sys.path.insert(0, "src")
import buffer_client as b

orgs = b._gql("query { account { organizations { id } } }")["account"]["organizations"]
for o in orgs:
    q = (
        'query { posts(first: 20, input: { organizationId: "'
        + o["id"]
        + '" }) { edges { node { id status dueAt sentAt channel { service name } } } } }'
    )
    r = b._gql(q)
    for e in r["posts"]["edges"]:
        n = e["node"]
        print(n["id"], n["status"], "due:", n.get("dueAt"), "sent:", n.get("sentAt"), n["channel"]["service"])
