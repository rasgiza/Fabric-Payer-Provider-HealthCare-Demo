"""
Convert Healthcare-Data-Analytics-Repo artifacts to fabric-cicd format
=====================================================================

This script reads the FabricDemoHLS/ source artifacts and generates a
workspace/ folder compatible with fabric-cicd / fabric-launcher deployment.

Run once after cloning Healthcare-Data-Analytics-Repo, then commit the output.
Re-run whenever source notebooks, pipelines, or other artifacts change.

Usage:
    python scripts/convert_from_source.py --source ../Healthcare-Data-Analytics-Repo/FabricDemoHLS
"""

import os
import sys
import json
import uuid
import re
import shutil
import base64
import argparse
from pathlib import Path
from html import unescape


# ============================================================
# MASTER GUID MAPPING
# ============================================================
# These logicalIds are used consistently across ALL artifacts
# for cross-item references. fabric-cicd resolves them to real
# workspace item IDs at deploy time.

LOGICAL_IDS = {
    # Lakehouses
    "lh_bronze_raw":                    "a1000001-0001-0001-0001-000000000001",
    "lh_silver_stage":                  "a1000001-0001-0001-0001-000000000002",
    "lh_silver_ods":                    "a1000001-0001-0001-0001-000000000003",
    "lh_gold_curated":                  "a1000001-0001-0001-0001-000000000004",
    # Notebooks
    "01_Bronze_Ingest_CSV":             "b2000002-0002-0002-0002-000000000001",
    "02_Silver_Stage_Clean":            "b2000002-0002-0002-0002-000000000002",
    "03_Silver_ODS_Enrich":             "b2000002-0002-0002-0002-000000000003",
    "06a_Create_Gold_Lakehouse_Tables": "b2000002-0002-0002-0002-000000000004",
    "06b_Gold_Transform_Load_v2":       "b2000002-0002-0002-0002-000000000005",
    "NB_Generate_Sample_Data":          "b2000002-0002-0002-0002-000000000006",
    "NB_Generate_Incremental_Data":     "b2000002-0002-0002-0002-000000000007",
    # Pipelines
    "PL_Healthcare_Full_Load":          "c3000003-0003-0003-0003-000000000001",
    "PL_Healthcare_Master":             "c3000003-0003-0003-0003-000000000002",
    # Semantic Model
    "HealthcareDemoHLS":                "d4000004-0004-0004-0004-000000000001",
    # Data Agent
    "HealthcareHLSAgent":               "e5000005-0005-0005-0005-000000000001",
}

# Notebook → default lakehouse mapping
NOTEBOOK_LAKEHOUSES = {
    "01_Bronze_Ingest_CSV":             "lh_bronze_raw",
    "02_Silver_Stage_Clean":            "lh_silver_stage",
    "03_Silver_ODS_Enrich":             "lh_silver_ods",
    "06a_Create_Gold_Lakehouse_Tables": "lh_gold_curated",
    "06b_Gold_Transform_Load_v2":       "lh_gold_curated",
    "NB_Generate_Sample_Data":          "lh_bronze_raw",
    "NB_Generate_Incremental_Data":     "lh_bronze_raw",
}

# Notebook → additional known lakehouses (cross-references)
NOTEBOOK_KNOWN_LAKEHOUSES = {
    "01_Bronze_Ingest_CSV":             [],
    "02_Silver_Stage_Clean":            ["lh_bronze_raw"],
    "03_Silver_ODS_Enrich":             ["lh_bronze_raw", "lh_silver_stage"],
    "06a_Create_Gold_Lakehouse_Tables": [],
    "06b_Gold_Transform_Load_v2":       ["lh_silver_ods", "lh_bronze_raw"],
    "NB_Generate_Sample_Data":          [],
    "NB_Generate_Incremental_Data":     [],
}

