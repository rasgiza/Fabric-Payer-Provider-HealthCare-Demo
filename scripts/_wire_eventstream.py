"""
Wire Healthcare_RTI_Eventstream — Full Topology via Fabric REST API.

Builds a production-style Eventstream topology:

    Custom Endpoint (source)
        │
        ├──► Eventhouse / KQL DB    (real-time dashboards, scoring, Operations Agent)
        ├──► Lakehouse (lh_bronze_raw)  (raw archival, medallion compliance)
        └──► Activator (Reflex)     (fraud/care-gap/high-cost alerts — if item exists)

The API does 95% of the work. The only manual step is copying the
Custom Endpoint connection string from the Fabric portal (the API
creates the endpoint but does not expose its connection string —
CustomEndpointSourceProperties is an empty object in the schema).

Usage (standalone):
    python _wire_eventstream.py

Also embedded in Healthcare_Launcher.ipynb Cell 12 for automated deployment.
"""
import subprocess, json, requests, base64, time, sys

# ── Helpers ───────────────────────────────────────────────────────
API = "https://api.fabric.microsoft.com/v1"

def get_token():
    """Get Fabric API token via Azure CLI."""
    r = subprocess.run(
        ["cmd", "/c", "az", "account", "get-access-token",
         "--resource", "https://api.fabric.microsoft.com"],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"ERROR: az login failed: {r.stderr}")
        sys.exit(1)
    return json.loads(r.stdout)["accessToken"]

def _headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def _wait_lro(op_id, token, label="operation", max_polls=60, interval=3):
    """Poll a Fabric LRO until Succeeded/Failed."""
    H = _headers(token)
    for i in range(max_polls):
        time.sleep(interval)
        r = requests.get(f"{API}/operations/{op_id}", headers=H)
        body = r.json()
        status = body.get("status", "Unknown")
        pct = body.get("percentComplete", "?")
        print(f"    Poll {i+1}: {status} ({pct}%)")
        if status == "Succeeded":
            return True, body
        elif status in ("Failed", "Cancelled"):
            err = body.get("error", {}).get("message", str(body)[:300])
            print(f"    {label} failed: {err}")
            return False, body
    print(f"    {label} timed out after {max_polls} polls")
    return False, None


# ── Step 1: Discover workspace + items ────────────────────────────
def discover(token):
    """Discover workspace and healthcare RTI items.

    Scans all workspaces containing 'healthcare'/'health' in the name
    and picks the first one that has a Healthcare_RTI_Eventhouse item.
    """
    H = _headers(token)
    r = requests.get(f"{API}/workspaces", headers=H)
    workspaces = r.json().get("value", [])

    # Collect candidate workspaces (healthcare-related)
    candidates = [ws for ws in workspaces
                  if any(k in ws.get("displayName", "").lower()
                         for k in ("healthcare", "health"))]
    if not candidates:
        candidates = workspaces[:1]  # fallback to first

    # Pick the workspace that has the required RTI items
    ws_id = None
    items = []
    for ws in candidates:
        _r = requests.get(f"{API}/workspaces/{ws['id']}/items", headers=H)
        _items = _r.json().get("value", [])
        has_eventhouse = any(i["type"] == "Eventhouse" and "Healthcare" in i["displayName"]
                            for i in _items)
        has_es = any(i["type"] == "Eventstream" and "Healthcare" in i["displayName"]
                     for i in _items)
        if has_eventhouse and has_es:
            ws_id = ws["id"]
            items = _items
            print(f"  Workspace: {ws['displayName']} ({ws_id[:8]}...)")
            break
    if not ws_id:
        # Fallback: first candidate
        ws_id = candidates[0]["id"]
        _r = requests.get(f"{API}/workspaces/{ws_id}/items", headers=H)
        items = _r.json().get("value", [])
        print(f"  Workspace (fallback): {candidates[0]['displayName']} ({ws_id[:8]}...)")

    if not ws_id:
        print("ERROR: No workspace found"); sys.exit(1)

    result = {
        "ws_id": ws_id, "eventhouse_id": None, "kqldb_id": None,
        "kqldb_name": None, "eventstream_id": None,
        "lakehouse_bronze_id": None, "activator_id": None
    }
    for i in items:
        t, n = i["type"], i["displayName"]
        if t == "Eventhouse" and "Healthcare" in n:
            result["eventhouse_id"] = i["id"]
            print(f"  Eventhouse:   {n} ({i['id'][:8]}...)")
        elif t == "KQLDatabase" and "Healthcare" in n:
            result["kqldb_id"] = i["id"]
            result["kqldb_name"] = n
            print(f"  KQL Database: {n} ({i['id'][:8]}...)")
        elif t == "Eventstream" and "Healthcare" in n:
            result["eventstream_id"] = i["id"]
            print(f"  Eventstream:  {n} ({i['id'][:8]}...)")
        elif t == "Lakehouse" and n == "lh_bronze_raw":
            result["lakehouse_bronze_id"] = i["id"]
            print(f"  Lakehouse:    {n} ({i['id'][:8]}...)")
        elif t == "Reflex":
            result["activator_id"] = i["id"]
            print(f"  Activator:    {n} ({i['id'][:8]}...)")
    return result


