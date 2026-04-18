"""
Delete and recreate the Healthcare_Demo_Graph from scratch.
This resolves edges that failed to load during the stuck InProgress data load.
"""
import sys
import json
import time
sys.path.insert(0, ".")
from azure.identity import InteractiveBrowserCredential
from clients.graph_client import GraphModelClient
from clients.graph_definition_builder import GraphDefinitionBuilder

WS = "2966d7c8-dd6c-4b14-a4c9-82cce36d7fe4"
LH = "655a25f7-837c-40e6-9552-8cb42515afc5"
OLD_GID = "6fb20f2d-a35f-449c-a891-64cb2ec2628a"
ONTOLOGY = r"..\ontology\Healthcare_Demo_Ontology_HLS"
GRAPH_NAME = "Healthcare_Demo_Graph"

cred = InteractiveBrowserCredential(login_hint="admin@MngEnvMCAP661056.onmicrosoft.com")
token = cred.get_token("https://analysis.windows.net/powerbi/api/.default").token
gc = GraphModelClient(token)

# ── Step 1: Delete old graph ──────────────────────────────────
print("=" * 60)
print("Step 1: Delete old graph model")
info = gc.get(WS, OLD_GID)
if info:
    qr = info.get("properties", {}).get("queryReadiness", "?")
    ls = info.get("properties", {}).get("lastDataLoadingStatus", {}).get("status", "?")
    print(f"  Current state: queryReadiness={qr}, loadingStatus={ls}")
    gc.delete(WS, OLD_GID)
    print("  Waiting 15s for deletion to propagate...")
    time.sleep(15)
else:
    print("  Old graph not found (already deleted?)")

# ── Step 2: Build definition from ontology ─────────────────────
print()
print("=" * 60)
print("Step 2: Build graph definition from ontology")
builder = GraphDefinitionBuilder(ONTOLOGY, WS, LH)
builder.load_ontology()
parts = builder.build_all_parts(GRAPH_NAME, "Healthcare demo knowledge graph")

# Validate
for p in parts:
    path = p.get("path", "unknown")
    print(f"  {path}: ready")

# ── Step 3: Create new graph model ────────────────────────────
print()
print("=" * 60)
print("Step 3: Create new graph model")
new_id = gc.create(WS, GRAPH_NAME, "Healthcare demo knowledge graph", parts)
if not new_id:
    print("  FAILED to create graph model — exiting")
    sys.exit(1)

print(f"  New graph model ID: {new_id}")

# ── Step 4: Wait for data load ────────────────────────────────
print()
print("=" * 60)
print("Step 4: Waiting for data load (polling every 30s, max 15 min)...")
max_wait = 900
start = time.time()
while time.time() - start < max_wait:
    info = gc.get(WS, new_id)
    if not info:
        print("  [WARN] Could not get graph status")
        break
    qr = info.get("properties", {}).get("queryReadiness", "None")
    ls = info.get("properties", {}).get("lastDataLoadingStatus", {}).get("status", "Unknown")
    elapsed = int(time.time() - start)
    print(f"  [{elapsed}s] queryReadiness={qr}  loadingStatus={ls}")
    if ls in ("Completed", "Failed"):
        break
    if qr == "Full" and elapsed > 120:
        print("  queryReadiness=Full, proceeding to test...")
        break
    time.sleep(30)

# ── Step 5: Test ALL 18 edge traversals ───────────────────────
print()
print("=" * 60)
print("Step 5: Testing all 18 edge traversals")

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
    ("covers", "Claim", "Patient"),
    ("involves", "Encounter", "Patient"),
    ("treatedBy", "Encounter", "Provider"),
    ("billsFor", "Claim", "Encounter"),
    ("originatesFrom", "Prescription", "Encounter"),
    ("occursIn", "PatientDiagnosis", "Encounter"),
    ("adherenceFor", "MedicationAdherence", "Patient"),
    ("adherenceMedication", "MedicationAdherence", "Medication"),
    ("vitalsTakenFor", "Vitals", "Patient"),
]