# Pipeline notebook references (activity name → notebook name)
PIPELINE_NOTEBOOK_MAP = {
    "PL_Healthcare_Full_Load": {
        "Bronze_Ingest":      "01_Bronze_Ingest_CSV",
        "Silver_Stage_Clean": "02_Silver_Stage_Clean",
        "Silver_ODS_Enrich":  "03_Silver_ODS_Enrich",
        "Gold_Star_Schema":   "06b_Gold_Transform_Load_v2",
    },
    "PL_Healthcare_Master": {},
}

# Pipeline cross-pipeline references (activity name → pipeline name)
PIPELINE_PIPELINE_MAP = {
    "PL_Healthcare_Master": {
        "Execute_Full_Load":        "PL_Healthcare_Full_Load",
        "Execute_Incremental_Load": "PL_Healthcare_Full_Load",
    },
    "PL_Healthcare_Full_Load": {},
}

PLATFORM_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json"


# ============================================================
# HELPER: Create .platform file
# ============================================================

def create_platform_file(item_type, display_name, logical_id):
    return json.dumps({
        "$schema": PLATFORM_SCHEMA,
        "metadata": {
            "type": item_type,
            "displayName": display_name
        },
        "config": {
            "version": "2.0",
            "logicalId": logical_id
        }
    }, indent=2)


# ============================================================
# CONVERT: Lakehouses (minimal .platform only)
# ============================================================

def convert_lakehouses(output_dir):
    print("\n=== Converting Lakehouses ===")
    lakehouses = ["lh_bronze_raw", "lh_silver_stage", "lh_silver_ods", "lh_gold_curated"]

    for lh_name in lakehouses:
        folder = output_dir / f"{lh_name}.Lakehouse"
        folder.mkdir(parents=True, exist_ok=True)

        platform = create_platform_file("Lakehouse", lh_name, LOGICAL_IDS[lh_name])
        (folder / ".platform").write_text(platform, encoding="utf-8")
        print(f"  [OK] {lh_name}.Lakehouse/")


# ============================================================
# CONVERT: Notebooks (VSCode XML → Fabric notebook-content.py)
# ============================================================

def parse_vscode_notebook(file_path):
    """Parse standard .ipynb JSON files into a list of cells."""
    raw = file_path.read_text(encoding="utf-8-sig")
    notebook = json.loads(raw)
    cells = []

    for i, cell in enumerate(notebook.get("cells", [])):
        cell_type = cell.get("cell_type", "code")
        cell_id = cell.get("id", f"cell_{i}")

        # Source can be a list of lines or a single string
        source = cell.get("source", [])
        if isinstance(source, list):
            cell_content = "".join(source)
        else:
            cell_content = source

        # Strip trailing whitespace/newlines
        cell_content = cell_content.rstrip()

        language = "markdown" if cell_type == "markdown" else "python"

        cells.append({
            "id": cell_id,
            "type": cell_type,
            "language": language,
            "content": cell_content
        })

    return cells


def cells_to_fabric_notebook_py(cells, notebook_name):
    """
    Convert parsed cells to Fabric notebook-content.py format.

    Fabric Git Integration format:
    - First line: # Fabric notebook source
    - Then for each cell:
      # METADATA **{"type": "code"/"markdown"}**
      # CELL **{"type": "code"/"markdown"}**
      <content>
    """
    lines = ["# Fabric notebook source"]

    for cell in cells:
        cell_type = cell["type"]

        # Metadata line
        lines.append("")
        lines.append(f'# METADATA **{{"language":"{cell["language"]}"}}**')
        lines.append("")

        if cell_type == "markdown":
            lines.append(f'# MARKDOWN **{{"language":"markdown"}}**')
            lines.append("")
            # Prefix each line with #
            for line in cell["content"].split("\n"):
                lines.append(f"# {line}")
        else:
            lines.append(f'# CELL **{{"language":"{cell["language"]}"}}**')
            lines.append("")
            lines.append(cell["content"])

    return "\n".join(lines) + "\n"


