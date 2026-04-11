"""
Deploy Ontology to Microsoft Fabric
=====================================
Reads the ontology definition from ontology/ and deploys it to a target
Fabric workspace via the Ontology REST API.

The ontology binds to Gold tables in lh_gold_curated (schema-less lakehouse).
The script automatically patches workspace/lakehouse GUIDs in data binding
files so the ontology points to the correct target environment.

Prerequisites:
  1. lh_gold_curated exists (created by the launcher)
  2. Gold tables are populated (ETL pipeline has run at least once)
  3. pip install azure-identity requests

Usage:
    python scripts/deploy_ontology.py
    python scripts/deploy_ontology.py --workspace "My-Workspace"
    python scripts/deploy_ontology.py --update
"""

import sys
import os
import json
import base64
import re
import argparse
import requests
from pathlib import Path

# Add scripts/ to path for client imports
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from fabric_auth import get_fabric_token, get_auth_headers
from clients.ontology_client import OntologyClient
from clients.graph_client import GraphModelClient
from clients.graph_definition_builder import GraphDefinitionBuilder

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ============================================================
# CONFIGURATION
# ============================================================
FABRIC_API_BASE = "https://api.fabric.microsoft.com/v1"
ONTOLOGY_NAME = "Healthcare_Demo_Ontology_HLS"
GRAPH_MODEL_NAME = "Healthcare_Demo_Graph"
LAKEHOUSE_NAME = "lh_gold_curated"
FOLDER_NAME = "Ontologies"
ONTOLOGY_DIR = SCRIPT_DIR.parent / "ontology" / ONTOLOGY_NAME


# ============================================================
# WORKSPACE HELPERS
# ============================================================

def get_workspace_id(token, workspace_name):
    url = f"{FABRIC_API_BASE}/workspaces"
    resp = requests.get(url, headers=get_auth_headers(token))
    resp.raise_for_status()
    for ws in resp.json().get("value", []):
        if ws["displayName"] == workspace_name:
            return ws["id"]
    available = [w["displayName"] for w in resp.json().get("value", [])]
    print(f"  [FAIL] Workspace '{workspace_name}' not found")
    print(f"    Available: {available}")
    sys.exit(1)


def get_lakehouse_id(token, workspace_id, lakehouse_name):
    url = f"{FABRIC_API_BASE}/workspaces/{workspace_id}/lakehouses"
    resp = requests.get(url, headers=get_auth_headers(token))
    if resp.status_code != 200:
        return None
    for lh in resp.json().get("value", []):
        if lh["displayName"] == lakehouse_name:
            return lh["id"]
    return None


def get_or_create_folder(token, workspace_id, folder_name):
    headers = get_auth_headers(token)
    url = f"{FABRIC_API_BASE}/workspaces/{workspace_id}/folders"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        for folder in response.json().get("value", []):
            if folder["displayName"] == folder_name:
                return folder["id"]
    payload = {"displayName": folder_name}
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code in (200, 201):
        return response.json()["id"]
    elif response.status_code == 409:
        resp2 = requests.get(url, headers=headers)
        if resp2.status_code == 200:
            for folder in resp2.json().get("value", []):
                if folder["displayName"] == folder_name:
                    return folder["id"]
    return None


# ============================================================
# DATA BINDING PATCHING
# ============================================================

def patch_data_bindings(parts, target_workspace_id, target_lakehouse_id):
    """Patch workspace/lakehouse GUIDs in data binding files."""
    patched_parts = []
    for part in parts:
        part_path = part.get("path", "")
        payload = part.get("payload", "")
        payload_type = part.get("payloadType", "InlineBase64")
        needs_patching = (
            "DataBindings" in part_path or
            "Contextualizations" in part_path or
            part_path == ".platform"
        )
        if needs_patching and payload_type == "InlineBase64" and payload:
            try:
                content = base64.b64decode(payload).decode("utf-8")
                if "DataBindings" in part_path or "Contextualizations" in part_path:
                    content = _patch_binding_content(
                        content, target_workspace_id, target_lakehouse_id
                    )
                payload = base64.b64encode(content.encode("utf-8")).decode("utf-8")
            except Exception as e:
                print(f"    [WARN] Could not patch {part_path}: {e}")
        patched_parts.append({
            "path": part_path,
            "payload": payload,
            "payloadType": payload_type,
        })
    return patched_parts


