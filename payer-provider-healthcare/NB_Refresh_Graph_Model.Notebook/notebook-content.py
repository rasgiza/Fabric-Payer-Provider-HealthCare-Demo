# Fabric notebook source

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# NB_Refresh_Graph_Model
# ============================================================================
# Lightweight notebook for day-2 operations: triggers an on-demand refresh
# of the Healthcare_Demo_Graph graph model after Gold Delta tables have been
# updated (e.g., by the Silver->Gold pipeline or incremental load).
#
# Usage:
#   1. Pipeline runs 02_Silver -> 03_Gold (Delta tables updated)
#   2. Pipeline calls this notebook as a follow-up activity
#   3. This notebook: refreshes graph data, waits, runs smoke test
#
# Can also be run manually from the Fabric UI for ad-hoc refreshes.
#
# Default lakehouse: lh_gold_curated
# ============================================================================

import requests, time, json
from notebookutils import mssparkutils

print("=" * 60)
print("  NB_Refresh_Graph_Model")
print("=" * 60)

# -- Config ---------------------------------------------------
GRAPH_MODEL_NAME = "Healthcare_Demo_Graph"
API = "https://api.fabric.microsoft.com/v1"

# -- Auth & Discovery -----------------------------------------
token = mssparkutils.credentials.getToken("pbi")
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}

# Discover workspace ID from notebook context
workspace_id = spark.conf.get("trident.workspace.id")
print(f"  Workspace: {workspace_id}")

GM_API = f"{API}/workspaces/{workspace_id}/graphModels"

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ==============================================================
# STEP 1: Find the graph model
# ==============================================================
print()
print("Step 1: Find graph model")
print("-" * 40)

token = mssparkutils.credentials.getToken("pbi")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

r = requests.get(GM_API, headers=headers)
r.raise_for_status()

gm_id = None
gm_display = None
for g in r.json().get("value", []):
    if g.get("displayName") == GRAPH_MODEL_NAME:
        gm_id = g["id"]
        gm_display = g["displayName"]
        break

if not gm_id:
    # Fallback: look for any graph with "Healthcare" or "Ontology" in the name
    for g in r.json().get("value", []):
        gn = g.get("displayName", "")
        if "Healthcare" in gn or "Ontology" in gn:
            gm_id = g["id"]
            gm_display = gn
            print(f"  Exact match not found, using: {gn}")
            break

if not gm_id:
    raise RuntimeError(
        f"Graph model '{GRAPH_MODEL_NAME}' not found in workspace. "
        f"Available: {[g['displayName'] for g in r.json().get('value', [])]}"
    )

print(f"  Found: {gm_display} ({gm_id})")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ==============================================================
# STEP 2: Trigger on-demand refresh
# ==============================================================
print()
print("Step 2: Trigger graph refresh")
print("-" * 40)

token = mssparkutils.credentials.getToken("pbi")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

refresh_url = f"{GM_API}/{gm_id}/jobs/refreshGraph/instances"
r = requests.post(refresh_url, headers=headers)

if r.status_code == 200:
    print("  [OK] Refresh completed synchronously")
    refresh_ok = True
elif r.status_code == 202:
    print("  Refresh started (async) -- polling for completion...")
    lro_url = r.headers.get("Location")
    retry_after = int(r.headers.get("Retry-After", 10))

    refresh_ok = False
    start = time.time()
    timeout = 600  # 10 minutes max

    while time.time() - start < timeout:
        time.sleep(retry_after)
        token = mssparkutils.credentials.getToken("pbi")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        if lro_url:
            poll = requests.get(lro_url, headers=headers)
            if poll.status_code == 200:
                body = poll.json()
                status = body.get("status", "")
                if status == "Succeeded":
                    refresh_ok = True
                    elapsed = int(time.time() - start)
                    print(f"  [OK] Refresh succeeded ({elapsed}s)")
                    break
                elif status in ("Failed", "Cancelled"):
                    err = body.get("error", {})
                    print(f"  [FAIL] Refresh {status}: {err.get('message', 'unknown')[:300]}")
                    break
                else:
                    if int(time.time() - start) % 30 < retry_after:
                        print(f"    status={status}...")
        else:
            # No Location header -- fall back to polling graph properties
            poll = requests.get(f"{GM_API}/{gm_id}", headers=headers)
            if poll.status_code == 200:
                props = poll.json().get("properties", {})
                readiness = props.get("queryReadiness", "")
                load_status = (props.get("lastDataLoadingStatus") or {}).get("status", "")
                if readiness == "Full" or load_status == "Completed":
                    refresh_ok = True
                    elapsed = int(time.time() - start)
                    print(f"  [OK] Data loaded ({elapsed}s)")
                    break
                if load_status == "Failed":
                    print(f"  [FAIL] Data load failed")
                    break

    if not refresh_ok and time.time() - start >= timeout:
        print(f"  [FAIL] Refresh timed out after {timeout}s")
else:
    print(f"  [FAIL] Refresh trigger: HTTP {r.status_code}")
    print(f"    {r.text[:300]}")
    refresh_ok = False

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ==============================================================
# STEP 3: Smoke test via executeQuery (beta)
# ==============================================================
print()
print("Step 3: Smoke test (GQL query)")
print("-" * 40)

smoke_ok = False

if refresh_ok:
    token = mssparkutils.credentials.getToken("pbi")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    query_url = f"{GM_API}/{gm_id}/executeQuery?beta=True"

    # Count patients as a quick health check
    gql = "MATCH (p:Patient) RETURN COUNT(p) AS patient_count;"
    r = requests.post(query_url, headers=headers, json={"query": gql})

    if r.status_code == 200:
        result = r.json()
        status_code = result.get("status", {}).get("code", "")
        if status_code == "00000":
            data = result.get("result", {}).get("data", [])
            if data:
                count = data[0].get("patient_count", "?")
                print(f"  Patient count: {count}")
                smoke_ok = True
            else:
                print(f"  [WARN] Query returned no data rows")
        else:
            desc = result.get("status", {}).get("description", "")
            print(f"  [WARN] Query status: {status_code} -- {desc}")
    elif r.status_code == 429:
        print(f"  [WARN] Rate limited -- skipping smoke test (graph refresh was OK)")
        smoke_ok = True  # refresh itself succeeded
    else:
        print(f"  [WARN] executeQuery: HTTP {r.status_code}")
        print(f"    {r.text[:200]}")
        # Don't fail the whole notebook -- the refresh itself may have worked
        print(f"  Note: executeQuery is beta; refresh may still be OK")
else:
    print("  Skipping -- refresh did not succeed")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ==============================================================
# Summary
# ==============================================================
print()
print("=" * 60)
refresh_status = "[OK]" if refresh_ok else "[FAIL]"
smoke_status = "[OK]" if smoke_ok else "[WARN]" if refresh_ok else "[SKIP]"
print(f"  GRAPH:      {GRAPH_MODEL_NAME:<38} {refresh_status}")
print(f"  SMOKE TEST: {'Patient count query':<38} {smoke_status}")
print("=" * 60)

if not refresh_ok:
    raise RuntimeError(
        f"Graph refresh failed for {GRAPH_MODEL_NAME}. "
        "Check the Fabric UI for graph model status."
    )