def build_notebook_metadata(notebook_name):
    """
    Build the lakehouse dependency metadata for a notebook.
    This tells Fabric which lakehouse is the default and which others are known.
    """
    default_lh = NOTEBOOK_LAKEHOUSES.get(notebook_name)
    known_lhs = NOTEBOOK_KNOWN_LAKEHOUSES.get(notebook_name, [])

    if not default_lh:
        return None

    # Build the lakehouse list (default + known)
    all_lakehouses = [default_lh] + [lh for lh in known_lhs if lh != default_lh]

    lakehouses_config = []
    for lh in all_lakehouses:
        lh_config = {
            "id": LOGICAL_IDS[lh],
            "displayName": lh,
            "isDefault": lh == default_lh
        }
        lakehouses_config.append(lh_config)

    return {
        "dependencies": {
            "lakehouse": {
                "default_lakehouse": LOGICAL_IDS[default_lh],
                "default_lakehouse_name": default_lh,
                "default_lakehouse_workspace_id": "00000000-0000-0000-0000-000000000000",
                "known_lakehouses": lakehouses_config
            }
        }
    }


def convert_notebooks(source_dir, output_dir):
    print("\n=== Converting Notebooks ===")
    notebooks_dir = source_dir / "notebooks"

    # These are the ETL notebooks to convert
    notebook_files = [
        "01_Bronze_Ingest_CSV.ipynb",
        "02_Silver_Stage_Clean.ipynb",
        "03_Silver_ODS_Enrich.ipynb",
        "06a_Create_Gold_Lakehouse_Tables.ipynb",
        "06b_Gold_Transform_Load_v2.ipynb",
    ]

    for nb_file in notebook_files:
        nb_path = notebooks_dir / nb_file
        nb_name = nb_file.replace(".ipynb", "")

        if not nb_path.exists():
            print(f"  [SKIP] {nb_file} not found")
            continue

        # Parse cells
        cells = parse_vscode_notebook(nb_path)
        print(f"  Parsing {nb_file}: {len(cells)} cells")

        # Convert to notebook-content.py
        py_content = cells_to_fabric_notebook_py(cells, nb_name)

        # Create output folder
        folder = output_dir / f"{nb_name}.Notebook"
        folder.mkdir(parents=True, exist_ok=True)

        # Write .platform
        platform = create_platform_file("Notebook", nb_name, LOGICAL_IDS[nb_name])
        (folder / ".platform").write_text(platform, encoding="utf-8")

        # Write notebook-content.py
        (folder / "notebook-content.py").write_text(py_content, encoding="utf-8")

        # Write notebook metadata (lakehouse bindings)
        metadata = build_notebook_metadata(nb_name)
        if metadata:
            meta_dir = folder / ".metadata"
            meta_dir.mkdir(exist_ok=True)
            (meta_dir / "notebook-metadata.json").write_text(
                json.dumps(metadata, indent=2), encoding="utf-8"
            )

        print(f"  [OK] {nb_name}.Notebook/ ({len(cells)} cells)")


# ============================================================
# CONVERT: Pipelines (custom JSON → fabric-cicd format)
# ============================================================

