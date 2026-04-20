"""
Wire Healthcare_RTI_Eventstream with full topology via API:
  - Custom Endpoint source
  - Eventhouse (KQL DB) destination
  - Default + derived streams
Then retrieve the connection string for the simulator.
"""
import subprocess, json, requests, base64, time, sys

# ── Auth ──
def get_token(resource):
    r = subprocess.run(
        ["cmd", "/c", "az", "account", "get-access-token", "--resource", resource],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"ERROR: az login failed: {r.stderr}")
        sys.exit(1)
    return json.loads(r.stdout)["accessToken"]

token = get_token("https://api.fabric.microsoft.com")
H = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
API = "https://api.fabric.microsoft.com/v1"
WS = "e0f2c894-7f63-4301-b2e1-2b8c6ae8c40c"

# ── Step 1: Discover workspace items ──
print("=" * 60)
print("Step 1: Discover workspace items")
print("=" * 60)
r = requests.get(f"{API}/workspaces/{WS}/items", headers=H)
items = r.json().get("value", [])

eventhouse_id = None
kqldb_id = None
eventstream_id = None
kqldb_name = None

for i in items:
    if i["type"] == "Eventhouse" and "Healthcare" in i["displayName"]:
        eventhouse_id = i["id"]
        print(f"  Eventhouse:   {i['displayName']} = {i['id']}")
    elif i["type"] == "KQLDatabase" and "Healthcare" in i["displayName"]:
        kqldb_id = i["id"]
        kqldb_name = i["displayName"]
        print(f"  KQL Database: {i['displayName']} = {i['id']}")
    elif i["type"] == "Eventstream" and "Healthcare" in i["displayName"]:
        eventstream_id = i["id"]
        print(f"  Eventstream:  {i['displayName']} = {i['id']}")

if not all([eventhouse_id, kqldb_id, eventstream_id]):
    print("ERROR: Missing items. Need Eventhouse, KQL Database, and Eventstream.")
    sys.exit(1)

# ── Step 2: Get current Eventstream definition ──
print()
print("=" * 60)
print("Step 2: Get current Eventstream definition")
print("=" * 60)

r = requests.post(
    f"{API}/workspaces/{WS}/eventstreams/{eventstream_id}/getDefinition",
    headers=H
)
print(f"  getDefinition status: {r.status_code}")

if r.status_code == 202:
    # LRO - poll for completion
    op_id = r.headers.get("x-ms-operation-id")
    location = r.headers.get("Location")
    print(f"  LRO operation: {op_id}")
    for attempt in range(30):
        time.sleep(2)
        poll = requests.get(f"{API}/operations/{op_id}", headers=H)
        status = poll.json().get("status", "Unknown")
        print(f"  Poll {attempt+1}: {status}")
        if status in ("Succeeded", "Failed"):
            break
    if status == "Succeeded":
        # Get the result
        result_url = f"{API}/operations/{op_id}/result"
        r = requests.get(result_url, headers=H)
        print(f"  Result status: {r.status_code}")

if r.status_code == 200:
    defn = r.json()
    parts = defn.get("definition", {}).get("parts", [])
    print(f"  Found {len(parts)} definition parts:")
    for p in parts:
        payload_decoded = base64.b64decode(p["payload"]).decode("utf-8", errors="replace")
        print(f"    {p['path']}: {len(payload_decoded)} chars")
        if p["path"] == "eventstream.json":
            print(f"    Current topology: {payload_decoded[:500]}")
            current_es = json.loads(payload_decoded)
            print(f"    Sources: {len(current_es.get('sources', []))}")
            print(f"    Destinations: {len(current_es.get('destinations', []))}")
            print(f"    Streams: {len(current_es.get('streams', []))}")
else:
    print(f"  Response: {r.text[:500]}")

# ── Step 3: Build full Eventstream definition ──
print()
print("=" * 60)
print("Step 3: Build and push Eventstream definition")
print("=" * 60)

# Build the eventstream.json with Custom Endpoint source + Eventhouse destination
eventstream_def = {
    "sources": [
        {
            "name": "HealthcareCustomEndpoint",
            "type": "CustomEndpoint",
            "properties": {
                "inputSerialization": {
                    "type": "Json",
                    "properties": {
                        "encoding": "UTF8"
                    }
                }
            }
        }
    ],
    "destinations": [
        {
            "name": "HealthcareEventhouse",
            "type": "Eventhouse",
            "properties": {
                "dataIngestionMode": "ProcessedIngestion",
                "workspaceId": WS,
                "itemId": kqldb_id,
                "databaseName": kqldb_name,
                "tableName": "rti_claims_events",
                "inputSerialization": {
                    "type": "Json",
                    "properties": {
                        "encoding": "UTF8"
                    }
                }
            },
            "inputNodes": [
                {"name": "HealthcareRTI-stream"}
            ]
        }
    ],
    "streams": [
        {
            "name": "HealthcareRTI-stream",
            "type": "DefaultStream",
            "properties": {},
            "inputNodes": [
                {"name": "HealthcareCustomEndpoint"}
            ]
        }
    ],
    "operators": [],
    "compatibilityLevel": "1.1"
}

