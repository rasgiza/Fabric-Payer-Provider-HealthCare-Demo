"""Diagnose blank Power BI report — checks SM binding, data, and report definition."""
import requests, json, base64
from azure.identity import InteractiveBrowserCredential

WORKSPACE_ID = "d6ed5901-0f1d-4a5c-a263-e5f857169a79"
SM_NAME = "HealthcareDemoHLS"
REPORT_NAME = "HealthcareAnalyticsDashboard"

cred = InteractiveBrowserCredential(login_hint="admin@MngEnvMCAP661056.onmicrosoft.com")
token = cred.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

FABRIC = f"https://api.fabric.microsoft.com/v1/workspaces/{WORKSPACE_ID}"
PBI = f"https://api.powerbi.com/v1.0/myorg/groups/{WORKSPACE_ID}"

print("=" * 60)
print("  REPORT DIAGNOSTIC")
print("=" * 60)

# 1. Find SM
resp = requests.get(f"{FABRIC}/items?type=SemanticModel", headers=headers)
resp.raise_for_status()
sm_id = None
for item in resp.json().get("value", []):
    if item["displayName"] == SM_NAME:
        sm_id = item["id"]
        break
print(f"\n1. Semantic Model: {SM_NAME}")
print(f"   ID: {sm_id}")

# 2. Find Report
resp = requests.get(f"{FABRIC}/items?type=Report", headers=headers)
resp.raise_for_status()
rpt_id = None
for item in resp.json().get("value", []):
    if item["displayName"] == REPORT_NAME:
        rpt_id = item["id"]
        break
print(f"\n2. Report: {REPORT_NAME}")
print(f"   ID: {rpt_id}")

# 3. Check report's dataset binding via PBI API
if rpt_id:
    resp = requests.get(f"{PBI}/reports/{rpt_id}", headers=headers)
    if resp.status_code == 200:
        rpt_info = resp.json()
        bound_ds = rpt_info.get("datasetId", "NONE")
        print(f"\n3. Report's bound datasetId: {bound_ds}")
        if bound_ds == sm_id:
            print("   MATCH — report is correctly bound to the SM")
        elif bound_ds == "NONE" or not bound_ds:
            print("   *** NO DATASET BOUND — this is why the report is blank! ***")
        else:
            print(f"   *** MISMATCH — expected {sm_id} ***")
    else:
        print(f"\n3. Could not get report info: HTTP {resp.status_code}")

# 4. Check SM has data via dataset info
if sm_id:
    resp = requests.get(f"{PBI}/datasets/{sm_id}", headers=headers)
    if resp.status_code == 200:
        ds = resp.json()
        print(f"\n4. Dataset info:")
        print(f"   isRefreshable: {ds.get('isRefreshable')}")
        print(f"   isEffectiveIdentityRequired: {ds.get('isEffectiveIdentityRequired')}")
        print(f"   isEffectiveIdentityRolesRequired: {ds.get('isEffectiveIdentityRolesRequired')}")
        print(f"   configuredBy: {ds.get('configuredBy')}")

    # 5. Check refresh history
    resp = requests.get(f"{PBI}/datasets/{sm_id}/refreshes?$top=3", headers=headers)
    if resp.status_code == 200:
        refreshes = resp.json().get("value", [])
        print(f"\n5. Recent refreshes ({len(refreshes)}):")
        for r in refreshes:
            print(f"   {r.get('startTime', '?')} — {r.get('status', '?')} ({r.get('refreshType', '?')})")
            if r.get("serviceExceptionJson"):
                try:
                    err = json.loads(r["serviceExceptionJson"])
                    print(f"   Error: {err.get('errorCode', '')}: {err.get('errorDescription', '')[:200]}")
                except:
                    print(f"   Error: {r['serviceExceptionJson'][:200]}")

    # 6. Try a DAX query to check if tables have data
    print(f"\n6. DAX query test (row counts):")
    dax_query = """
    EVALUATE
    ROW(
        "dim_patient_rows", COUNTROWS(dim_patient),
        "fact_claim_rows", COUNTROWS(fact_claim),
        "fact_encounter_rows", COUNTROWS(fact_encounter),
        "dim_payer_rows", COUNTROWS(dim_payer),
        "dim_provider_rows", COUNTROWS(dim_provider)
    )
    """
    resp = requests.post(
        f"{PBI}/datasets/{sm_id}/executeQueries",
        headers=headers,
        json={"queries": [{"query": dax_query}], "serializerSettings": {"includeNulls": True}}
    )
    if resp.status_code == 200:
        result = resp.json()
        tables = result.get("results", [{}])[0].get("tables", [{}])
        if tables:
            rows = tables[0].get("rows", [])
            if rows:
                for k, v in rows[0].items():
                    clean_key = k.replace("[", "").replace("]", "")
                    print(f"   {clean_key}: {v}")
            else:
                print("   No rows returned — SM might be empty!")
        else:
            print("   No tables in response")
    else:
        print(f"   DAX query failed: HTTP {resp.status_code}")
        print(f"   {resp.text[:300]}")

# 7. Get report definition to check what was actually deployed
if rpt_id:
    print(f"\n7. Report definition check:")
    resp = requests.post(f"{FABRIC}/reports/{rpt_id}/getDefinition", headers=headers)
    if resp.status_code == 200:
        defn = resp.json()
        parts = defn.get("definition", {}).get("parts", [])
        print(f"   Parts in deployed report: {len(parts)}")
        page_count = 0
        visual_count = 0
        has_pbir = False
        pbir_content = None
        for p in parts:
            path = p.get("path", "")
            if path == "definition.pbir":
                has_pbir = True
                raw = base64.b64decode(p["payload"]).decode("utf-8")
                pbir_content = raw
            if "/page.json" in path:
                page_count += 1
            if "/visual.json" in path:
                visual_count += 1
        print(f"   definition.pbir present: {has_pbir}")
        print(f"   Pages: {page_count}")
        print(f"   Visuals: {visual_count}")
        if pbir_content:
            print(f"\n   definition.pbir content:")
            print(f"   {pbir_content}")
    elif resp.status_code == 202:
        # LRO
        loc = resp.headers.get("Location", "")
        import time
        for i in range(20):
            time.sleep(3)
            r2 = requests.get(loc, headers=headers)
            if r2.status_code == 200:
                body = r2.json()
                if body.get("status") == "Succeeded":
                    res_loc = body.get("resourceLocation", "")
                    if res_loc:
                        r3 = requests.get(res_loc, headers=headers)
                        if r3.status_code == 200:
                            defn = r3.json()
                            parts = defn.get("definition", {}).get("parts", [])
                            print(f"   Parts in deployed report: {len(parts)}")
                            page_count = sum(1 for p in parts if "/page.json" in p.get("path", ""))
                            visual_count = sum(1 for p in parts if "/visual.json" in p.get("path", ""))
                            has_pbir = any(p.get("path") == "definition.pbir" for p in parts)
                            print(f"   definition.pbir present: {has_pbir}")
                            print(f"   Pages: {page_count}")
                            print(f"   Visuals: {visual_count}")
                            for p in parts:
                                if p.get("path") == "definition.pbir":
                                    raw = base64.b64decode(p["payload"]).decode("utf-8")
                                    print(f"\n   definition.pbir content:")
                                    print(f"   {raw}")
                    break
                elif body.get("status") in ("Failed", "Cancelled"):
                    print(f"   getDefinition failed: {body}")
                    break
    else:
        print(f"   Could not get definition: HTTP {resp.status_code}: {resp.text[:200]}")

print("\n" + "=" * 60)
