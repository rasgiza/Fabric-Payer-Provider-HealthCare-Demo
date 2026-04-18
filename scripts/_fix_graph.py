"""
Diagnose and fix the Healthcare graph model.
1. Check queryable schema (which node/edge types actually exist)
2. Get the current definition
3. Rebuild and push corrected definition if edges are missing
4. Trigger data reload
"""
import sys, json, time
sys.path.insert(0, ".")
from azure.identity import InteractiveBrowserCredential
from clients.graph_client import GraphModelClient
from clients.graph_definition_builder import GraphDefinitionBuilder
from pathlib import Path

WS = "2966d7c8-dd6c-4b14-a4c9-82cce36d7fe4"
LH = "655a25f7-837c-40e6-9552-8cb42515afc5"
GRAPH_ID = "6fb20f2d-a35f-449c-a891-64cb2ec2628a"
ONTOLOGY_DIR = Path(__file__).resolve().parent.parent / "ontology" / "Healthcare_Demo_Ontology_HLS"

print("Authenticating...")
cred = InteractiveBrowserCredential(login_hint="admin@MngEnvMCAP661056.onmicrosoft.com")
token = cred.get_token("https://analysis.windows.net/powerbi/api/.default").token
gc = GraphModelClient(token)

# ── Step 1: Check status ──────────────────────────────────
print("\n=== Step 1: Graph Model Status ===")
item = gc.get(WS, GRAPH_ID)
if item:
    props = item.get("properties", {})
    print(f"  queryReadiness: {props.get('queryReadiness', 'N/A')}")
    loading = props.get("lastDataLoadingStatus", {})
    print(f"  loadingStatus:  {loading.get('status', 'N/A')}")
    if loading.get("startTime"):
        print(f"  loadStartTime:  {loading['startTime']}")
    if loading.get("endTime"):
        print(f"  loadEndTime:    {loading['endTime']}")

# ── Step 2: Check queryable graph type ────────────────────
print("\n=== Step 2: Queryable Graph Schema ===")
schema = gc.get_queryable_graph_type(WS, GRAPH_ID)
if schema:
    node_types = schema.get("nodeTypes", [])
    edge_types = schema.get("edgeTypes", [])
    print(f"  Queryable nodeTypes: {len(node_types)}")
    for nt in node_types:
        labels = nt.get("labels", [])
        pk = nt.get("primaryKeyProperties", [])
        print(f"    {labels} (PK: {pk})")
    print(f"  Queryable edgeTypes: {len(edge_types)}")
    for et in edge_types:
        labels = et.get("labels", [])
        src = et.get("sourceNodeType", {}).get("labels", ["?"])
        dst = et.get("destinationNodeType", {}).get("labels", ["?"])
        print(f"    {labels}: {src} -> {dst}")
    if len(edge_types) == 0:
        print("  *** NO EDGE TYPES REGISTERED — this is why traversals fail! ***")
else:
    print("  Could not retrieve queryable schema")

# ── Step 3: Get current definition ────────────────────────
print("\n=== Step 3: Current Graph Definition ===")
defn = gc.get_definition(WS, GRAPH_ID)
if defn:
    for part_name, content in defn.items():
        if part_name == "graphType.json":
            nt = content.get("nodeTypes", [])
            et = content.get("edgeTypes", [])
            print(f"  graphType.json: {len(nt)} nodeTypes, {len(et)} edgeTypes")
            if len(et) == 0:
                print("  *** GRAPH DEFINITION HAS NO EDGE TYPES ***")
            for e in et[:3]:
                print(f"    Sample edge: {e.get('labels', [])} "
                      f"{e.get('sourceNodeType', {}).get('alias', '?')} -> "
                      f"{e.get('destinationNodeType', {}).get('alias', '?')}")
            if len(et) > 3:
                print(f"    ... and {len(et)-3} more")
        elif part_name == "graphDefinition.json":
            nts = content.get("nodeTables", [])
            ets = content.get("edgeTables", [])
            print(f"  graphDefinition.json: {len(nts)} nodeTables, {len(ets)} edgeTables")
            if len(ets) == 0:
                print("  *** NO EDGE TABLES — edges can't load ***")
            for e in ets[:3]:
                print(f"    Edge table: {e.get('edgeTypeAlias', '?')} "
                      f"src={e.get('sourceNodeKeyColumns', [])} "
                      f"dst={e.get('destinationNodeKeyColumns', [])}")
            if len(ets) > 3:
                print(f"    ... and {len(ets)-3} more")
        elif part_name == "dataSources.json":
            sources = content.get("dataSources", [])
            print(f"  dataSources.json: {len(sources)} sources")
            for s in sources[:3]:
                path = s.get("properties", {}).get("path", "")
                print(f"    {s.get('name', '?')}: ...{path[-60:]}")
            if len(sources) > 3:
                print(f"    ... and {len(sources)-3} more")
        else:
            print(f"  {part_name}: present")