def convert_pipelines(source_dir, output_dir):
    print("\n=== Converting Pipelines ===")
    pipelines_dir = source_dir / "pipelines"

    pipeline_files = [
        "PL_Healthcare_Full_Load.json",
        "PL_Healthcare_Master.json",
    ]

    for pl_file in pipeline_files:
        pl_path = pipelines_dir / pl_file
        pl_name = pl_file.replace(".json", "")

        if not pl_path.exists():
            print(f"  [SKIP] {pl_file} not found")
            continue

        # Read source pipeline
        raw = json.loads(pl_path.read_text(encoding="utf-8-sig"))

        # Extract core properties (strip __deploy_config__ and other wrappers)
        properties = raw.get("properties", raw)

        # Patch notebook references
        nb_map = PIPELINE_NOTEBOOK_MAP.get(pl_name, {})
        pl_map = PIPELINE_PIPELINE_MAP.get(pl_name, {})

        def patch_activities(activities):
            """Recursively patch notebook and pipeline references in activities."""
            for activity in activities:
                act_name = activity.get("name", "")
                act_type = activity.get("type", "")
                type_props = activity.get("typeProperties", {})

                if act_type == "TridentNotebook":
                    # Patch notebookId
                    target_nb = nb_map.get(act_name)
                    if target_nb and target_nb in LOGICAL_IDS:
                        type_props["notebookId"] = LOGICAL_IDS[target_nb]
                        print(f"    Patched {act_name} → notebook {target_nb}")
                    # Remove workspaceId (fabric-cicd handles this)
                    if "workspaceId" in type_props:
                        del type_props["workspaceId"]

                elif act_type == "ExecutePipeline":
                    # Patch pipeline reference
                    target_pl = pl_map.get(act_name)
                    if target_pl and target_pl in LOGICAL_IDS:
                        pipeline_ref = type_props.get("pipeline", {})
                        pipeline_ref["referenceName"] = LOGICAL_IDS[target_pl]
                        print(f"    Patched {act_name} → pipeline {target_pl}")

                # Recurse into IfCondition branches
                if act_type == "IfCondition":
                    if_props = activity.get("typeProperties", {})
                    patch_activities(if_props.get("ifTrueActivities", []))
                    patch_activities(if_props.get("ifFalseActivities", []))

        all_activities = properties.get("activities", [])
        patch_activities(all_activities)

        # Build pipeline-content.json (fabric-cicd format)
        pipeline_content = {"properties": properties}

        # Create output folder
        folder = output_dir / f"{pl_name}.DataPipeline"
        folder.mkdir(parents=True, exist_ok=True)

        # Write .platform
        platform = create_platform_file("DataPipeline", pl_name, LOGICAL_IDS[pl_name])
        (folder / ".platform").write_text(platform, encoding="utf-8")

        # Write pipeline-content.json
        (folder / "pipeline-content.json").write_text(
            json.dumps(pipeline_content, indent=4, ensure_ascii=False),
            encoding="utf-8"
        )

        print(f"  [OK] {pl_name}.DataPipeline/")


# ============================================================
# CONVERT: Semantic Model (copy + patch GUIDs)
# ============================================================

def convert_semantic_model(source_dir, output_dir):
    print("\n=== Converting Semantic Model ===")
    sm_name = "HealthcareDemoHLS"
    src_dir = source_dir / "semantic_models" / sm_name
    dst_dir = output_dir / f"{sm_name}.SemanticModel"

    if not src_dir.exists():
        print(f"  [SKIP] {src_dir} not found")
        return

    # Copy entire folder (handle OneDrive locks)
    if dst_dir.exists():
        try:
            shutil.rmtree(dst_dir)
        except PermissionError:
            print(f"  [WARN] Could not clean {dst_dir.name}, merging instead")
    shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)

    # Update .platform logicalId
    platform_path = dst_dir / ".platform"
    platform = json.loads(platform_path.read_text(encoding="utf-8-sig"))
    platform["config"]["logicalId"] = LOGICAL_IDS[sm_name]
    platform_path.write_text(json.dumps(platform, indent=2), encoding="utf-8")

    # Patch expressions.tmdl — replace hardcoded OneLake GUIDs with lakehouse logicalId
    expr_path = dst_dir / "definition" / "expressions.tmdl"
    if expr_path.exists():
        content = expr_path.read_text(encoding="utf-8-sig")

        # The expression contains:
        # AzureStorage.DataLake("https://onelake.dfs.fabric.microsoft.com/WORKSPACE_GUID/LAKEHOUSE_GUID", ...)
        # Replace both GUIDs with logicalIds that fabric-cicd will resolve
        guid_pattern = re.compile(
            r'(https://onelake\.dfs\.fabric\.microsoft\.com/)([0-9a-f-]{36})/([0-9a-f-]{36})',
            re.IGNORECASE
        )

        def replace_onelake(match):
            return f"{match.group(1)}{LOGICAL_IDS['lh_gold_curated']}/{LOGICAL_IDS['lh_gold_curated']}"

        new_content = guid_pattern.sub(replace_onelake, content)

        if new_content != content:
            expr_path.write_text(new_content, encoding="utf-8")
            print(f"  Patched expressions.tmdl with logicalIds")
        else:
            # The GUIDs might already be 00000000-... placeholder format
            # Try patching those too
            zero_pattern = re.compile(
                r'(https://onelake\.dfs\.fabric\.microsoft\.com/)([0-9a-f-]{36})/([0-9a-f-]{36})',
                re.IGNORECASE
            )
            new_content = zero_pattern.sub(replace_onelake, content)
            expr_path.write_text(new_content, encoding="utf-8")
            print(f"  Patched expressions.tmdl (from placeholders)")

    print(f"  [OK] {sm_name}.SemanticModel/")


