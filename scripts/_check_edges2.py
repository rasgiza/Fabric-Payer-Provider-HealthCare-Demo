"""Re-test failing edges with corrected node types, and deeper diagnostics."""
import sys, json
sys.path.insert(0, ".")
from azure.identity import InteractiveBrowserCredential
from clients.graph_client import GraphModelClient

WS = "2966d7c8-dd6c-4b14-a4c9-82cce36d7fe4"
GID = "6fb20f2d-a35f-449c-a891-64cb2ec2628a"

cred = InteractiveBrowserCredential(login_hint="admin@MngEnvMCAP661056.onmicrosoft.com")
token = cred.get_token("https://analysis.windows.net/powerbi/api/.default").token
gc = GraphModelClient(token)

def run(label, gql):
    r = gc.execute_query(WS, GID, gql)
    if not r:
        print(f"  {label}: NO RESPONSE")
        return
    status = r.get("status", {})
    data = r.get("result", {}).get("data", [])
    if status.get("code") == "00000" and data:
        print(f"  {label}: OK — {len(data)} rows")
        for row in data[:2]:
            print(f"    {row}")
    elif status.get("code") == "00000":
        print(f"  {label}: OK but 0 rows")
    else:
        cause = status.get("cause", {}).get("description", "")[:200]
        print(f"  {label}: FAIL — {cause}")

# First: get the primaryKeyProperties from graphType
defn = gc.get_definition(WS, GID)
gt = defn.get("graphType.json", {})
print("=== Node Type Primary Keys ===")
for nt in gt.get("nodeTypes", []):
    alias = nt["alias"]
    pks = nt.get("primaryKeyProperties", "NOT SET")
    print(f"  {alias}: PKs={pks}")

# Check Prescription node has payer_key in fact_prescription table
print("\n=== Checking fact_prescription columns ===")
gd = defn.get("graphDefinition.json", {})
for nt in gd.get("nodeTables", []):
    if nt.get("nodeTypeAlias") == "Prescription_nodeType":
        cols = [m["sourceColumn"] for m in nt.get("propertyMappings", [])]
        print(f"  Prescription node cols: {cols}")
        print(f"  Has provider_key: {'provider_key' in cols}")
        print(f"  Has payer_key: {'payer_key' in cols}")

# Re-test corrected edges
print("\n=== Corrected Edge Tests ===")

# The 3 definitely-failing edges (correctly tested before)
run("prescribedBy (Prescription->Provider)",
    "MATCH (rx:Prescription)-[:prescribedBy]->(pv:Provider) RETURN rx.prescription_id, pv.display_name LIMIT 3")

run("PrescriptionHasPayer (Prescription->Payer)",
    "MATCH (rx:Prescription)-[:PrescriptionHasPayer]->(pay:Payer) RETURN rx.prescription_id, pay.payer_name LIMIT 3")

run("vitalsTakenFor (Vitals->Patient)",
    "MATCH (v:Vitals)-[:vitalsTakenFor]->(pt:Patient) RETURN v.vitals_key, pt.patient_id LIMIT 3")

# These were tested with wrong node types before - retest correctly
run("covers (Claim->Patient) [was tested as Payer->Patient]",
    "MATCH (c:Claim)-[:covers]->(pt:Patient) RETURN c.claim_id, pt.patient_id LIMIT 3")

run("occursIn (PatientDiagnosis->Encounter) [was tested as Encounter->Encounter]",
    "MATCH (pd:PatientDiagnosis)-[:occursIn]->(e:Encounter) RETURN pd.diagnosis_id, e.encounter_id LIMIT 3")

# Try prescribedBy without typed nodes
print("\n=== Untyped Node Tests ===")
run("prescribedBy untyped",
    "MATCH ()-[e:prescribedBy]->() RETURN e LIMIT 3")

# Try query that avoids the failing edge
print("\n=== Workaround: provider via Encounter (no prescribedBy needed) ===")
run("Provider prescribing via Encounter path",
    "MATCH (rx:Prescription)-[:originatesFrom]->(e:Encounter)-[:treatedBy]->(pv:Provider), "
    "(rx)-[:dispenses]->(m:Medication) "
    "RETURN pv.display_name, pv.specialty, m.medication_name LIMIT 5")

# Check if there's a data source for payer_key column
print("\n=== Data Sources ===")
ds = defn.get("dataSources.json", {})
for s in ds.get("dataSources", []):
    if "prescription" in s.get("name", "").lower():
        print(f"  {s['name']}: {s['properties']['path']}")
