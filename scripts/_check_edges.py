"""Check node type keys and all edge types from the graph definition."""
import sys, json
sys.path.insert(0, ".")
from azure.identity import InteractiveBrowserCredential
from clients.graph_client import GraphModelClient

WS = "2966d7c8-dd6c-4b14-a4c9-82cce36d7fe4"
GID = "6fb20f2d-a35f-449c-a891-64cb2ec2628a"

cred = InteractiveBrowserCredential(login_hint="admin@MngEnvMCAP661056.onmicrosoft.com")
token = cred.get_token("https://analysis.windows.net/powerbi/api/.default").token
gc = GraphModelClient(token)
defn = gc.get_definition(WS, GID)
gt = defn.get("graphType.json", {})

print("=== All nodeTypes (with keys) ===")
for nt in gt.get("nodeTypes", []):
    alias = nt["alias"]
    labels = nt.get("labels")
    key = nt.get("key", nt.get("keyPropertyNames", "NOT SET"))
    props = [p["name"] for p in nt.get("properties", [])]
    print(f"{alias}: labels={labels}, key={key}")
    print(f"    properties: {props}")
    print()

print("=== All edgeTypes ===")
for et in gt.get("edgeTypes", []):
    alias = et["alias"]
    src = et.get("sourceNodeType", {}).get("alias")
    dst = et.get("destinationNodeType", {}).get("alias")
    labels = et.get("labels")
    key = et.get("key", et.get("keyPropertyNames", "NOT SET"))
    props = et.get("properties", [])
    print(f"{alias}: {src} -> {dst}, labels={labels}, key={key}, props={props}")

# Now test each edge
print("\n=== Testing ALL 18 edge traversals ===")
edges = [
    ("livesIn", "Patient", "CommunityHealth"),
    ("references", "PatientDiagnosis", "Diagnosis"),
    ("affects", "PatientDiagnosis", "Patient"),
    ("dispenses", "Prescription", "Medication"),
    ("PrescriptionHasPayer", "Prescription", "Payer"),
    ("prescribedBy", "Prescription", "Provider"),
    ("serves", "Prescription", "Patient"),
    ("ClaimHasPayer", "Claim", "Payer"),
    ("submittedBy", "Claim", "Provider"),
    ("covers", "Payer", "Patient"),
    ("involves", "Encounter", "Patient"),
    ("treatedBy", "Encounter", "Provider"),
    ("billsFor", "Claim", "Encounter"),
    ("originatesFrom", "Prescription", "Encounter"),
    ("occursIn", "Encounter", "Encounter"),
    ("adherenceFor", "MedicationAdherence", "Patient"),
    ("adherenceMedication", "MedicationAdherence", "Medication"),
    ("vitalsTakenFor", "Vitals", "Patient"),
]

for name, src, dst in edges:
    gql = f"MATCH (s:{src})-[:{name}]->(d:{dst}) RETURN s, d LIMIT 1"
    r = gc.execute_query(WS, GID, gql)
    if not r:
        print(f"  {name}: NO RESPONSE")
        continue
    status = r.get("status", {})
    data = r.get("result", {}).get("data", [])
    if status.get("code") == "00000" and data:
        print(f"  {name}: OK ({src} -> {dst})")
    elif status.get("code") == "00000":
        print(f"  {name}: OK but 0 rows ({src} -> {dst})")
    else:
        cause = status.get("cause", {}).get("description", "")[:120]
        print(f"  {name}: FAIL — {cause}")