def _patch_binding_content(content, target_workspace_id, target_lakehouse_id):
    try:
        binding = json.loads(content)
        _patch_binding_obj(binding, target_workspace_id, target_lakehouse_id)
        return json.dumps(binding, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        return content


def _patch_binding_obj(obj, workspace_id, lakehouse_id):
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            val = obj[key]
            lower_key = key.lower()
            if lower_key in ("workspaceid", "workspaceguid", "workspace_id"):
                obj[key] = workspace_id
            elif lower_key in ("lakehouseid", "artifactid", "lakehouse_id",
                               "artifact_id", "itemid", "item_id"):
                obj[key] = lakehouse_id
            elif isinstance(val, str) and "onelake" in val.lower():
                patched = _patch_onelake_path(val, workspace_id, lakehouse_id)
                if patched != val:
                    obj[key] = patched
            elif isinstance(val, (dict, list)):
                _patch_binding_obj(val, workspace_id, lakehouse_id)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                _patch_binding_obj(item, workspace_id, lakehouse_id)


def _patch_onelake_path(path, workspace_id, lakehouse_id):
    abfss_match = re.match(
        r'(abfss://)([0-9a-f-]+)(@onelake\.dfs\.fabric\.microsoft\.com/)([0-9a-f-]+)(.*)',
        path, re.IGNORECASE
    )
    if abfss_match:
        return (f"{abfss_match.group(1)}{workspace_id}"
                f"{abfss_match.group(3)}{lakehouse_id}"
                f"{abfss_match.group(5)}")
    return path


# ============================================================
# LOAD ONTOLOGY FROM DISK
# ============================================================

def load_ontology_parts(ontology_dir):
    manifest_path = ontology_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"  [FAIL] No manifest.json found in {ontology_dir}")
        sys.exit(1)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    parts = []
    for part_info in manifest.get("exportedParts", []):
        part_path = part_info["path"]
        file_path = ontology_dir / part_path
        if not file_path.exists():
            print(f"  [WARN] Missing file: {file_path}")
            continue
        raw = file_path.read_bytes()
        if raw.startswith(b'\xef\xbb\xbf'):
            raw = raw[3:]
        payload_b64 = base64.b64encode(raw).decode("utf-8")
        parts.append({
            "path": part_path,
            "payload": payload_b64,
            "payloadType": "InlineBase64",
        })
    print(f"  Loaded {len(parts)} part(s) from {ontology_dir.name}")
    return parts


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Deploy Ontology to Fabric")
    parser.add_argument("--workspace", required=True,
                        help="Target workspace name")
    parser.add_argument("--tenant-id", required=True,
                        help="Azure AD tenant ID")
    parser.add_argument("--account", default=None,
                        help="Login hint (email)")
    parser.add_argument("--ontology", default=ONTOLOGY_NAME,
                        help=f"Ontology name (default: {ONTOLOGY_NAME})")
    parser.add_argument("--update", action="store_true",
                        help="Update existing ontology definition")
    parser.add_argument("--skip-graph", action="store_true",
                        help="Skip automatic graph model deployment")
    parser.add_argument("--graph-model", default=GRAPH_MODEL_NAME,
                        help=f"Graph model name (default: {GRAPH_MODEL_NAME})")
    args = parser.parse_args()

    ontology_dir = SCRIPT_DIR.parent / "ontology" / args.ontology

    print("=" * 70)
    print("  DEPLOY ONTOLOGY TO FABRIC")
    print("=" * 70)
    print(f"  Target Workspace: {args.workspace}")
    print(f"  Ontology Name:    {args.ontology}")
    print(f"  Source:           {ontology_dir}")
    print(f"  Lakehouse:        {LAKEHOUSE_NAME}")
    print(f"  Mode:             {'Update' if args.update else 'Create'}")
    print()

    if not ontology_dir.exists():
        print(f"  [FAIL] Ontology directory not found: {ontology_dir}")
        sys.exit(1)

    # Step 1: Authenticate
    print("Step 1: Authenticating...")
    token = get_fabric_token(args.tenant_id, args.account)
    client = OntologyClient(token)
    print()

    # Step 2: Resolve workspace
    print("Step 2: Finding workspace...")
    workspace_id = get_workspace_id(token, args.workspace)
    print(f"  [OK] Workspace ID: {workspace_id}")
    print()

    # Step 3: Resolve lakehouse
    print("Step 3: Finding target lakehouse...")
    lakehouse_id = get_lakehouse_id(token, workspace_id, LAKEHOUSE_NAME)
    if lakehouse_id:
        print(f"  [OK] {LAKEHOUSE_NAME}: {lakehouse_id}")
    else:
        print(f"  [WARN] {LAKEHOUSE_NAME} not found — data bindings may fail")
        lakehouse_id = "PLACEHOLDER-LAKEHOUSE-ID"
    print()

    # Step 4: Load from disk
    print("Step 4: Loading ontology definition...")
    parts = load_ontology_parts(ontology_dir)
    if not parts:
        print("  [FAIL] No definition parts loaded")
        sys.exit(1)
    print()

    # Step 5: Patch data bindings
    print("Step 5: Patching data bindings...")
    parts = patch_data_bindings(parts, workspace_id, lakehouse_id)
    print(f"  [OK] Patching complete")
    print()

    # Step 6: Create folder
    print("Step 6: Creating workspace folder...")
    folder_id = get_or_create_folder(token, workspace_id, FOLDER_NAME)
    print()

    # Step 7: Deploy
    existing = client.find_by_name(workspace_id, args.ontology)
    description = (
        f"Healthcare Ontology — 12 entity types, 18 relationships, "
        f"bound to {LAKEHOUSE_NAME}"
    )

    print("Step 7: Deploying...")
    if existing and args.update:
        ok = client.update_definition(workspace_id, existing["id"], parts)
        result = "[OK] Updated" if ok else "[FAIL] Update failed"
    elif existing and not args.update:
        print(f"  Already exists: {args.ontology} (use --update to overwrite)")
        result = "[SKIP] Already exists"
    else:
        item_id = client.create(workspace_id, args.ontology, description,
                                parts, folder_id)
        if item_id:
            ok = client.update_definition(workspace_id, item_id, parts)
            result = "[OK] Created + definition applied" if ok else "[WARN] Created but update failed"
        else:
            result = "[FAIL] Create failed"

    # Step 8: Verify
    print()
    verified = client.find_by_name(workspace_id, args.ontology)
    if verified:
        print(f"  [OK] Verified: {verified['displayName']} ({verified['id']})")

    print()
    print("=" * 70)
    print(f"  ONTOLOGY: {args.ontology:<42} {result}")
    print("=" * 70)

    if "FAIL" in result:
        sys.exit(1)

    # ── Step 9: Auto-deploy Graph Model ───────────────────────
    # The Fabric API does NOT auto-provision a graph model when you
    # create an ontology programmatically (unlike the Fabric UI).
    # So we chain the graph model deployment here automatically.
    if args.skip_graph:
        print()
        print("  --skip-graph: Skipping graph model deployment.")
        print(f"  To deploy later: python scripts/deploy_graph_model.py "
              f"--workspace \"{args.workspace}\" --tenant-id \"{args.tenant_id}\"")
        print()
        return

    print()
    print("=" * 70)
    print("  DEPLOYING GRAPH MODEL (auto-provisioned for ontology)")
    print("=" * 70)
    print()
    print("  NOTE: The Fabric REST API does not auto-provision a graph model")
    print("  underneath the ontology (unlike the Fabric UI). Deploying now...")
    print()

    graph_client = GraphModelClient(token)
    builder = GraphDefinitionBuilder(ontology_dir, workspace_id, lakehouse_id)

    print("  Step 9a: Parsing ontology metadata for graph definition...")
    builder.load_ontology()

    entities = builder.entities
    relationships = builder.relationships

    print("\n  Step 9b: Generating graph model definition parts...")
    graph_description = (
        f"Graph model for {args.ontology}. "
        f"{len(entities)} node types, {len(relationships)} edge types, "
        f"bound to {LAKEHOUSE_NAME} delta tables."
    )
    graph_parts = builder.build_all_parts(
        display_name=args.graph_model,
        description=graph_description,
    )

    print(f"\n  Step 9c: Deploying graph model '{args.graph_model}'...")
    existing_graph = graph_client.find_by_name(workspace_id, args.graph_model)
    graph_result = ""
    gm_id = None

    if existing_graph and args.update:
        gm_id = existing_graph["id"]
        ok = graph_client.update_definition(workspace_id, gm_id, graph_parts)
        graph_result = "[OK] Updated" if ok else "[FAIL] Update failed"
    elif existing_graph and not args.update:
        gm_id = existing_graph["id"]
        print(f"    Already exists: {args.graph_model} (use --update to overwrite)")
        graph_result = "[SKIP] Already exists"
    else:
        folder_id_for_graph = get_or_create_folder(token, workspace_id, FOLDER_NAME)
        gm_id = graph_client.create(
            workspace_id, args.graph_model, graph_description,
            definition_parts=graph_parts, folder_id=folder_id_for_graph,
        )
        if gm_id:
            graph_result = f"[OK] Created ({gm_id})"
        else:
            graph_result = "[FAIL] Create failed"
            gm_id = None

    # Wait for data load
    if gm_id and "FAIL" not in graph_result and "SKIP" not in graph_result:
        print(f"\n  Step 9d: Waiting for graph data load...")
        loaded = graph_client.wait_for_data_load(workspace_id, gm_id, timeout=600)
        if loaded:
            graph_result += " + data loaded"
        else:
            print(f"    [WARN] Data load incomplete — check Fabric UI job history")

    # Verify
    if gm_id and "FAIL" not in graph_result and "SKIP" not in graph_result:
        schema = graph_client.get_queryable_graph_type(workspace_id, gm_id)
        if schema:
            nt = schema.get("nodeTypes", [])
            et = schema.get("edgeTypes", [])
            print(f"    Queryable: {len(nt)} node types, {len(et)} edge types")

    print()
    print("=" * 70)
    print(f"  ONTOLOGY:    {args.ontology:<38} {result}")
    print(f"  GRAPH MODEL: {args.graph_model:<38} {graph_result}")
    print("=" * 70)
    print()

    if "FAIL" in graph_result:
        sys.exit(1)


if __name__ == "__main__":
    main()
