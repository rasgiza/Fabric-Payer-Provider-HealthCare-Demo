"""
Deploy Power BI Report to Microsoft Fabric
============================================
Deploys the HealthcareAnalyticsDashboard report using the Fabric
Report Items API with PBIR (Power BI Interactive Report) format.

The report definition lives in payer-provider-healthcare/HealthcareAnalyticsDashboard.Report/
and includes 6 pages with 60+ visuals. The script patches definition.pbir
with the real Semantic Model ID from the target workspace.

Prerequisites:
  - Semantic model must already exist in the target workspace
  - pip install azure-identity requests

Usage:
    python scripts/deploy_report.py --workspace "MyWorkspace" --tenant-id "xxx"
    python scripts/deploy_report.py --workspace "MyWorkspace" --tenant-id "xxx" --update
    python scripts/deploy_report.py --workspace "MyWorkspace" --tenant-id "xxx" --report "My Report"
"""

import sys
import os
import json
import base64
import time
import argparse
import requests
from pathlib import Path

# Add scripts/ to path for fabric_auth import
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from fabric_auth import get_fabric_token, get_auth_headers

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ============================================================
# CONFIGURATION
# ============================================================
FABRIC_API_BASE = "https://api.fabric.microsoft.com/v1"

REPORT_NAME = "HealthcareAnalyticsDashboard"
SEMANTIC_MODEL_NAME = "HealthcareDemoHLS"

# Report definition on disk (PBIR format)
# payer-provider-healthcare/HealthcareAnalyticsDashboard.Report/
REPORT_DIR = SCRIPT_DIR.parent / "payer-provider-healthcare" / "HealthcareAnalyticsDashboard.Report"


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


def get_item(token, workspace_id, item_type, name):
    """Find a Fabric item by type and display name."""
    headers = get_auth_headers(token)
    url = f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type={item_type}"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        for item in resp.json().get("value", []):
            if item["displayName"] == name:
                return item
    return None


def wait_for_operation(token, response, name, timeout=180):
    headers = get_auth_headers(token)
    op_url = response.headers.get("Location")
    if not op_url:
        time.sleep(10)
        return True

    print(f"    Provisioning {name}...")
    start = time.time()
    while time.time() - start < timeout:
        retry = int(response.headers.get("Retry-After", 5))
        time.sleep(retry)
        op_resp = requests.get(op_url, headers=headers)
        if op_resp.status_code == 200:
            status = op_resp.json().get("status", "")
            if status == "Succeeded":
                return True
            elif status in ("Failed", "Cancelled"):
                err = op_resp.json().get("error", {}).get("message", "")
                print(f"    [FAIL] {name}: {status} -- {err}")
                return False
        elif op_resp.status_code == 404:
            time.sleep(3)
            return True
    print(f"    [FAIL] {name} timed out ({timeout}s)")
    return False


# ============================================================
# REPORT DEFINITION LOADING
# ============================================================

def build_pbir_part(semantic_model_id):
    """Build the definition.pbir part with the real SM connection string."""
    pbir = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {
            "byConnection": {
                "connectionString": f"semanticmodelid={semantic_model_id}"
            }
        }
    }
    payload_b64 = base64.b64encode(
        json.dumps(pbir, indent=2).encode("utf-8")
    ).decode("utf-8")
    return {
        "path": "definition.pbir",
        "payload": payload_b64,
        "payloadType": "InlineBase64",
    }


def load_report_parts(report_dir, semantic_model_id):
    """
    Load all PBIR definition parts from disk and return them as API-ready
    parts list. The definition.pbir is generated on-the-fly with the
    real semantic model ID (the on-disk file has connectionString: null).
    """
    definition_dir = report_dir / "definition"
    if not definition_dir.exists():
        print(f"  [FAIL] No definition/ folder found in {report_dir}")
        sys.exit(1)

    parts = []

    # 1. definition.pbir -- generated with real SM ID (not from disk)
    parts.append(build_pbir_part(semantic_model_id))
    print(f"    definition.pbir (patched: semanticmodelid={semantic_model_id})")

    # 2. Walk definition/ folder -- pages, visuals, report.json, version.json
    for root, _dirs, files in os.walk(definition_dir):
        for fname in files:
            full_path = os.path.join(root, fname)
            # Path relative to the report root (not definition/)
            rel_path = os.path.relpath(full_path, report_dir).replace("\\", "/")

            raw = Path(full_path).read_bytes()
            # Strip UTF-8 BOM if present
            if raw.startswith(b"\xef\xbb\xbf"):
                raw = raw[3:]

            parts.append({
                "path": rel_path,
                "payload": base64.b64encode(raw).decode("utf-8"),
                "payloadType": "InlineBase64",
            })

    return parts


# ============================================================
# CREATE / DELETE REPORT
# ============================================================