# ── Step 2: Build Eventstream topology ────────────────────────────
def build_topology(ws_id, kqldb_id, kqldb_name, lakehouse_id=None, activator_id=None):
    """Build the eventstream.json with all destinations."""

    # Source: Custom Endpoint (EventHub-compatible ingress)
    sources = [{
        "name": "HealthcareCustomEndpoint",
        "type": "CustomEndpoint",
        "properties": {
            "inputSerialization": {"type": "Json", "properties": {"encoding": "UTF8"}}
        }
    }]

    # Default stream: source → fan-out
    streams = [{
        "name": "HealthcareRTI-stream",
        "type": "DefaultStream",
        "properties": {},
        "inputNodes": [{"name": "HealthcareCustomEndpoint"}]
    }]

    # Destination 1: Eventhouse / KQL DB (real-time)
    destinations = [{
        "name": "HealthcareEventhouse",
        "type": "Eventhouse",
        "properties": {
            "dataIngestionMode": "ProcessedIngestion",
            "workspaceId": ws_id,
            "itemId": kqldb_id,
            "databaseName": kqldb_name,
            "tableName": "rti_claims_events",
            "inputSerialization": {"type": "Json", "properties": {"encoding": "UTF8"}}
        },
        "inputNodes": [{"name": "HealthcareRTI-stream"}]
    }]

    # Destination 2: Lakehouse (raw archival → medallion)
    if lakehouse_id:
        destinations.append({
            "name": "BronzeLakehouse",
            "type": "Lakehouse",
            "properties": {
                "workspaceId": ws_id,
                "itemId": lakehouse_id,
                "schema": "",
                "deltaTable": "rti_raw_events",
                "minimumRows": 1000,
                "maximumDurationInSeconds": 120,
                "inputSerialization": {"type": "Json", "properties": {"encoding": "UTF8"}}
            },
            "inputNodes": [{"name": "HealthcareRTI-stream"}]
        })

    # Destination 3: Activator / Reflex (alerts)
    if activator_id:
        destinations.append({
            "name": "HealthcareActivator",
            "type": "Activator",
            "properties": {
                "workspaceId": ws_id,
                "itemId": activator_id,
                "inputSerialization": {"type": "Json", "properties": {"encoding": "UTF8"}}
            },
            "inputNodes": [{"name": "HealthcareRTI-stream"}]
        })

    return {
        "sources": sources,
        "destinations": destinations,
        "streams": streams,
        "operators": [],
        "compatibilityLevel": "1.1"
    }


# ── Step 3: Push definition ──────────────────────────────────────
def push_definition(ws_id, es_id, es_def, token):
    """Push the Eventstream definition via updateDefinition API."""
    H = _headers(token)

    es_json_b64 = base64.b64encode(json.dumps(es_def, indent=2).encode()).decode()
    props_b64 = base64.b64encode(json.dumps({
        "retentionTimeInDays": 1, "eventThroughputLevel": "Low"
    }).encode()).decode()
    platform_b64 = base64.b64encode(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Eventstream", "displayName": "Healthcare_RTI_Eventstream"},
        "config": {"version": "2.0", "logicalId": es_id}
    }).encode()).decode()

    body = {"definition": {"parts": [
        {"path": "eventstream.json", "payload": es_json_b64, "payloadType": "InlineBase64"},
        {"path": "eventstreamProperties.json", "payload": props_b64, "payloadType": "InlineBase64"},
        {"path": ".platform", "payload": platform_b64, "payloadType": "InlineBase64"},
    ]}}

    print("  Pushing definition via updateDefinition API...")
    r = requests.post(
        f"{API}/workspaces/{ws_id}/eventstreams/{es_id}/updateDefinition?updateMetadata=true",
        headers=H, json=body
    )
    print(f"  HTTP {r.status_code}")
    if r.status_code == 200:
        return True
    elif r.status_code == 202:
        op_id = r.headers.get("x-ms-operation-id")
        ok, _ = _wait_lro(op_id, token, "updateDefinition")
        return ok
    else:
        print(f"  Error: {r.text[:500]}")
        return False


