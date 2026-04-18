"""Quick diagnostic: check graph model status + run test queries."""
import sys, json
sys.path.insert(0, ".")
from fabric_auth import get_fabric_token
from clients.graph_client import GraphModelClient

WS = "2966d7c8-dd6c-4b14-a4c9-82cce36d7fe4"

print("Authenticating...")
from azure.identity import InteractiveBrowserCredential
cred = InteractiveBrowserCredential(login_hint="admin@MngEnvMCAP661056.onmicrosoft.com")
token = cred.get_token("https://analysis.windows.net/powerbi/api/.default").token
gc = GraphModelClient(token)

print("Listing graph models...")
graphs = gc.list(WS)
for g in graphs:
    print(f"  {g['displayName']} ({g['id']})")

# Find the healthcare graph
hg = None
for g in graphs:
    dn = g.get("displayName", "")
    if "healthcare" in dn.lower() or "demo" in dn.lower() or "ontology" in dn.lower():
        hg = g
        break
if not hg and graphs:
    hg = graphs[0]
if not hg:
    print("No graph models found!")
    sys.exit(1)

gid = hg["id"]
print(f"\nChecking: {hg['displayName']} ({gid})")

# Get status
item = gc.get(WS, gid)
if item:
    props = item.get("properties", {})
    print(f"  queryReadiness: {props.get('queryReadiness', 'N/A')}")
    loading = props.get("lastDataLoadingStatus", {})
    print(f"  loadingStatus:  {loading.get('status', 'N/A')}")
    if loading.get("error"):
        print(f"  loadingError:   {loading['error']}")
else:
    print("  Could not get graph model details")

# Test GQL queries
print("\n=== GQL Diagnostics ===\n")

# 1. Count all nodes
print("1) Node counts:")
r = gc.execute_query(WS, gid, "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt")
if r:
    results = r.get("results", [])
    if results:
        for row in results[0].get("rows", []):
            print(f"   {row}")
    if not results or not results[0].get("rows"):
        print(f"   Empty results. Raw: {json.dumps(r)[:300]}")
else:
    print("   GQL not available or query failed")

# 2. Count all edges
print("\n2) Edge counts:")
r = gc.execute_query(WS, gid, "MATCH ()-[e]->() RETURN type(e) AS rel, count(e) AS cnt")
if r:
    results = r.get("results", [])
    if results:
        for row in results[0].get("rows", []):
            print(f"   {row}")
    if not results or not results[0].get("rows"):
        print(f"   Empty results. Raw: {json.dumps(r)[:300]}")

# 3. Get a few providers
print("\n3) Sample providers (any 5):")
r = gc.execute_query(WS, gid, "MATCH (p:Provider) RETURN p.display_name, p.specialty LIMIT 5")
if r:
    results = r.get("results", [])
    if results:
        for row in results[0].get("rows", []):
            print(f"   {row}")
    if not results or not results[0].get("rows"):
        print(f"   Empty. Raw: {json.dumps(r)[:300]}")
else:
    print("   Query failed")

# 4. Filter providers by specialty
print("\n4) Providers WHERE specialty='Internal Medicine':")
r = gc.execute_query(WS, gid,
    "MATCH (p:Provider) WHERE p.specialty = 'Internal Medicine' RETURN p.display_name, p.specialty LIMIT 5")
if r:
    results = r.get("results", [])
    if results:
        for row in results[0].get("rows", []):
            print(f"   {row}")
    if not results or not results[0].get("rows"):
        print(f"   Empty. Raw: {json.dumps(r)[:300]}")
else:
    print("   Query failed")

# 5. Simple traversal: Prescription -> Provider
print("\n5) Prescription-[prescribedBy]->Provider:")
r = gc.execute_query(WS, gid,
    "MATCH (rx:Prescription)-[:prescribedBy]->(pv:Provider) RETURN pv.display_name, pv.specialty, count(rx) AS rx_count LIMIT 5")
if r:
    results = r.get("results", [])
    if results:
        for row in results[0].get("rows", []):
            print(f"   {row}")
    if not results or not results[0].get("rows"):
        print(f"   Empty. Raw: {json.dumps(r)[:300]}")
else:
    print("   Query failed")

# 6. Multi-hop: Provider -> Prescription -> Medication (prescribing pattern)
print("\n6) Provider->Prescription->Medication (prescribing pattern):")
r = gc.execute_query(WS, gid,
    "MATCH (rx:Prescription)-[:prescribedBy]->(pv:Provider), (rx)-[:dispenses]->(m:Medication) WHERE pv.specialty = 'Internal Medicine' RETURN pv.display_name, m.medication_name LIMIT 10")
if r:
    results = r.get("results", [])
    if results:
        for row in results[0].get("rows", []):
            print(f"   {row}")
    if not results or not results[0].get("rows"):
        print(f"   Empty. Raw: {json.dumps(r)[:300]}")
else:
    print("   Query failed")

# 7. Check distinct specialties in the data
print("\n7) Distinct specialties in Provider:")
r = gc.execute_query(WS, gid,
    "MATCH (p:Provider) RETURN DISTINCT p.specialty AS spec LIMIT 20")
if r:
    results = r.get("results", [])
    if results:
        for row in results[0].get("rows", []):
            print(f"   {row}")
    if not results or not results[0].get("rows"):
        print(f"   Empty. Raw: {json.dumps(r)[:300]}")
else:
    print("   Query failed")

print("\n=== Done ===")