# Build platform file
platform_def = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
    "metadata": {
        "type": "Eventstream",
        "displayName": "Healthcare_RTI_Eventstream"
    },
    "config": {
        "version": "2.0",
        "logicalId": eventstream_id
    }
}

# Build properties
properties_def = {
    "retentionTimeInDays": 1,
    "eventThroughputLevel": "Low"
}

# Encode to base64
es_json_b64 = base64.b64encode(json.dumps(eventstream_def, indent=2).encode()).decode()
platform_b64 = base64.b64encode(json.dumps(platform_def, indent=2).encode()).decode()
properties_b64 = base64.b64encode(json.dumps(properties_def, indent=2).encode()).decode()

print(f"  eventstream.json: {len(json.dumps(eventstream_def))} chars")
print(f"  Topology: 1 source (CustomEndpoint) → 1 stream → 1 destination (Eventhouse)")

# Push via updateDefinition
update_body = {
    "definition": {
        "parts": [
            {
                "path": "eventstream.json",
                "payload": es_json_b64,
                "payloadType": "InlineBase64"
            },
            {
                "path": "eventstreamProperties.json",
                "payload": properties_b64,
                "payloadType": "InlineBase64"
            },
            {
                "path": ".platform",
                "payload": platform_b64,
                "payloadType": "InlineBase64"
            }
        ]
    }
}

print(f"\n  Calling updateDefinition...")
r = requests.post(
    f"{API}/workspaces/{WS}/eventstreams/{eventstream_id}/updateDefinition?updateMetadata=true",
    headers=H,
    json=update_body
)
print(f"  updateDefinition status: {r.status_code}")

if r.status_code == 202:
    op_id = r.headers.get("x-ms-operation-id")
    print(f"  LRO operation: {op_id}")
    for attempt in range(60):
        time.sleep(3)
        poll = requests.get(f"{API}/operations/{op_id}", headers=H)
        pj = poll.json()
        status = pj.get("status", "Unknown")
        pct = pj.get("percentComplete", "?")
        print(f"  Poll {attempt+1}: {status} ({pct}%)")
        if status == "Succeeded":
            print("  ✅ Definition updated successfully!")
            break
        elif status == "Failed":
            print(f"  ❌ Failed: {json.dumps(pj, indent=2)}")
            break
elif r.status_code == 200:
    print("  ✅ Definition updated successfully!")
else:
    print(f"  Response: {r.text[:1000]}")

# ── Step 4: Retrieve the connection string ──
print()
print("=" * 60)
print("Step 4: Retrieve connection string from updated definition")
print("=" * 60)

time.sleep(5)  # Give it a moment to settle

r = requests.post(
    f"{API}/workspaces/{WS}/eventstreams/{eventstream_id}/getDefinition",
    headers=H
)
print(f"  getDefinition status: {r.status_code}")

if r.status_code == 202:
    op_id = r.headers.get("x-ms-operation-id")
    for attempt in range(30):
        time.sleep(2)
        poll = requests.get(f"{API}/operations/{op_id}", headers=H)
        status = poll.json().get("status", "Unknown")
        print(f"  Poll {attempt+1}: {status}")
        if status in ("Succeeded", "Failed"):
            break
    if status == "Succeeded":
        r = requests.get(f"{API}/operations/{op_id}/result", headers=H)

if r.status_code == 200:
    defn = r.json()
    parts = defn.get("definition", {}).get("parts", [])
    for p in parts:
        payload_decoded = base64.b64decode(p["payload"]).decode("utf-8", errors="replace")
        if p["path"] == "eventstream.json":
            updated_es = json.loads(payload_decoded)
            print(f"\n  Updated topology:")
            print(f"    Sources: {len(updated_es.get('sources', []))}")
            print(f"    Destinations: {len(updated_es.get('destinations', []))}")
            print(f"    Streams: {len(updated_es.get('streams', []))}")

            # Look for connection info in sources
            for src in updated_es.get("sources", []):
                print(f"\n    Source: {src['name']} (type={src['type']})")
                props = src.get("properties", {})
                print(f"    Properties: {json.dumps(props, indent=6)}")
                # Check for connection string, endpoint, etc.
                for key in ["connectionString", "endpoint", "eventHubName",
                             "sharedAccessKeyName", "sharedAccessKey",
                             "dataConnectionId", "customEndpointAddress"]:
                    if key in props:
                        print(f"    >>> {key}: {props[key]}")

            # Also dump full definition for inspection
            print(f"\n  Full eventstream.json (for inspection):")
            print(json.dumps(updated_es, indent=2)[:3000])
else:
    print(f"  Response: {r.text[:500]}")

print()
print("=" * 60)
print("Done")
print("=" * 60)
