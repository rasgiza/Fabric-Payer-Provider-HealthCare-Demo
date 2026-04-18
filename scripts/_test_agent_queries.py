"""Test all 6 failing agent query patterns against the live graph."""
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
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print(f"GQL:  {gql[:100]}...")
    r = gc.execute_query(WS, GID, gql)
    if not r:
        print("  RESULT: Query failed (no response)")
        return
    status = r.get("status", {})
    result = r.get("result", {})
    data = result.get("data", [])
    if status.get("code") == "00000" and data:
        print(f"  RESULT: SUCCESS — {len(data)} rows")
        for row in data[:5]:
            print(f"    {row}")
    elif status.get("code") == "00000":
        print(f"  RESULT: SUCCESS but 0 rows")
    else:
        cause = status.get("cause", {}).get("description", "")
        print(f"  RESULT: ERROR {status.get('code')} — {status.get('description', '')}")
        if cause:
            print(f"    Cause: {cause[:200]}")

# Q1: Full provider profile
run("Q1: Full provider profile",
    "MATCH (e:Encounter)-[:treatedBy]->(pv:Provider) "
    "RETURN pv.display_name, pv.specialty, count(e) AS encounters LIMIT 5")

# Q1b: Provider -> Claims
run("Q1b: Provider claims",
    "MATCH (c:Claim)-[:submittedBy]->(pv:Provider) "
    "RETURN pv.display_name, count(c) AS claims LIMIT 5")

# Q1c: Provider -> Prescriptions
run("Q1c: Provider prescriptions",
    "MATCH (rx:Prescription)-[:prescribedBy]->(pv:Provider) "
    "RETURN pv.display_name, count(rx) AS prescriptions LIMIT 5")

# Q2: Denied claims by provider
run("Q2: Denied claims by provider",
    "MATCH (c:Claim)-[:submittedBy]->(pv:Provider), (c)-[:ClaimHasPayer]->(pay:Payer) "
    "WHERE c.denial_flag = 1 "
    "RETURN pv.display_name, c.claim_id, c.primary_denial_reason, pay.payer_name LIMIT 5")

# Q3: Provider patient panel (this one WORKS already)
run("Q3: Provider patient panel",
    "MATCH (e:Encounter)-[:treatedBy]->(pv:Provider), (e)-[:involves]->(pt:Patient) "
    "RETURN pv.display_name, pt.patient_id, e.encounter_type LIMIT 5")

# Q4: Prescribing patterns by specialty
run("Q4: Prescribing by specialty (Internal Medicine)",
    "MATCH (rx:Prescription)-[:prescribedBy]->(pv:Provider), "
    "(rx)-[:dispenses]->(m:Medication) "
    "WHERE pv.specialty = 'Internal Medicine' "
    "RETURN pv.display_name, m.medication_name, m.drug_class LIMIT 10")

# Q4b: Try other specialties
run("Q4b: Prescribing by specialty (Cardiology)",
    "MATCH (rx:Prescription)-[:prescribedBy]->(pv:Provider), "
    "(rx)-[:dispenses]->(m:Medication) "
    "WHERE pv.specialty = 'Cardiology' "
    "RETURN pv.display_name, m.medication_name, m.drug_class LIMIT 10")

# Q5: High readmission risk patients -> providers
run("Q5: High readmission risk patients -> providers",
    "MATCH (e:Encounter)-[:involves]->(pt:Patient), (e)-[:treatedBy]->(pv:Provider) "
    "WHERE e.readmission_risk_category = 'High' "
    "RETURN pv.display_name, pt.patient_id, e.readmission_risk_score LIMIT 5")

# Q6: SDOH — providers serving vulnerable communities
run("Q6: Providers in vulnerable communities",
    "MATCH (e:Encounter)-[:involves]->(pt:Patient), "
    "(e)-[:treatedBy]->(pv:Provider), "
    "(pt)-[:livesIn]->(c:CommunityHealth) "
    "WHERE c.social_vulnerability_index > 0.3 "
    "RETURN pv.display_name, pt.patient_id, c.zip_code, c.risk_tier, c.social_vulnerability_index LIMIT 5")

# Bonus: Available specialties
run("Available specialties",
    "MATCH (p:Provider) RETURN DISTINCT p.specialty AS spec LIMIT 20")

print("\n" + "="*60)
print("ALL TESTS COMPLETE")