# ============================================================
# CONVERT: Data Agent (copy + update logicalId)
# ============================================================

def convert_data_agent(source_dir, output_dir):
    print("\n=== Converting Data Agent ===")
    da_name = "HealthcareHLSAgent"
    src_dir = source_dir / "data_agents" / da_name
    dst_dir = output_dir / f"{da_name}.DataAgent"

    if not src_dir.exists():
        print(f"  [SKIP] {src_dir} not found")
        return

    # Copy entire folder (handle OneDrive locks)
    if dst_dir.exists():
        try:
            shutil.rmtree(dst_dir)
        except PermissionError:
            print(f"  [WARN] Could not clean {dst_dir.name}, merging instead")
    shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)

    # Update .platform logicalId
    platform_path = dst_dir / ".platform"
    platform = json.loads(platform_path.read_text(encoding="utf-8-sig"))
    platform["config"]["logicalId"] = LOGICAL_IDS[da_name]
    platform_path.write_text(json.dumps(platform, indent=2), encoding="utf-8")

    # Patch datasource.json files — replace artifact GUIDs with logicalIds
    # These files reference lh_gold_curated and HealthcareDemoHLS
    guid_pattern = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.IGNORECASE)

    for ds_file in dst_dir.rglob("datasource.json"):
        content = ds_file.read_text(encoding="utf-8-sig")
        try:
            ds = json.loads(content)
            patched = _patch_data_agent_datasource(ds)
            ds_file.write_text(json.dumps(patched, indent=2), encoding="utf-8")
            print(f"  Patched {ds_file.relative_to(dst_dir)}")
        except json.JSONDecodeError:
            print(f"  [WARN] Could not parse {ds_file.relative_to(dst_dir)}")

    print(f"  [OK] {da_name}.DataAgent/")


def _patch_data_agent_datasource(obj):
    """Recursively patch GUID references in data agent datasource configs."""
    if isinstance(obj, dict):
        for key, val in obj.items():
            lower_key = key.lower()
            if lower_key in ("workspaceid", "workspace_id"):
                # Will be auto-resolved by fabric-cicd
                obj[key] = "00000000-0000-0000-0000-000000000000"
            elif lower_key in ("artifactid", "itemid", "item_id", "lakehouseid"):
                # Try to map to known logicalIds
                obj[key] = LOGICAL_IDS.get("lh_gold_curated", val)
            elif lower_key in ("semanticmodelid", "modelid"):
                obj[key] = LOGICAL_IDS.get("HealthcareDemoHLS", val)
            elif isinstance(val, (dict, list)):
                _patch_data_agent_datasource(val)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                _patch_data_agent_datasource(item)
    return obj


# ============================================================
# COPY: Ontology (already in fabric-cicd format)
# ============================================================

