# Fabric notebook source

# METADATA **{"language":"python"}**

# MARKDOWN **{"language":"markdown"}**

# # NB_Deploy_Graph_Model
# 
# **Standalone graph model deployer & diagnostic tool.**
# 
# Use this notebook when:
# - The auto-provisioned graph (from ontology) is not working
# - You want to test or debug individual graph nodes
# - You want to deploy a custom graph model from ontology metadata
# - You need to diagnose why specific entity types fail in the graph
# 
# **Prerequisites:**
# - Ontology has been deployed (Cell 10a / `05_deploy_ontology.py`)
# - Gold lakehouse tables exist in `lh_gold_curated`
# - Default lakehouse is set to `lh_gold_curated`
# 
# **What this notebook does:**
# 1. Discovers ontology files (local or downloads from GitHub)
# 2. Validates bindings against actual Delta table schemas
# 3. Builds a 5-part graph definition
# 4. Per-node validation: tests each node individually to find failures
# 5. Deploys the graph (excluding any bad nodes)
# 6. Waits for data load and runs a smoke test

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# CELL 1 -- Configuration & Discovery
# ============================================================================

import json, requests, time, base64, os, re, math, uuid

print("=" * 60)
print("  NB_Deploy_Graph_Model -- Ontology Graph Deployer")
print("=" * 60)

# -- Config -----------------------------------------------------------
ONTOLOGY_NAME = "Healthcare_Demo_Ontology_HLS"
GRAPH_MODEL_NAME = "Healthcare_Demo_Graph"
GITHUB_OWNER = "rasgiza"
GITHUB_REPO = "Fabric-Payer-Provider-HealthCare-Demo"
GITHUB_BRANCH = "main"

# -- Auth & Discovery -------------------------------------------------
from notebookutils import mssparkutils

token = mssparkutils.credentials.getToken("pbi")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
API = "https://api.fabric.microsoft.com/v1"

workspace_id = spark.conf.get("trident.workspace.id")
print(f"  Workspace: {workspace_id}")

# Discover lh_gold_curated
resp = requests.get(f"{API}/workspaces/{workspace_id}/lakehouses", headers=headers)
resp.raise_for_status()
lh_gold_id = None
for lh in resp.json().get("value", []):
    if lh["displayName"] == "lh_gold_curated":
        lh_gold_id = lh["id"]
        break
if not lh_gold_id:
    raise RuntimeError("lh_gold_curated not found -- run the pipeline first")
print(f"  Lakehouse: lh_gold_curated ({lh_gold_id})")

GM_API = f"{API}/workspaces/{workspace_id}/graphModels"

# -- Find ontology directory ------------------------------------------
ont_dir = None
for base in [".lakehouse/default/Files/src", "/lakehouse/default/Files/src"]:
    if not os.path.isdir(base):
        continue
    direct = os.path.join(base, "ontology", ONTOLOGY_NAME)
    if os.path.isdir(direct):
        ont_dir = direct
        break
    for sub in os.listdir(base):
        nested = os.path.join(base, sub, "ontology", ONTOLOGY_NAME)
        if os.path.isdir(nested):
            ont_dir = nested
            break
    if ont_dir:
        break