# ── Step 4: Verify topology ──────────────────────────────────────
def verify_topology(ws_id, es_id, token):
    """Check topology status via the topology API."""
    H = _headers(token)
    time.sleep(5)

    r = requests.get(f"{API}/workspaces/{ws_id}/eventstreams/{es_id}/topology", headers=H)
    if r.status_code != 200:
        print(f"  Topology check failed: HTTP {r.status_code}")
        return False

    topo = r.json()
    all_ok = True
    for kind in ("sources", "destinations", "streams"):
        nodes = topo.get(kind, [])
        print(f"  {kind.capitalize()}: {len(nodes)}")
        for n in nodes:
            st = n.get("status", "?")
            print(f"    {n['name']} ({n['type']}) — {st}")
            if st in ("Failed", "Warning"):
                all_ok = False
    return all_ok


# ── Main ──────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("Wire Healthcare_RTI_Eventstream — Full Topology via API")
    print("=" * 60)

    token = get_token()

    # Step 1: Discover
    print("\n[Step 1] Discovering workspace items...")
    info = discover(token)
    ws_id = info["ws_id"]

    if not all([info["eventhouse_id"], info["kqldb_id"], info["eventstream_id"]]):
        print("\nERROR: Missing required items (Eventhouse, KQL Database, Eventstream).")
        print("Run Healthcare_Launcher with DEPLOY_STREAMING=True first.")
        sys.exit(1)

    # Step 2: Build topology
    print("\n[Step 2] Building Eventstream topology...")
    es_def = build_topology(
        ws_id, info["kqldb_id"], info["kqldb_name"],
        lakehouse_id=info["lakehouse_bronze_id"],
        activator_id=info["activator_id"]
    )
    n_dest = len(es_def["destinations"])
    dest_names = [d["name"] for d in es_def["destinations"]]
    print(f"  Topology: CustomEndpoint → Stream → {n_dest} destinations")
    for dn in dest_names:
        print(f"    → {dn}")
    if not info["lakehouse_bronze_id"]:
        print("  NOTE: lh_bronze_raw not found — skipping Lakehouse destination")
    if not info["activator_id"]:
        print("  NOTE: No Activator/Reflex item found — skipping Activator destination")
        print("        Create one in the portal and re-run to auto-wire it.")

    # Step 3: Push
    print("\n[Step 3] Pushing definition via API...")
    ok = push_definition(ws_id, info["eventstream_id"], es_def, token)
    if not ok:
        print("\nERROR: Failed to push definition.")
        sys.exit(1)
    print("  Definition pushed successfully!")

    # Step 4: Verify
    print("\n[Step 4] Verifying topology...")
    healthy = verify_topology(ws_id, info["eventstream_id"], token)

    # Summary
    es_url = f"https://app.fabric.microsoft.com/groups/{ws_id}/eventstreams/{info['eventstream_id']}"
    print("\n" + "=" * 60)
    if healthy:
        print("  Eventstream topology wired successfully!")
    else:
        print("  Eventstream topology wired (some nodes still starting)")
    print("=" * 60)
    print()
    dest_summary = " + ".join(dest_names)
    print(f"  Topology: CustomEndpoint → Stream → {dest_summary}")
    print(f"  Eventstream URL: {es_url}")
    print()
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  ONE REMAINING STEP (portal only):                     │")
    print("  │                                                        │")
    print("  │  1. Open the Eventstream URL above in your browser     │")
    print("  │  2. Click the 'HealthcareCustomEndpoint' source node   │")
    print("  │  3. Copy the Connection String from the details pane   │")
    print("  │  4. Paste into NB_RTI_Event_Simulator →                │")
    print("  │     ES_CONNECTION_STRING parameter                     │")
    print("  │                                                        │")
    print("  │  The API wired the full topology but cannot expose     │")
    print("  │  the connection string (Fabric API limitation).        │")
    print("  └─────────────────────────────────────────────────────────┘")

if __name__ == "__main__":
    main()