def create_report(token, workspace_id, name, parts):
    """Create a new report. Returns item ID or None."""
    headers = get_auth_headers(token)
    url = f"{FABRIC_API_BASE}/workspaces/{workspace_id}/reports"

    payload = {
        "displayName": name,
        "definition": {"parts": parts},
    }

    resp = requests.post(url, headers=headers, json=payload)

    if resp.status_code in (200, 201):
        item_id = resp.json().get("id")
        print(f"  [OK] Created: {name} (ID: {item_id})")
        return item_id
    elif resp.status_code == 202:
        success = wait_for_operation(token, resp, name)
        if success:
            item = get_item(token, workspace_id, "Report", name)
            if item:
                print(f"  [OK] Created: {name} (ID: {item['id']})")
                return item["id"]
        print(f"  [FAIL] Failed to create: {name}")
        return None
    elif resp.status_code == 409:
        print(f"  [WARN] Already exists: {name}")
        return "exists"
    else:
        print(f"  [FAIL] Create failed: HTTP {resp.status_code}")
        print(f"    {resp.text[:500]}")
        return None


def delete_item(token, workspace_id, item_id, name):
    """Delete an existing item."""
    headers = get_auth_headers(token)
    url = f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items/{item_id}"
    resp = requests.delete(url, headers=headers)
    if resp.status_code in (200, 204):
        print(f"  [OK] Deleted existing: {name} ({item_id})")
        return True
    else:
        print(f"  [WARN] Could not delete {name}: HTTP {resp.status_code}")
        return False


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Deploy Power BI Report to Fabric")
    parser.add_argument("--workspace", required=True,
                        help="Target Fabric workspace name")
    parser.add_argument("--tenant-id", required=True,
                        help="Azure AD tenant ID")
    parser.add_argument("--account", default=None,
                        help="Account email hint for browser auth")
    parser.add_argument("--report", default=REPORT_NAME,
                        help=f"Report name (default: {REPORT_NAME})")
    parser.add_argument("--semantic-model", default=SEMANTIC_MODEL_NAME,
                        help=f"Semantic model name to bind to (default: {SEMANTIC_MODEL_NAME})")
    parser.add_argument("--update", action="store_true",
                        help="Delete and re-create existing report")
    args = parser.parse_args()

    report_dir = REPORT_DIR

    print("=" * 70)
    print("  DEPLOY POWER BI REPORT TO FABRIC")
    print("=" * 70)
    print(f"  Target Workspace: {args.workspace}")
    print(f"  Report Name:      {args.report}")
    print(f"  Semantic Model:   {args.semantic_model}")
    print(f"  Source:            {report_dir}")
    print(f"  Mode:             {'Replace existing' if args.update else 'Create new'}")
    print()

    if not report_dir.exists():
        print(f"  [FAIL] Report directory not found: {report_dir}")
        print(f"  Expected PBIR definition in: payer-provider-healthcare/HealthcareAnalyticsDashboard.Report/definition/")
        sys.exit(1)

    # -- Authenticate --
    print("Step 1: Authenticating...")
    token = get_fabric_token(args.tenant_id, args.account)
    print()

    # -- Resolve workspace --
    print("Step 2: Finding workspace...")
    workspace_id = get_workspace_id(token, args.workspace)
    print(f"  [OK] Workspace ID: {workspace_id}")
    print()

    # -- Find semantic model --
    print("Step 3: Finding semantic model...")
    sm = get_item(token, workspace_id, "SemanticModel", args.semantic_model)
    if not sm:
        print(f"  [FAIL] Semantic model '{args.semantic_model}' not found in workspace")
        print(f"  Deploy the semantic model first (Cell 8 in Healthcare_Launcher.ipynb)")
        sys.exit(1)
    sm_id = sm["id"]
    print(f"  [OK] {args.semantic_model} (ID: {sm_id})")
    print()

    # -- Load definition parts --
    print("Step 4: Loading report definition from disk...")
    parts = load_report_parts(report_dir, sm_id)
    if not parts:
        print("  [FAIL] No definition parts loaded")
        sys.exit(1)
    print(f"  [OK] Loaded {len(parts)} part(s)")
    page_count = sum(1 for p in parts if p["path"].endswith("/page.json"))
    visual_count = sum(1 for p in parts if p["path"].endswith("/visual.json"))
    print(f"       {page_count} pages, {visual_count} visuals")
    print()

    # -- Check existing --
    print("Step 5: Checking existing reports...")
    existing = get_item(token, workspace_id, "Report", args.report)

    if existing and args.update:
        print(f"  Found existing report: {existing['id']}")
        delete_item(token, workspace_id, existing["id"], args.report)
        time.sleep(3)
        existing = None
    elif existing and not args.update:
        print(f"  [WARN] Report '{args.report}' already exists (use --update to replace)")
        print(f"  Open: https://app.fabric.microsoft.com/groups/{workspace_id}/reports/{existing['id']}")
        print()
        print("=" * 70)
        print("  DEPLOYMENT SUMMARY")
        print("=" * 70)
        print(f"  {args.report:<45} [WARN] Already exists")
        print()
        return
    print()

    # -- Deploy --
    print("Step 6: Creating report...")
    item_id = create_report(token, workspace_id, args.report, parts)

    print()
    print("=" * 70)
    print("  DEPLOYMENT SUMMARY")
    print("=" * 70)
    if item_id and item_id != "exists":
        print(f"  {args.report:<45} [OK] Created")
        print(f"  Open: https://app.fabric.microsoft.com/groups/{workspace_id}/reports/{item_id}")
    elif item_id == "exists":
        print(f"  {args.report:<45} [WARN] Already exists")
    else:
        print(f"  {args.report:<45} [FAIL] Failed")
    print()

    if not item_id or item_id == "exists":
        sys.exit(1 if not item_id else 0)


if __name__ == "__main__":
    main()