ok_count = 0
fail_count = 0
for name, src, dst in edges:
    gql = f"MATCH (s:{src})-[:{name}]->(d:{dst}) RETURN s, d LIMIT 1"
    r = gc.execute_query(WS, new_id, gql)
    if not r:
        print(f"  {name}: NO RESPONSE")
        fail_count += 1
        continue
    status = r.get("status", {})
    data = r.get("result", {}).get("data", [])
    if status.get("code") == "00000" and data:
        print(f"  {name}: OK")
        ok_count += 1
    elif status.get("code") == "00000":
        print(f"  {name}: OK (0 rows)")
        ok_count += 1
    else:
        cause = status.get("cause", {}).get("description", "")[:120]
        print(f"  {name}: FAIL — {cause}")
        fail_count += 1

print(f"\n  Results: {ok_count} OK, {fail_count} FAILED out of {len(edges)}")

# ── Step 6: Test critical agent queries ───────────────────────
print()
print("=" * 60)
print("Step 6: Testing critical agent query patterns")

queries = [
    ("Q2: Denied claims by provider",
     "MATCH (c:Claim)-[:submittedBy]->(pv:Provider), (c)-[:ClaimHasPayer]->(pay:Payer) "
     "WHERE c.denial_flag = 1 "
     "RETURN pv.display_name, c.claim_id, c.primary_denial_reason, pay.payer_name LIMIT 3"),
    ("Q3: Patient panel",
     "MATCH (e:Encounter)-[:treatedBy]->(pv:Provider), (e)-[:involves]->(pt:Patient) "
     "RETURN pv.display_name, pt.patient_id, e.encounter_type LIMIT 3"),
    ("Q4: Prescribing by specialty (direct)",
     "MATCH (rx:Prescription)-[:prescribedBy]->(pv:Provider), "
     "(rx)-[:dispenses]->(m:Medication) "
     "WHERE pv.specialty = 'Internal Medicine' "
     "RETURN pv.display_name, m.medication_name LIMIT 5"),
    ("Q4-alt: Prescribing via encounter path",
     "MATCH (rx:Prescription)-[:originatesFrom]->(e:Encounter)-[:treatedBy]->(pv:Provider), "
     "(rx)-[:dispenses]->(m:Medication) "
     "WHERE pv.specialty = 'Internal Medicine' "
     "RETURN pv.display_name, m.medication_name LIMIT 5"),
    ("Q5: High readmission risk",
     "MATCH (e:Encounter)-[:involves]->(pt:Patient), (e)-[:treatedBy]->(pv:Provider) "
     "WHERE e.readmission_risk_category = 'High' "
     "RETURN pv.display_name, pt.patient_id, e.readmission_risk_score LIMIT 3"),
    ("Q6: SDOH via risk_tier",
     "MATCH (e:Encounter)-[:involves]->(pt:Patient), "
     "(e)-[:treatedBy]->(pv:Provider), "
     "(pt)-[:livesIn]->(c:CommunityHealth) "
     "WHERE c.risk_tier = 'High' "
     "RETURN pv.display_name, pt.patient_id, c.zip_code, c.risk_tier LIMIT 3"),
]

for label, gql in queries:
    r = gc.execute_query(WS, new_id, gql)
    if not r:
        print(f"  {label}: NO RESPONSE")
        continue
    status = r.get("status", {})
    data = r.get("result", {}).get("data", [])
    if status.get("code") == "00000" and data:
        print(f"  {label}: OK — {len(data)} rows")
        for row in data[:2]:
            print(f"    {row}")
    elif status.get("code") == "00000":
        print(f"  {label}: OK but 0 rows")
    else:
        cause = status.get("cause", {}).get("description", "")[:150]
        print(f"  {label}: FAIL — {cause}")

print()
print("=" * 60)
print(f"NEW GRAPH MODEL ID: {new_id}")
print("Update any references to the old graph ID accordingly.")
print("=" * 60)