def copy_ontology(source_dir, output_dir):
    """
    Copy ontology source files for post-deploy REST API deployment.
    Ontology is NOT supported by fabric-cicd, so we store it separately
    and deploy it via custom REST API calls in the launcher notebook.
    """
    print("\n=== Copying Ontology Source ===")
    ont_name = "Healthcare_Demo_Ontology_HLS"
    src_dir = source_dir / "ontologies" / ont_name

    if not src_dir.exists():
        print(f"  [SKIP] {src_dir} not found")
        return

    # Copy to a separate ontology/ folder (not workspace/ since fabric-cicd can't deploy it)
    dst_dir = output_dir.parent / "ontology" / ont_name
    if dst_dir.exists():
        try:
            shutil.rmtree(dst_dir)
        except PermissionError:
            print(f"  [WARN] Could not clean {dst_dir}, merging instead")
    shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
    print(f"  [OK] Copied to ontology/{ont_name}/")


# ============================================================
# COPY: Healthcare Knowledge Docs
# ============================================================

def copy_knowledge_docs(source_dir, output_dir):
    print("\n=== Copying Healthcare Knowledge Docs ===")
    src_dir = source_dir / "healthcare_knowledge"
    dst_dir = output_dir.parent / "healthcare_knowledge"

    if not src_dir.exists():
        print(f"  [SKIP] {src_dir} not found")
        return

    if dst_dir.exists():
        try:
            shutil.rmtree(dst_dir)
        except PermissionError:
            print(f"  [WARN] Could not clean {dst_dir}, merging instead")
    shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)

    # Count files
    count = sum(1 for _ in dst_dir.rglob("*.md"))
    print(f"  [OK] Copied {count} knowledge docs to healthcare_knowledge/")


# ============================================================
# WRITE: logicalId mapping file (for reference)
# ============================================================

def write_guid_mapping(output_dir):
    print("\n=== Writing GUID mapping ===")
    mapping_path = output_dir.parent / "scripts" / "logical_id_mapping.json"
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    mapping_path.write_text(
        json.dumps(LOGICAL_IDS, indent=2), encoding="utf-8"
    )
    print(f"  [OK] scripts/logical_id_mapping.json")


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Convert Healthcare-Data-Analytics-Repo to fabric-cicd format"
    )
    parser.add_argument(
        "--source",
        type=str,
        default=str(Path(__file__).parent.parent.parent / "Healthcare-Data-Analytics-Repo" / "FabricDemoHLS"),
        help="Path to FabricDemoHLS source directory"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(Path(__file__).parent.parent / "workspace"),
        help="Path to output workspace directory"
    )
    args = parser.parse_args()

    source_dir = Path(args.source).resolve()
    output_dir = Path(args.output).resolve()

    print("=" * 70)
    print("  CONVERT TO FABRIC-CICD FORMAT")
    print("=" * 70)
    print(f"  Source: {source_dir}")
    print(f"  Output: {output_dir}")
    print()

    if not source_dir.exists():
        print(f"[FAIL] Source directory not found: {source_dir}")
        print(f"  Make sure Healthcare-Data-Analytics-Repo is cloned alongside this repo.")
        sys.exit(1)

    # Clean output (handle OneDrive locks gracefully)
    if output_dir.exists():
        for child in output_dir.iterdir():
            try:
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
            except PermissionError:
                print(f"  [WARN] Could not remove {child.name} (locked by OneDrive?), skipping")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Convert all artifact types
    convert_lakehouses(output_dir)
    convert_notebooks(source_dir, output_dir)
    convert_pipelines(source_dir, output_dir)
    convert_semantic_model(source_dir, output_dir)
    convert_data_agent(source_dir, output_dir)
    copy_ontology(source_dir, output_dir)
    copy_knowledge_docs(source_dir, output_dir)
    write_guid_mapping(output_dir)

    # Summary
    print()
    print("=" * 70)
    print("  CONVERSION COMPLETE")
    print("=" * 70)
    item_count = sum(1 for d in output_dir.iterdir() if d.is_dir())
    print(f"  {item_count} items in workspace/")
    for d in sorted(output_dir.iterdir()):
        if d.is_dir():
            print(f"    {d.name}")
    print()
    print("  Next: Create NB_Generate_Sample_Data and NB_Generate_Incremental_Data")
    print("        manually (these are new notebooks, not converted from source).")
    print()


if __name__ == "__main__":
    main()