if not ont_dir:
    import tempfile
    print(f"  Ontology not found locally -- downloading from GitHub...")
    raw_base = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/ontology/{ONTOLOGY_NAME}"
    r_manifest = requests.get(f"{raw_base}/manifest.json")
    r_manifest.raise_for_status()
    manifest = r_manifest.json()
    ont_dir = tempfile.mkdtemp(prefix="ontology_")
    with open(os.path.join(ont_dir, "manifest.json"), "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2)
    for part_info in manifest.get("exportedParts", []):
        part_path = part_info["path"]
        r_part = requests.get(f"{raw_base}/{part_path}")
        r_part.raise_for_status()
        dest = os.path.join(ont_dir, part_path.replace("/", os.sep))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as pf:
            pf.write(r_part.content)
    print(f"  Downloaded ontology to: {ont_dir}")
else:
    print(f"  Ontology dir: {ont_dir}")

print()
print("  [OK] Configuration ready")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# CELL 2 -- Parse Ontology & Validate Against Table Schemas
# ============================================================================

print("=" * 60)
print("  Step 1: Parse ontology + validate bindings")
print("=" * 60)

# -- Ontology value type -> Graph Model property type --
TYPE_MAP = {
    "String": "STRING", "BigInt": "INT", "Int": "INT", "Int32": "INT",
    "Int64": "INT", "Double": "FLOAT", "Decimal": "FLOAT", "Float": "FLOAT",
    "DateTime": "DATETIME", "Date": "DATETIME", "Boolean": "BOOLEAN",
}

entity_dir = os.path.join(ont_dir, "EntityTypes")
rel_dir = os.path.join(ont_dir, "RelationshipTypes")

# -- Parse entity types --
entities = {}
for ent_name in sorted(os.listdir(entity_dir)):
    ent_path = os.path.join(entity_dir, ent_name)
    if not os.path.isdir(ent_path):
        continue
    defn_file = os.path.join(ent_path, "definition.json")
    if not os.path.exists(defn_file):
        continue
    with open(defn_file, "r", encoding="utf-8-sig") as f:
        defn = json.load(f)
    eid = defn["id"]
    pk_prop_id = defn["entityIdParts"][0] if defn.get("entityIdParts") else None
    prop_map = {p["id"]: {"name": p["name"], "type": p["valueType"]}
                for p in defn.get("properties", [])}
    pk_name = (prop_map[pk_prop_id]["name"]
               if pk_prop_id and pk_prop_id in prop_map else None)

    bindings, source_table = {}, None
    db_dir = os.path.join(ent_path, "DataBindings")
    if os.path.isdir(db_dir):
        for fname in os.listdir(db_dir):
            if not fname.endswith(".json"):
                continue
            with open(os.path.join(db_dir, fname), "r", encoding="utf-8-sig") as bf:
                db = json.load(bf)
            cfg = db.get("dataBindingConfiguration", {})
            bindings.update({
                pb["targetPropertyId"]: pb["sourceColumnName"]
                for pb in cfg.get("propertyBindings", [])
            })
            source_table = (cfg.get("sourceTableProperties", {})
                           .get("sourceTableName") or source_table)

    pk_col = bindings.get(pk_prop_id) if pk_prop_id else None

    entities[eid] = {
        "name": defn["name"], "pk": pk_name, "pk_col": pk_col,
        "props": prop_map, "table": source_table, "bindings": bindings,
    }

# -- Parse relationships --
relationships = {}
if os.path.isdir(rel_dir):
    for rel_name in sorted(os.listdir(rel_dir)):
        rel_path = os.path.join(rel_dir, rel_name)
        if not os.path.isdir(rel_path):
            continue
        defn_file = os.path.join(rel_path, "definition.json")
        if not os.path.exists(defn_file):
            continue
        with open(defn_file, "r", encoding="utf-8-sig") as f:
            defn = json.load(f)
        rid = defn["id"]
        src_id = defn["source"]["entityTypeId"]
        tgt_id = defn["target"]["entityTypeId"]

        ctx_table, src_cols, tgt_cols = None, [], []
        ctx_dir = os.path.join(rel_path, "Contextualizations")
        if os.path.isdir(ctx_dir):
            for fname in os.listdir(ctx_dir):
                if not fname.endswith(".json"):
                    continue
                with open(os.path.join(ctx_dir, fname), "r", encoding="utf-8-sig") as cf:
                    ctx = json.load(cf)
                ctx_table = ctx.get("dataBindingTable", {}).get("sourceTableName")
                src_cols = [sk["sourceColumnName"]
                            for sk in ctx.get("sourceKeyRefBindings", [])]
                tgt_cols = [tk["sourceColumnName"]
                            for tk in ctx.get("targetKeyRefBindings", [])]

        relationships[rid] = {
            "name": defn["name"], "src": src_id, "tgt": tgt_id,
            "table": ctx_table, "src_cols": src_cols, "tgt_cols": tgt_cols,
        }

valid_ids = {eid for eid, e in entities.items() if e["table"]}
print(f"  Parsed: {len(entities)} entities ({len(valid_ids)} with tables), "
      f"{len(relationships)} relationships")

# -- Validate bindings vs actual table columns --
print()
print("  Validating bindings against table schemas...")
val_errors = []
table_cols_cache = {}

def _get_table_cols(tbl_name):
    if tbl_name in table_cols_cache:
        return table_cols_cache[tbl_name]
    cols = None
    # Try 1: Spark SQL (works if default lakehouse is attached)
    try:
        _df = spark.sql(f"DESCRIBE lh_gold_curated.{tbl_name}")
        cols = {r["col_name"] for r in _df.collect() if not r["col_name"].startswith("#")}
    except Exception:
        pass
    # Try 2: Read Delta schema via OneLake path (no default lakehouse needed)
    if cols is None:
        try:
            _path = (f"abfss://{workspace_id}@onelake.dfs.fabric.microsoft.com"
                     f"/{lh_gold_id}/Tables/{tbl_name}")
            _df = spark.read.format("delta").load(_path)
            cols = {f.name for f in _df.schema.fields}
        except Exception:
            pass
    table_cols_cache[tbl_name] = cols
    return cols

# Quick check: can we reach tables at all?
_sample_tbl = next((e["table"] for e in entities.values() if e.get("table")), None)
_can_validate = _get_table_cols(_sample_tbl) is not None if _sample_tbl else False
if not _can_validate:
    print("  [INFO] Table schemas not accessible (no default lakehouse context)")
    print("         Skipping column validation -- property consistency still checked")

for eid, e in entities.items():
    if not e["table"]:
        continue
    actual = _get_table_cols(e["table"]) if _can_validate else None

    # Check every bound column exists (only if table is accessible)
    if actual is not None:
        for pid, src_col in e["bindings"].items():
            if src_col not in actual:
                prop_name = e["props"].get(pid, {}).get("name", "?")
                val_errors.append(
                    f"{e['name']}: binding col '{src_col}' (prop={prop_name}) "
                    f"not in {e['table']} columns"
                )

    # Check property name vs source column consistency (always)
    for pid, prop_info in e["props"].items():
        src_col = e["bindings"].get(pid)
        if src_col and prop_info["name"] != src_col:
            print(f"    [WARN] {e['name']}: property '{prop_info['name']}' "
                  f"!= binding column '{src_col}' (may confuse auto-graph)")

# Validate contextualization columns (only if tables are accessible)
if _can_validate:
    for rid, r in relationships.items():
        if not r["table"]:
            continue
        actual = _get_table_cols(r["table"])
        if actual is None:
            val_errors.append(f"{r['name']}: ctx table {r['table']} not accessible")
            continue
        for sc in r["src_cols"]:
            if sc not in actual:
                val_errors.append(f"{r['name']}: ctx sourceKey '{sc}' not in {r['table']}")
        for tc in r["tgt_cols"]:
            if tc not in actual:
                val_errors.append(f"{r['name']}: ctx targetKey '{tc}' not in {r['table']}")

if val_errors:
    print()
    print(f"  *** VALIDATION ERRORS ({len(val_errors)}) ***")
    for ve in val_errors:
        print(f"    {ve}")
    print()
    print("  NOTE: The graph will be deployed excluding problematic nodes.")
    print("  Fix the ontology bindings and re-run to get a full graph.")
else:
    print("  [OK] All bindings verified against table schemas")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# CELL 3 -- Build 5-Part Graph Definition
# ============================================================================

print("=" * 60)
print("  Step 2: Build graph definition")
print("=" * 60)

# -- graphType.json --
node_types = []
for eid, e in entities.items():
    if eid not in valid_ids:
        continue
    props = [
        {"name": p["name"], "type": TYPE_MAP.get(p["type"], "STRING")}
        for pid, p in e["props"].items() if pid in e["bindings"]
    ]
    node_types.append({
        "alias": f"{e['name']}_nodeType",
        "labels": [e["name"]],
        "primaryKeyProperties": [e["pk"]] if e["pk"] else [],
        "properties": props,
    })

edge_types = []
for rid, r in relationships.items():
    if not r["table"] or not r["src_cols"] or not r["tgt_cols"]:
        continue
    if r["src"] not in valid_ids or r["tgt"] not in valid_ids:
        continue
    edge_types.append({
        "alias": f"{r['name']}_edgeType",
        "labels": [r["name"]],
        "sourceNodeType": {"alias": f"{entities[r['src']]['name']}_nodeType"},
        "destinationNodeType": {"alias": f"{entities[r['tgt']]['name']}_nodeType"},
        "properties": [],
    })

graph_type = {"schemaVersion": "1.0.0", "nodeTypes": node_types, "edgeTypes": edge_types}
print(f"  graphType:       {len(node_types)} nodes, {len(edge_types)} edges")

# -- graphDefinition.json --
node_tables = []
for eid, e in entities.items():
    if eid not in valid_ids:
        continue
    mappings = [
        {"propertyName": p["name"], "sourceColumn": e["bindings"][pid]}
        for pid, p in e["props"].items() if pid in e["bindings"]
    ]
    node_tables.append({
        "id": str(uuid.uuid4()),
        "nodeTypeAlias": f"{e['name']}_nodeType",
        "dataSourceName": f"{e['table']}_Source",
        "propertyMappings": mappings,
    })

edge_tables = []
for rid, r in relationships.items():
    if not r["table"] or not r["src_cols"] or not r["tgt_cols"]:
        continue
    if r["src"] not in valid_ids or r["tgt"] not in valid_ids:
        continue
    src_ent = entities[r["src"]]
    src_key = [src_ent["pk_col"]] if src_ent.get("pk_col") else r["src_cols"]
    edge_tables.append({
        "id": str(uuid.uuid4()),
        "edgeTypeAlias": f"{r['name']}_edgeType",
        "dataSourceName": f"{r['table']}_Source",
        "sourceNodeKeyColumns": src_key,
        "destinationNodeKeyColumns": r["tgt_cols"],
        "propertyMappings": [],
    })

graph_def = {"schemaVersion": "1.0.0", "nodeTables": node_tables, "edgeTables": edge_tables}
print(f"  graphDefinition: {len(node_tables)} nodeTables, {len(edge_tables)} edgeTables")

# -- dataSources.json --
tables = set()
for eid, e in entities.items():
    if eid in valid_ids and e["table"]:
        tables.add(e["table"])
for r in relationships.values():
    if (r["table"] and r["src_cols"] and r["tgt_cols"]
            and r["src"] in valid_ids and r["tgt"] in valid_ids):
        tables.add(r["table"])

table_paths = {}
for t in sorted(tables):
    try:
        loc_df = spark.sql(f"DESCRIBE EXTENDED lh_gold_curated.{t}")
        for row in loc_df.collect():
            if row["col_name"] == "Location":
                table_paths[t] = row["data_type"]
                break
        if t not in table_paths:
            raise Exception("Location not found")
    except Exception:
        table_paths[t] = (
            f"abfss://{workspace_id}@onelake.dfs.fabric.microsoft.com"
            f"/{lh_gold_id}/Tables/{t}"
        )

data_sources = {
    "dataSources": [
        {"name": f"{t}_Source", "type": "DeltaTable",
         "properties": {"path": table_paths[t]}}
        for t in sorted(tables)
    ]
}
print(f"  dataSources:     {len(tables)} tables")

# -- stylingConfiguration.json --
n = len(node_types)
radius = 300
positions, styles = {}, {}
for i, nt in enumerate(node_types):
    alias = nt["alias"]
    angle = 2 * math.pi * i / max(n, 1)
    positions[alias] = {
        "x": int(radius + radius * math.cos(angle)),
        "y": int(radius + radius * math.sin(angle)),
    }
    styles[alias] = {"size": 30}
for et in edge_types:
    styles[et["alias"]] = {"size": 30}

styling = {
    "schemaVersion": "1.0.0",
    "modelLayout": {
        "positions": positions,
        "styles": styles,
        "pan": {"x": 0, "y": 0},
        "zoomLevel": 1,
    },
}

# -- .platform --
platform = {
    "$schema": (
        "https://developer.microsoft.com/json-schemas/fabric/"
        "gitIntegration/platformProperties/2.0.0/schema.json"
    ),
    "metadata": {"type": "GraphModel", "displayName": GRAPH_MODEL_NAME},
    "config": {
        "version": "2.0",
        "logicalId": "00000000-0000-0000-0000-000000000000",
    },
}


def encode_part(path, content):
    payload = base64.b64encode(json.dumps(content, indent=2).encode()).decode()
    return {"path": path, "payload": payload, "payloadType": "InlineBase64"}


# -- Self-validation --
print()
print("  Validating definition cross-references...")
_err = []
for _nt in node_types:
    _pnames = {p["name"] for p in _nt["properties"]}
    for _pk in _nt.get("primaryKeyProperties", []):
        if _pk not in _pnames:
            _err.append(f"nodeType {_nt['alias']}: PK '{_pk}' not in properties")
_nt_aliases = {nt["alias"] for nt in node_types}
for _et in edge_types:
    if _et["sourceNodeType"]["alias"] not in _nt_aliases:
        _err.append(f"edgeType {_et['alias']}: source alias not found")
    if _et["destinationNodeType"]["alias"] not in _nt_aliases:
        _err.append(f"edgeType {_et['alias']}: destination alias not found")
_ds_names = {ds["name"] for ds in data_sources["dataSources"]}
for _ntbl in node_tables:
    if _ntbl["dataSourceName"] not in _ds_names:
        _err.append(f"nodeTable: dataSource '{_ntbl['dataSourceName']}' missing")
for _etbl in edge_tables:
    if _etbl["dataSourceName"] not in _ds_names:
        _err.append(f"edgeTable: dataSource '{_etbl['dataSourceName']}' missing")

if _err:
    print("  *** CROSS-REFERENCE ERRORS ***")
    for e in _err:
        print(f"    {e}")
else:
    print("  [OK] All cross-references valid")

# Edge key column summary
print()
print("  Edge key columns:")
for et in edge_tables:
    print(f"    {et['edgeTypeAlias']:30s}  "
          f"src={et['sourceNodeKeyColumns']}  "
          f"dst={et['destinationNodeKeyColumns']}")

gm_parts = [
    encode_part("graphType.json", graph_type),
    encode_part("graphDefinition.json", graph_def),
    encode_part("dataSources.json", data_sources),
    encode_part("stylingConfiguration.json", styling),
    encode_part(".platform", platform),
]
print(f"\n  [OK] {len(gm_parts)} definition parts ready")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# CELL 4 -- Per-Node Validation (test each node individually)
# ============================================================================
# This is the key diagnostic cell. It pushes each node type individually
# to the graph model API to find which specific nodes fail. For any failing
# node, it runs a 12-point root-cause analysis.
# ============================================================================

print("=" * 60)
print("  Step 3: Per-node validation")
print("=" * 60)

# -- Helper: verbose LRO poller --
def _wait_lro(response, label, timeout=120):
    loc = response.headers.get("Location")
    if not loc:
        time.sleep(10)
        return True
    start = time.time()
    retry = int(response.headers.get("Retry-After", 5))
    while time.time() - start < timeout:
        time.sleep(retry)
        t = mssparkutils.credentials.getToken("pbi")
        h = {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}
        r = requests.get(loc, headers=h)
        if r.status_code == 200:
            body = r.json()
            status = body.get("status", "")
            if status == "Succeeded":
                return True
            if status in ("Failed", "Cancelled"):
                err = body.get("error", {})
                print(f"    [{label}] {status}: "
                      f"{err.get('errorCode', err.get('code', ''))} "
                      f"-- {err.get('message', '')[:300]}")
                return False
    print(f"    [{label}] timed out ({timeout}s)")
    return False

# Create/find graph model for testing
# Strategy: prefer auto-provisioned graph (child of ontology) over standalone.
# The Ontology API auto-creates a Graph child item, but never pushes a graph
# definition to it. We find that child and push our 4-part definition to it
# (graphType, graphDefinition, dataSources, stylingConfiguration), which
# triggers the data-loading pipeline. Only create a new standalone graph
# as a fallback if no auto-provisioned graph exists.
token = mssparkutils.credentials.getToken("pbi")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

gm_id = None
auto_provisioned = False

# Step A: Look for auto-provisioned graph (child of ontology)
# Fabric names auto-provisioned graph children as:
#   {OntologyName}_graph_{ontology_id_no_hyphens}
# e.g. Healthcare_Demo_Ontology_HLS_graph_f08d75fd73694abaa7e89bced24d2d12
r = requests.get(GM_API, headers=headers)
if r.status_code == 200:
    all_graphs = r.json().get("value", [])
    # Match by prefix: displayName starts with ontology name + "_graph_"
    for g in all_graphs:
        gname = g.get("displayName", "")
        if gname.startswith(ONTOLOGY_NAME) and "_graph_" in gname:
            gm_id = g["id"]
            auto_provisioned = True
            print(f"  Found auto-provisioned graph: {gm_id}")
            print(f"  Name: {gname}")
            print(f"  (child of ontology '{ONTOLOGY_NAME}' — will push definition to it)")
            break
    # Fallback: check for existing standalone graph
    if not gm_id:
        for g in all_graphs:
            if g.get("displayName") == GRAPH_MODEL_NAME:
                gm_id = g["id"]
                print(f"  Found existing standalone graph: {gm_id}")
                print(f"  (will update definition)")
                break

# Step B: Create standalone graph only if nothing exists
if not gm_id:
    print(f"  No auto-provisioned or existing graph found")
    print(f"  Creating standalone: {GRAPH_MODEL_NAME}")
    cr = requests.post(GM_API, headers=headers, json={
        "displayName": GRAPH_MODEL_NAME,
        "description": f"Graph for {ONTOLOGY_NAME}. "
                       f"{len(node_types)} nodes, {len(edge_types)} edges.",
    })
    if cr.status_code in (200, 201):
        gm_id = cr.json().get("id")
    elif cr.status_code == 202:
        _wait_lro(cr, "create")
        time.sleep(3)
        r2 = requests.get(GM_API, headers=headers)
        for g in r2.json().get("value", []):
            if g["displayName"] == GRAPH_MODEL_NAME:
                gm_id = g["id"]
                break
    if not gm_id:
        raise RuntimeError(f"Failed to create graph model: HTTP {cr.status_code}")
    print(f"  Created: {gm_id}")
    print("  Waiting 60s for backend hydration...")
    time.sleep(60)
else:
    print("  Waiting 15s before pushing definition...")
    time.sleep(15)

update_url = f"{GM_API}/{gm_id}/updateDefinition?updateMetadata=True"

# -- Test each node individually (standalone graphs only) --
# Skip per-node validation for auto-provisioned graphs: the ontology
# deployment already validated all bindings, and pushing single-node
# definitions to a child graph triggers backend errors.
print()
bad_nodes = []
good_nodes = []
fail_reasons = {}

if auto_provisioned:
    print("  [SKIP] Per-node validation -- auto-provisioned graph")
    print("         (ontology deployment already validated all bindings)")
    good_nodes = [nt["alias"].replace("_nodeType", "") for nt in node_types]

elif not auto_provisioned:
  for ni, (nt, ntbl) in enumerate(zip(node_types, node_tables)):
    nds_name = ntbl["dataSourceName"]
    nds = [ds for ds in data_sources["dataSources"] if ds["name"] == nds_name]
    n_gt = {"schemaVersion": "1.0.0", "nodeTypes": [nt], "edgeTypes": []}
    n_gd = {"schemaVersion": "1.0.0", "nodeTables": [ntbl], "edgeTables": []}
    n_ds = {"dataSources": nds}
    n_st = {"schemaVersion": "1.0.0", "modelLayout": {
        "positions": {nt["alias"]: {"x": 300, "y": 300}},
        "styles": {nt["alias"]: {"size": 30}},
        "pan": {"x": 0, "y": 0}, "zoomLevel": 1,
    }}
    n_parts = [
        encode_part("graphType.json", n_gt),
        encode_part("graphDefinition.json", n_gd),
        encode_part("dataSources.json", n_ds),
        encode_part("stylingConfiguration.json", n_st),
        encode_part(".platform", platform),
    ]
    n_body = {"definition": {"format": "json", "parts": n_parts}}
    token = mssparkutils.credentials.getToken("pbi")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    n_r = requests.post(update_url, headers=headers, json=n_body)
    n_label = nt["alias"].replace("_nodeType", "")

    ok = False
    if n_r.status_code in (200, 201):
        ok = True
    elif n_r.status_code == 202:
        ok = _wait_lro(n_r, n_label, timeout=60)
    else:
        fail_reasons[n_label] = [f"HTTP {n_r.status_code}: {n_r.text[:200]}"]

    if ok:
        good_nodes.append(n_label)
        print(f"  [{ni+1:2d}/{len(node_types)}] {n_label:25s} OK")
    else:
        bad_nodes.append(n_label)
        # -- 12-point root-cause analysis --
        reasons = []
        prop_names = {p["name"] for p in nt.get("properties", [])}
        # 1. PK not in properties
        for pk in nt.get("primaryKeyProperties", []):
            if pk not in prop_names:
                reasons.append(f"PK '{pk}' not in properties {sorted(prop_names)}")
        # 2. No PK
        if not nt.get("primaryKeyProperties"):
            reasons.append("No primaryKeyProperties defined")
        # 3. dataSource missing
        if not nds:
            reasons.append(f"dataSource '{nds_name}' not found")
        # 4. Bad table path
        if nds:
            ds_path = nds[0].get("properties", {}).get("path", "")
            if not ds_path:
                reasons.append("dataSource has empty path")
        # 5. Mapping references non-existent property
        for pm in ntbl.get("propertyMappings", []):
            if pm["propertyName"] not in prop_names:
                reasons.append(f"mapping '{pm['propertyName']}' not in nodeType properties")
        # 6. Unknown property type
        valid_types = {"STRING", "INT", "FLOAT", "DATETIME", "BOOLEAN"}
        for p in nt.get("properties", []):
            if p["type"] not in valid_types:
                reasons.append(f"property '{p['name']}' has type '{p['type']}'")
        # 7. Too many properties
        if len(nt.get("properties", [])) > 25:
            reasons.append(f"High property count: {len(nt['properties'])}")
        # 8. Duplicate property names
        pn_list = [p["name"] for p in nt.get("properties", [])]
        pn_dupes = [n for n in set(pn_list) if pn_list.count(n) > 1]
        if pn_dupes:
            reasons.append(f"Duplicate properties: {pn_dupes}")
        # 9. nodeTypeAlias mismatch
        if ntbl["nodeTypeAlias"] != nt["alias"]:
            reasons.append(f"Alias mismatch: {ntbl['nodeTypeAlias']} vs {nt['alias']}")
        # 10. Duplicate mappings
        mp = [pm["propertyName"] for pm in ntbl.get("propertyMappings", [])]
        mp_dupes = [n for n in set(mp) if mp.count(n) > 1]
        if mp_dupes:
            reasons.append(f"Duplicate mappings: {mp_dupes}")
        # 11. Unmapped PK
        for pk in nt.get("primaryKeyProperties", []):
            if pk not in mp:
                reasons.append(f"PK '{pk}' not in propertyMappings")
        # 12. sourceColumn not in actual table
        tbl_name = nds_name.replace("_Source", "")
        try:
            tbl_check = spark.sql(f"DESCRIBE lh_gold_curated.{tbl_name}")
            tbl_cols = {row["col_name"] for row in tbl_check.collect()}
            for pm in ntbl.get("propertyMappings", []):
                if pm["sourceColumn"] not in tbl_cols:
                    reasons.append(f"sourceColumn '{pm['sourceColumn']}' not in {tbl_name}")
        except Exception as te:
            reasons.append(f"Table '{tbl_name}' not accessible: {str(te)[:80]}")

        if not reasons:
            reasons.append("No obvious issue -- may be backend/data problem")
        fail_reasons[n_label] = reasons

        print(f"  [{ni+1:2d}/{len(node_types)}] {n_label:25s} FAIL")
        for r in reasons:
            print(f"         - {r}")

    time.sleep(2)

print(f"\n  Results: {len(good_nodes)} OK, {len(bad_nodes)} FAIL")
if bad_nodes:
    print(f"  Failing: {bad_nodes}")
    print()
    print("  === FAILURE SUMMARY ===")
    for fn, frs in fail_reasons.items():
        print(f"    {fn}:")
        for fr in frs:
            print(f"      - {fr}")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# CELL 5 -- Deploy Full Graph (auto-exclude bad nodes)
# ============================================================================

print("=" * 60)
print("  Step 4: Deploy full graph")
print("=" * 60)

token = mssparkutils.credentials.getToken("pbi")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Rebuild definition excluding bad nodes
if bad_nodes:
    bad_aliases = {f"{n}_nodeType" for n in bad_nodes}
    filt_nt = [nt for nt in node_types if nt["alias"] not in bad_aliases]
    filt_ntbl = [ntbl for ntbl in node_tables if ntbl["nodeTypeAlias"] not in bad_aliases]
    filt_et = [et for et in edge_types
               if et["sourceNodeType"]["alias"] not in bad_aliases
               and et["destinationNodeType"]["alias"] not in bad_aliases]
    filt_etbl = [etbl for etbl in edge_tables
                 if etbl["edgeTypeAlias"] in {et["alias"] for et in filt_et}]
    used_ds = ({ntbl["dataSourceName"] for ntbl in filt_ntbl}
               | {etbl["dataSourceName"] for etbl in filt_etbl})
    filt_ds = {"dataSources": [ds for ds in data_sources["dataSources"]
                               if ds["name"] in used_ds]}
    filt_pos = {a: positions[a] for a in positions if a not in bad_aliases}
    filt_styles = {a: styles[a] for a in styles
                   if a in ({nt["alias"] for nt in filt_nt} | {et["alias"] for et in filt_et})}
    filt_styling = {"schemaVersion": "1.0.0", "modelLayout": {
        "positions": filt_pos, "styles": filt_styles,
        "pan": {"x": 0, "y": 0}, "zoomLevel": 1}}
    filt_gt = {"schemaVersion": "1.0.0", "nodeTypes": filt_nt, "edgeTypes": filt_et}
    filt_gd = {"schemaVersion": "1.0.0", "nodeTables": filt_ntbl, "edgeTables": filt_etbl}
    deploy_parts = [
        encode_part("graphType.json", filt_gt),
        encode_part("graphDefinition.json", filt_gd),
        encode_part("dataSources.json", filt_ds),
        encode_part("stylingConfiguration.json", filt_styling),
        encode_part(".platform", platform),
    ]
    print(f"  Rebuilt excluding {bad_nodes}: "
          f"{len(filt_nt)} nodes, {len(filt_et)} edges")
else:
    deploy_parts = gm_parts
    print(f"  Full graph: {len(node_types)} nodes, {len(edge_types)} edges")

body = {"definition": {"format": "json", "parts": deploy_parts}}
gm_success = False

for attempt in range(3):
    token = mssparkutils.credentials.getToken("pbi")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    print(f"  Push attempt {attempt + 1}/3...")
    r = requests.post(update_url, headers=headers, json=body)

    if r.status_code in (200, 201):
        gm_success = True
        print("  [OK] Definition pushed")
        break
    elif r.status_code == 202:
        ok = _wait_lro(r, "updateDefinition", timeout=300)
        if ok:
            gm_success = True
            print("  [OK] Definition pushed (async)")
            break
        print(f"  Attempt {attempt + 1} failed")
    else:
        print(f"  HTTP {r.status_code}: {r.text[:300]}")

    if attempt < 2:
        wait = 60 * (attempt + 1)
        print(f"  Retrying in {wait}s...")
        time.sleep(wait)

# Fallback: 4-part (without .platform)
if not gm_success:
    print("  Trying 4-part fallback (without .platform)...")
    parts_4 = [p for p in deploy_parts if p["path"] != ".platform"]
    url_4 = f"{GM_API}/{gm_id}/updateDefinition"
    body_4 = {"definition": {"format": "json", "parts": parts_4}}
    r = requests.post(url_4, headers=headers, json=body_4)
    if r.status_code in (200, 201):
        gm_success = True
    elif r.status_code == 202:
        gm_success = _wait_lro(r, "4-part push", timeout=300)
    if gm_success:
        print("  [OK] 4-part fallback succeeded")
    else:
        print("  [FAIL] All attempts failed")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# CELL 6 -- Wait for Data Load & Smoke Test
# ============================================================================

print("=" * 60)
print("  Step 5: Data load & smoke test")
print("=" * 60)

if gm_id and gm_success:
    print("  Waiting for data load...")
    for poll in range(60):
        token = mssparkutils.credentials.getToken("pbi")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        r = requests.get(f"{GM_API}/{gm_id}", headers=headers)
        if r.status_code == 200:
            props = r.json().get("properties", {})
            readiness = props.get("queryReadiness", "")
            status = (props.get("lastDataLoadingStatus") or {}).get("status", "")
            if readiness == "Full" or status == "Completed":
                print(f"  [OK] Data loaded (queryReadiness={readiness})")
                break
            if status == "Failed":
                print("  [WARN] Data load failed -- check Fabric UI")
                break
            if poll % 6 == 0:
                print(f"    readiness={readiness}, status={status}...")
        time.sleep(5)

    # Smoke test: GQL query
    print()
    print("  Running smoke test...")
    token = mssparkutils.credentials.getToken("pbi")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    query_url = f"{GM_API}/{gm_id}/executeQuery?beta=True"

    queries = [
        ("Patient count", "MATCH (p:Patient) RETURN COUNT(p) AS cnt;"),
        ("Provider count", "MATCH (p:Provider) RETURN COUNT(p) AS cnt;"),
        ("Edge count", "MATCH ()-[r]->() RETURN COUNT(r) AS cnt;"),
    ]
    for label, gql in queries:
        r = requests.post(query_url, headers=headers, json={"query": gql})
        if r.status_code == 200:
            result = r.json()
            if result.get("status", {}).get("code") == "00000":
                data = result.get("result", {}).get("data", [])
                cnt = data[0].get("cnt", "?") if data else "?"
                print(f"    {label:20s}: {cnt}")
            else:
                desc = result.get("status", {}).get("description", "")
                print(f"    {label:20s}: query error -- {desc[:100]}")
        else:
            print(f"    {label:20s}: HTTP {r.status_code}")

# -- Summary --
print()
print("=" * 60)
graph_status = "[OK]" if gm_success else "[FAIL]"
total_nodes = len(good_nodes)
total_edges = len(edge_types) if not bad_nodes else len([
    et for et in edge_types
    if et["sourceNodeType"]["alias"].replace("_nodeType", "") not in bad_nodes
    and et["destinationNodeType"]["alias"].replace("_nodeType", "") not in bad_nodes
])
print(f"  GRAPH:  {GRAPH_MODEL_NAME:<40} {graph_status}")
print(f"  NODES:  {total_nodes}/{len(node_types)} passed validation")
print(f"  EDGES:  {total_edges} deployed")
if bad_nodes:
    print(f"  EXCLUDED: {bad_nodes}")
    print()
    print("  To fix excluded nodes:")
    print("    1. Check the ontology bindings match actual table columns")
    print("    2. Re-deploy ontology (Cell 10a in Healthcare_Launcher)")
    print("    3. Re-run this notebook")
print("=" * 60)

if not gm_success:
    raise RuntimeError("Graph model deployment failed")