else:
    print("  Could not retrieve definition (may need LRO)")

# ── Step 4: Rebuild and push if edges are missing ─────────
print("\n=== Step 4: Rebuild Decision ===")
needs_rebuild = False

if defn:
    gt = defn.get("graphType.json", {})
    gd = defn.get("graphDefinition.json", {})
    if len(gt.get("edgeTypes", [])) < 10:
        print(f"  REBUILD NEEDED: Only {len(gt.get('edgeTypes', []))} edge types (expected 18)")
        needs_rebuild = True
    if len(gd.get("edgeTables", [])) < 10:
        print(f"  REBUILD NEEDED: Only {len(gd.get('edgeTables', []))} edge tables (expected 18)")
        needs_rebuild = True
else:
    print("  REBUILD NEEDED: Could not retrieve definition")
    needs_rebuild = True

if not needs_rebuild:
    # Check if loading is stuck
    if item:
        loading = item.get("properties", {}).get("lastDataLoadingStatus", {})
        status = loading.get("status", "")
        if status == "InProgress":
            start = loading.get("startTime", "")
            print(f"  Data load stuck InProgress since {start}")
            print(f"  Will trigger reload via updateDefinition")
            needs_rebuild = True
        elif status == "Failed":
            print(f"  Data load FAILED — will trigger reload")
            needs_rebuild = True

if needs_rebuild:
    print("\n=== Step 5: Rebuilding Graph Definition ===")
    builder = GraphDefinitionBuilder(ONTOLOGY_DIR, WS, LH)
    builder.load_ontology()

    desc = (f"Graph model for Healthcare_Demo_Ontology_HLS. "
            f"{len(builder.entities)} node types, {len(builder.relationships)} edge types, "
            f"bound to lh_gold_curated delta tables.")
    parts = builder.build_all_parts(
        display_name="Healthcare_Demo_Graph",
        description=desc,
    )

    print(f"\n  Pushing updated definition to graph {GRAPH_ID}...")
    ok = gc.update_definition(WS, GRAPH_ID, parts)
    if ok:
        print("  [OK] Definition pushed — data reload triggered")
        print("  Waiting for data load (polling every 30s, max 10min)...")
        loaded = gc.wait_for_data_load(WS, GRAPH_ID, timeout=600, poll_interval=30)
        if loaded:
            print("  [OK] Data loaded successfully!")
        else:
            print("  [WARN] Data load not yet complete — check Fabric portal")
    else:
        print("  [FAIL] Could not push definition")
else:
    print("  Graph definition looks correct — no rebuild needed")

# ── Step 6: Final verification ────────────────────────────
print("\n=== Step 6: Final Verification ===")
item = gc.get(WS, GRAPH_ID)
if item:
    props = item.get("properties", {})
    print(f"  queryReadiness: {props.get('queryReadiness', 'N/A')}")
    loading = props.get("lastDataLoadingStatus", {})
    print(f"  loadingStatus:  {loading.get('status', 'N/A')}")

# Quick GQL test
print("\n  Testing Provider query...")
r = gc.execute_query(WS, GRAPH_ID,
    "MATCH (p:Provider) RETURN p.display_name, p.specialty LIMIT 3")
if r:
    result = r.get("result", {})
    data = result.get("data", [])
    if data:
        print(f"  [OK] Provider query returned {len(data)} rows:")
        for row in data[:3]:
            print(f"    {row}")
    else:
        print(f"  Provider query returned no data. Status: {r.get('status', {}).get('description', 'unknown')}")

print("\n  Testing edge traversal...")
r = gc.execute_query(WS, GRAPH_ID,
    "MATCH (e:Encounter)-[:involves]->(pt:Patient) RETURN pt.patient_id, e.encounter_type LIMIT 3")
if r:
    result = r.get("result", {})
    data = result.get("data", [])
    status = r.get("status", {})
    if data:
        print(f"  [OK] Traversal returned {len(data)} rows:")
        for row in data[:3]:
            print(f"    {row}")
    elif status.get("code") == "00000":
        print(f"  Traversal succeeded but no data yet (data still loading?)")
    else:
        print(f"  Traversal error: {status.get('description', 'unknown')}")
        cause = status.get("cause", {})
        if cause:
            print(f"    Cause: {cause.get('description', '')[:200]}")

print("\n=== Done ===")
