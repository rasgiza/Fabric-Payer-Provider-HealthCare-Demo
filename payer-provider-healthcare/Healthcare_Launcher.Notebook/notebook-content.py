# Fabric notebook source

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# # Healthcare Payer & Provider Analytics — Launcher
#
# **Jumpstart entry-point notebook.** This notebook orchestrates the post-deploy steps for the
# `payer-provider-healthcare` Microsoft Fabric Jumpstart.
#
# ## What this notebook does
#
# After `fabric_jumpstart.install('payer-provider-healthcare', ...)` deploys the Lakehouses, Notebooks,
# Pipelines, Semantic Model, Report, RTI items, and HLS Data Agent into your workspace, **Run All**
# in this notebook to:
#
# 1. Upload healthcare knowledge documents to `lh_gold_curated/Files/healthcare_knowledge/`
# 2. Generate synthetic patient/claims data into `lh_bronze_raw`
# 3. Run the `PL_Healthcare_Master` pipeline (Bronze → Silver → Gold, full-load mode)
# 4. Create / refresh the `HealthcareDemoHLS` Direct Lake Semantic Model
# 5. Deploy the `HealthcareAnalyticsDashboard` Power BI report (PBIR import + rebind)
# 6. Deploy the `Healthcare_Demo_Ontology_HLS` ontology and graph model
# 7. Patch the `HealthcareHLSAgent` Data Agent with the deployed Semantic Model + Lakehouse IDs
# 8. Set up Real-Time Intelligence: KQL tables in `Healthcare_RTI_Eventhouse`, `Healthcare_RTI_Eventstream` (CustomEndpoint → KQL DB + `lh_bronze_raw` + Activator), and the `Healthcare RTI Dashboard`
# 9. Run the RTI fraud-detection and high-cost-trajectory scoring notebooks
# 10. Organize workspace items into folders
#
# > Set `DEPLOY_STREAMING = False` in the CONFIGURATION cell below if you want to skip steps 8–9 (batch-only demo).
#
# ## Prerequisites
#
# - Workspace is a Fabric-capacity workspace (F64+ recommended for Direct Lake + RTI).
# - This notebook was deployed via `fabric_jumpstart.install('payer-provider-healthcare', ...)`.
# - All items in the `payer-provider-healthcare/` folder are visible in the workspace.
#
# ## What you do next
#
# 1. Edit the **CONFIGURATION** cell below if you want to skip data generation or enable streaming.
# 2. **Run All**.
# 3. When complete, open the **HealthcareAnalyticsDashboard** Power BI report, the **Healthcare RTI Dashboard** (real-time KQL), or chat with the **HealthcareHLSAgent** Data Agent.
# 4. *(Streaming)* Copy the Eventstream connection string from the portal into
#    `NB_RTI_Event_Simulator` to start streaming events end-to-end.

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# CONFIGURATION — Edit these values
# ============================================================================

# GitHub source (used as a runtime fallback when fetching healthcare_knowledge/
# markdown files and ontology JSON — the Jumpstart installer does NOT extract
# the repo into a lakehouse Files/ folder, so a couple of cells download
# auxiliary files directly from the public mirror).
GITHUB_OWNER  = "rasgiza"
GITHUB_REPO   = "Fabric-Payer-Provider-HealthCare-Demo"
GITHUB_BRANCH = "v1.0.1"   # tag pinned by the fabric-jumpstart catalog entry

# Post-deploy options
UPLOAD_KNOWLEDGE_DOCS = True   # Fetch healthcare_knowledge/*.md and upload to lh_gold_curated
GENERATE_DATA         = True   # Run NB_Generate_Sample_Data to populate lh_bronze_raw
RUN_PIPELINE          = True   # Run PL_Healthcare_Master end-to-end (full-load)
DEPLOY_STREAMING      = True   # Wire RTI Eventstream topology, deploy KQL Dashboard, run scoring notebooks

# Resolve the workspace_id at runtime (set automatically by Fabric)
workspace_id = spark.conf.get("trident.workspace.id")
print(f"Workspace: {workspace_id}")
print(f"Source ref: github.com/{GITHUB_OWNER}/{GITHUB_REPO}@{GITHUB_BRANCH}")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# CELL 1 — Upload healthcare knowledge docs to lh_gold_curated
# ============================================================================
# The Jumpstart installer deploys Fabric items but does not extract loose
# documentation files. We fetch healthcare_knowledge/*.md directly from the
# public GitHub raw URL and write them to the lakehouse via OneLake DFS.
# ============================================================================

if UPLOAD_KNOWLEDGE_DOCS:
    import requests, json
    from notebookutils import mssparkutils

    KNOWN_DOCS = [
        "clinical_terminology.md",
        "hcc_risk_adjustment.md",
        "hedis_quality_measures.md",
        "icd10_common_codes.md",
        "payer_glossary.md",
        "provider_glossary.md",
    ]
    raw_base = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/healthcare_knowledge"

    # GitHub Contents API to enumerate the folder (handles future additions)
    api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/healthcare_knowledge?ref={GITHUB_BRANCH}"
    try:
        resp = requests.get(api_url, timeout=30)
        if resp.status_code == 200:
            entries = [e["name"] for e in resp.json() if e.get("name", "").endswith(".md")]
        else:
            print(f"  GitHub Contents API returned {resp.status_code}, falling back to known list")
            entries = KNOWN_DOCS
    except Exception as e:
        print(f"  GitHub Contents API failed ({e}), falling back to known list")
        entries = KNOWN_DOCS

    target_dir = "/lakehouse/default/Files/healthcare_knowledge"
    mssparkutils.fs.mkdirs(f"file:{target_dir}")

    uploaded = 0
    for name in entries:
        try:
            r = requests.get(f"{raw_base}/{name}", timeout=30)
            r.raise_for_status()
            with open(f"{target_dir}/{name}", "wb") as fh:
                fh.write(r.content)
            uploaded += 1
        except Exception as e:
            print(f"  [WARN] failed to upload {name}: {e}")
    print(f"Uploaded {uploaded}/{len(entries)} knowledge documents to lh_gold_curated/Files/healthcare_knowledge/")
else:
    print("Skipping knowledge doc upload (UPLOAD_KNOWLEDGE_DOCS=False)")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# CELL 2 — Generate synthetic data
# ============================================================================
# Uses notebookutils.notebook.run() — the native Fabric way to orchestrate
# notebooks. More reliable than the Jobs REST API after updateDefinition.
# ============================================================================

if GENERATE_DATA:
    print("Running NB_Generate_Sample_Data (generates ~10K patients, 100K encounters)...")
    print("This takes 2-4 minutes.\n")

    try:
        notebookutils.notebook.run("NB_Generate_Sample_Data", 1200, {"useRootDefaultLakehouse": True})
        print("\n✅ Data generation SUCCEEDED")
    except Exception as e:
        # Known Fabric bug: notebook succeeds but result-parsing throws
        # NoSuchElementException on the snapshot MIME key. Treat as success.
        if "mssparkutilsrun-result+json" in str(e) or "NoSuchElementException" in str(e):
            print("\n✅ Data generation SUCCEEDED (ignoring Fabric result-parse bug)")
        else:
            print(f"\n❌ Data generation FAILED: {e}")
            print("Try running NB_Generate_Sample_Data manually from the workspace.")
else:
    print("Skipping data generation (GENERATE_DATA=False)")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# CELL 3 — Run the full-load pipeline
# ============================================================================

if RUN_PIPELINE:
    import requests, time, json

    token = notebookutils.credentials.getToken("pbi")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    api_base = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}"

    # Find the pipeline ID
    print("Looking up PL_Healthcare_Master pipeline...")
    resp = requests.get(f"{api_base}/items?type=DataPipeline", headers=headers)
    resp.raise_for_status()
    pipelines = resp.json().get("value", [])
    pipeline = next((p for p in pipelines if p["displayName"] == "PL_Healthcare_Master"), None)

    if not pipeline:
        print("WARNING: PL_Healthcare_Master not found. Skipping pipeline run.")
        print("You can run it manually from the workspace.")
    else:
        pipeline_id = pipeline["id"]
        print(f"Pipeline ID: {pipeline_id}")

        # Trigger pipeline with load_mode=full
        print("Triggering pipeline with load_mode=full...")
        trigger_body = {
            "executionData": {
                "parameters": {
                    "load_mode": "full"
                }
            }
        }
        resp = requests.post(
            f"{api_base}/items/{pipeline_id}/jobs/instances?jobType=Pipeline",
            headers=headers,
            json=trigger_body,
        )

        if resp.status_code in (200, 202):
            # Get job ID from Location header or response
            location = resp.headers.get("Location", "")
            print(f"Pipeline triggered. Polling for completion...")
            print(f"(This takes 8-15 minutes for full load)\n")

            # Poll until complete
            max_polls = 120  # 120 * 15s = 30 min max
            for poll in range(max_polls):
                time.sleep(15)
                try:
                    if location:
                        poll_resp = requests.get(location, headers=headers)
                    else:
                        poll_resp = requests.get(
                            f"{api_base}/items/{pipeline_id}/jobs/instances",
                            headers=headers,
                        )
                    if poll_resp.status_code == 200:
                        job_data = poll_resp.json()
                        status = job_data.get("status", "Unknown")
                        if status in ("Completed", "Succeeded"):
                            print(f"  Pipeline COMPLETED after {(poll+1)*15}s")
                            break
                        elif status in ("Failed", "Cancelled"):
                            print(f"  Pipeline {status} after {(poll+1)*15}s")
                            print(f"  Check the pipeline run history for details.")
                            break
                        else:
                            if poll % 4 == 0:  # Print every 60s
                                print(f"  [{(poll+1)*15}s] Status: {status}...")
                except Exception as e:
                    if poll % 4 == 0:
                        print(f"  [{(poll+1)*15}s] Polling... ({e})")
            else:
                print("  Pipeline still running after 30 min. Check workspace for status.")
        else:
            print(f"  Pipeline trigger returned {resp.status_code}: {resp.text}")
            print("  You can run it manually from the workspace.")
else:
    print("Skipping pipeline run (RUN_PIPELINE=False)")
    print("To run manually: Open PL_Healthcare_Master → Run with load_mode=full")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# CELL 4 — Create & Refresh Semantic Model (Direct Lake)
# ============================================================================
# The Semantic Model is rebuilt at runtime here (placeholder GUIDs in the repo
# would corrupt AS internal metadata). Instead we create it here, AFTER the
# pipeline has run and Gold tables exist in lh_gold_curated.
#
# Steps:
#   1. Find lh_gold_curated lakehouse ID
#   2. Delete any existing SM with the same name (idempotent re-run)
#   3. Load all TMDL files from the extracted repo on the lakehouse filesystem
#   4. Patch expressions.tmdl URL with correct payer-provider-healthcare/lakehouse IDs
#   5. Create fresh SM via POST /semanticModels with all definition parts
#   6. Trigger Full refresh
# ============================================================================

import requests, time, base64, re, json, os

token = notebookutils.credentials.getToken("pbi")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
FABRIC_API = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}"

SM_NAME = "HealthcareDemoHLS"
SM_REPO_DIR = "payer-provider-healthcare/HealthcareDemoHLS.SemanticModel"
URL_PATTERN = re.compile(
    r'https://onelake\.dfs\.fabric\.microsoft\.com/'
    r'[0-9a-fA-F-]{36}/[0-9a-fA-F-]{36}'
)

def wait_lro(resp, hdr, timeout=120):
    """Poll an LRO and return (final_status, result_body)."""
    loc = resp.headers.get("Location", "")
    retry = int(resp.headers.get("Retry-After", 5))
    elapsed = 0
    while elapsed < timeout:
        time.sleep(retry)
        elapsed += retry
        r = requests.get(loc, headers=hdr)
        if r.status_code != 200:
            continue
        body = r.json()
        st = body.get("status", "")
        if st == "Succeeded":
            res_loc = body.get("resourceLocation", "")
            if res_loc:
                rr = requests.get(res_loc, headers=hdr)
                if rr.status_code == 200:
                    return "Succeeded", rr.json()
            rr = requests.get(f"{loc}/result", headers=hdr)
            if rr.status_code == 200:
                return "Succeeded", rr.json()
            return "Succeeded", body
        elif st in ("Failed", "Cancelled"):
            err = body.get("error", {})
            return st, err
    return "Timeout", {}

print("=" * 60)
print("  SEMANTIC MODEL -- Create from Repo Definition")
print("=" * 60)

# -- Step 1: Discover lakehouse ID ----------------------------------------
resp = requests.get(f"{FABRIC_API}/lakehouses", headers=headers)
resp.raise_for_status()
lh_gold_id = None
for lh in resp.json().get("value", []):
    if lh["displayName"] == "lh_gold_curated":
        lh_gold_id = lh["id"]
        break

if not lh_gold_id:
    print("  [WARN] lh_gold_curated not found -- skipping SM creation")
    print("  Run the pipeline first, then re-run this cell.")
else:
    print(f"  Lakehouse: lh_gold_curated ({lh_gold_id})")
    print(f"  Workspace: {workspace_id}")
    new_url = f"https://onelake.dfs.fabric.microsoft.com/{workspace_id}/{lh_gold_id}"

    # -- Step 2: Delete existing SM if any (idempotent re-run) -------------
    resp = requests.get(f"{FABRIC_API}/items?type=SemanticModel", headers=headers)
    resp.raise_for_status()
    for sm in resp.json().get("value", []):
        if sm["displayName"] == SM_NAME:
            old_id = sm["id"]
            print(f"  Deleting existing SM: {SM_NAME} ({old_id})...")
            dr = requests.delete(f"{FABRIC_API}/semanticModels/{old_id}", headers=headers)
            if dr.status_code in (200, 202, 204):
                if dr.status_code == 202:
                    wait_lro(dr, headers, timeout=60)
                print(f"  Deleted.")
            else:
                print(f"  [WARN] Delete HTTP {dr.status_code}: {dr.text[:200]}")
            print("  Waiting 10s for name availability...")
            time.sleep(10)
            break

    # -- Step 3: Load TMDL from extracted repo on lakehouse ----------------
    # tmdl source is fetched from GitHub raw at runtime
    sm_base = None
    for base_prefix in [".lakehouse/default/Files/src", "/lakehouse/default/Files/src"]:
        if not os.path.isdir(base_prefix):
            continue
        # Direct path
        direct = os.path.join(base_prefix, SM_REPO_DIR)
        if os.path.isdir(direct):
            sm_base = direct
            break
        # One level down (extracted repo subdirectory)
        for sub in os.listdir(base_prefix):
            nested = os.path.join(base_prefix, sub, SM_REPO_DIR)
            if os.path.isdir(nested):
                sm_base = nested
                break
        if sm_base:
            break

    # -- Fallback: download SM definition from GitHub directly ---------
    if not sm_base:
        print("  Lakehouse extract not found. Downloading SM from GitHub...")
        import tempfile
        _tmp_dir = tempfile.mkdtemp()
        _sm_local = os.path.join(_tmp_dir, SM_REPO_DIR)
        try:
            _gh_hdrs = {"Accept": "application/vnd.github.v3+json"}
            if GITHUB_TOKEN:
                _gh_hdrs["Authorization"] = f"Bearer {GITHUB_TOKEN}"
            _tree_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/trees/{GITHUB_BRANCH}?recursive=1"
            _tree_r = requests.get(_tree_url, headers=_gh_hdrs)
            _tree_r.raise_for_status()
            _sm_prefix = SM_REPO_DIR + "/"
            _sm_files = [
                e for e in _tree_r.json()["tree"]
                if e["path"].startswith(_sm_prefix) and e["type"] == "blob"
            ]
            _downloaded = 0
            for entry in _sm_files:
                rel = entry["path"][len(_sm_prefix):]
                if rel == ".platform":
                    continue
                raw_url = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{entry['path']}"
                dr = requests.get(raw_url)
                dr.raise_for_status()
                local_path = os.path.join(_sm_local, rel)
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, "wb") as f:
                    f.write(dr.content)
                _downloaded += 1
            if os.path.isdir(_sm_local):
                sm_base = _sm_local
                print(f"  Downloaded {_downloaded} SM definition files from GitHub")
        except Exception as ex:
            print(f"  [WARN] GitHub download failed: {ex}")

    if not sm_base:
        print("  [FAIL] SM definition not found on lakehouse or GitHub.")
    else:
        print(f"  SM definition dir: {sm_base}")
        def_dir = os.path.join(sm_base, "definition")

        parts = []

        # Load definition.pbism
        pbism_path = os.path.join(sm_base, "definition.pbism")
        if os.path.exists(pbism_path):
            with open(pbism_path, "rb") as f:
                raw = f.read()
            if raw.startswith(b"\xef\xbb\xbf"):
                raw = raw[3:]
            parts.append({
                "path": "definition.pbism",
                "payload": base64.b64encode(raw).decode(),
                "payloadType": "InlineBase64"
            })

        # Load all definition/*.tmdl files (recursively for tables/)
        if os.path.isdir(def_dir):
            for root, dirs, files in os.walk(def_dir):
                for fname in sorted(files):
                    fpath = os.path.join(root, fname)
                    rel = "definition/" + os.path.relpath(fpath, def_dir).replace("\\", "/")
                    with open(fpath, "rb") as f:
                        raw = f.read()
                    if raw.startswith(b"\xef\xbb\xbf"):
                        raw = raw[3:]

                    # Patch expressions.tmdl URL
                    if "expressions.tmdl" in rel:
                        content = raw.decode("utf-8")
                        matches = URL_PATTERN.findall(content)
                        if matches and matches[0] != new_url:
                            print(f"  Patching URL: {matches[0]} -> {new_url}")
                            content = URL_PATTERN.sub(new_url, content)
                            raw = content.encode("utf-8")
                        elif matches:
                            print(f"  URL already correct in expressions.tmdl")
                        else:
                            print(f"  [WARN] No URL found in expressions.tmdl -- injecting correct URL")

                    parts.append({
                        "path": rel,
                        "payload": base64.b64encode(raw).decode(),
                        "payloadType": "InlineBase64"
                    })

        print(f"  Loaded {len(parts)} definition parts:")
        for p in parts[:5]:
            print(f"    {p['path']}")
        if len(parts) > 5:
            print(f"    ... and {len(parts) - 5} more")

        if not parts:
            print("  [FAIL] No definition parts loaded. Cannot create SM.")
        else:
            # -- Step 4: Create SM with correct definition -----------------
            token = notebookutils.credentials.getToken("pbi")
            headers["Authorization"] = f"Bearer {token}"

            create_body = {
                "displayName": SM_NAME,
                "description": "Healthcare Demo Direct Lake semantic model",
                "definition": {"parts": parts}
            }

            print(f"  Creating SM: {SM_NAME} with {len(parts)} TMDL parts...")
            r = requests.post(f"{FABRIC_API}/semanticModels", headers=headers, json=create_body)
            print(f"  Create HTTP {r.status_code}")

            sm_id = None
            if r.status_code in (200, 201):
                sm_id = r.json().get("id")
                print(f"  Created: {sm_id}")
            elif r.status_code == 202:
                st, body = wait_lro(r, headers, timeout=180)
                if st == "Succeeded":
                    time.sleep(3)
                    resp2 = requests.get(f"{FABRIC_API}/items?type=SemanticModel", headers=headers)
                    for sm in resp2.json().get("value", []):
                        if sm["displayName"] == SM_NAME:
                            sm_id = sm["id"]
                            break
                if sm_id:
                    print(f"  Created (async): {sm_id}")
                else:
                    print(f"  Create LRO {st}: {body}")
            else:
                print(f"  [FAIL] Create SM: HTTP {r.status_code}")
                print(f"  Response: {r.text[:500]}")
                sm_id = None

            # -- Step 5: Trigger refresh -----------------------------------
            if sm_id:
                print("  Waiting 15s for SM initialization...")
                time.sleep(15)

                token = notebookutils.credentials.getToken("pbi")
                headers["Authorization"] = f"Bearer {token}"

                pbi_base = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}"
                refresh_url = f"{pbi_base}/datasets/{sm_id}/refreshes"

                MAX_ATTEMPTS = 3
                for attempt in range(1, MAX_ATTEMPTS + 1):
                    print(f"  Triggering refresh (attempt {attempt}/{MAX_ATTEMPTS})...")
                    r = requests.post(refresh_url, headers=headers, json={"type": "Full"})

                    if r.status_code not in (200, 202):
                        print(f"  Refresh trigger HTTP {r.status_code}: {r.text[:300]}")
                        if attempt < MAX_ATTEMPTS:
                            print(f"  Retrying in 15s...")
                            time.sleep(15)
                            token = notebookutils.credentials.getToken("pbi")
                            headers["Authorization"] = f"Bearer {token}"
                            continue
                        else:
                            print("  All attempts failed. Refresh manually from the workspace.")
                            break

                    # Poll for completion
                    success = False
                    for poll_i in range(60):
                        time.sleep(10)
                        poll_resp = requests.get(refresh_url, headers=headers)
                        if poll_resp.status_code == 200:
                            refreshes = poll_resp.json().get("value", [])
                            if refreshes:
                                latest = refreshes[0]
                                status = latest.get("status", "Unknown")
                                if status in ("Completed", "Succeeded"):
                                    print(f"  Refresh COMPLETED after {(poll_i+1)*10}s")
                                    success = True
                                    break
                                elif status == "Failed":
                                    err_msg = latest.get("serviceExceptionJson", "")
                                    print(f"  Refresh FAILED after {(poll_i+1)*10}s")
                                    if err_msg:
                                        try:
                                            err_obj = json.loads(err_msg)
                                            print(f"  Error: {err_obj.get('errorCode', '')}")
                                            print(f"  Detail: {err_obj.get('errorDescription', '')[:300]}")
                                        except Exception:
                                            print(f"  Error: {err_msg[:300]}")
                                    break
                            elif poll_i % 3 == 0:
                                print(f"  [{(poll_i+1)*10}s] Status: {status}...")
                    else:
                        print("  Refresh still running after 10 min. Check workspace.")
                        break

                    if success:
                        break
                    elif attempt < MAX_ATTEMPTS:
                        print(f"  Retrying in 20s...")
                        time.sleep(20)
                        token = notebookutils.credentials.getToken("pbi")
                        headers["Authorization"] = f"Bearer {token}"
                    else:
                        print("  All refresh attempts failed. Refresh manually from the workspace.")

print("=" * 60)

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# CELL 4b — Deploy Power BI Report (requires Semantic Model from Cell 4)
# ============================================================================
# Imports the pre-built .pbix file from the lakehouse (or GitHub) and rebinds
# it to the Semantic Model deployed in Cell 8.
#
# The .pbix contains the report layout only (6 pages, 65 visuals, live
# connection). Data flows automatically from Lakehouse → Direct Lake SM →
# Report at query time. No data is stored in the .pbix.
#
# To update visuals: edit the report in Power BI Desktop, re-save the .pbix,
# and commit it to the repo. Re-running this cell will redeploy it.
# ============================================================================

import requests, json, os, time, io

print("=" * 60)
print("  POWER BI REPORT DEPLOYMENT (PBIX Import)")
print("=" * 60)

token = notebookutils.credentials.getToken("pbi")
headers = {"Authorization": f"Bearer {token}"}
PBI_API = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}"
FABRIC_API = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}"

REPORT_NAME = "HealthcareAnalyticsDashboard"
SM_NAME = "HealthcareDemoHLS"
PBIX_FILENAME = "Healthcare_Analytics_Dashboard.pbix"
PBIX_REPO_PATH = f"payer-provider-healthcare/{PBIX_FILENAME}"

# --- 1. Find the Semantic Model ID in workspace ---
headers_json = {**headers, "Content-Type": "application/json"}
resp = requests.get(f"{FABRIC_API}/items?type=SemanticModel", headers=headers_json)
sm_id = None
for item in resp.json().get("value", []):
    if item["displayName"] == SM_NAME:
        sm_id = item["id"]
        break

if not sm_id:
    print(f"  [SKIP] SemanticModel '{SM_NAME}' not found — run Cell 8 first.")
else:
    print(f"  SemanticModel: {SM_NAME} ({sm_id})")

    # --- 2. Find the .pbix file ---
    pbix_path = None
    # Check lakehouse first
    for base in [".lakehouse/default/Files/src", "/lakehouse/default/Files/src"]:
        if not os.path.isdir(base):
            continue
        # Direct path
        direct = os.path.join(base, PBIX_REPO_PATH)
        if os.path.isfile(direct):
            pbix_path = direct
            break
        # One level down (extracted repo subdirectory)
        for sub in os.listdir(base):
            nested = os.path.join(base, sub, PBIX_REPO_PATH)
            if os.path.isfile(nested):
                pbix_path = nested
                break
        if pbix_path:
            break

    # Fallback: download .pbix from GitHub
    pbix_bytes = None
    if pbix_path:
        print(f"  PBIX source: {pbix_path}")
        with open(pbix_path, "rb") as f:
            pbix_bytes = f.read()
    else:
        print(f"  PBIX not found on lakehouse. Downloading from GitHub...")
        try:
            gh_hdrs = {"Accept": "application/vnd.github.v3.raw"}
            if GITHUB_TOKEN:
                gh_hdrs["Authorization"] = f"Bearer {GITHUB_TOKEN}"
            raw_url = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{PBIX_REPO_PATH}"
            dl = requests.get(raw_url, headers=gh_hdrs)
            dl.raise_for_status()
            pbix_bytes = dl.content
            print(f"  Downloaded {PBIX_FILENAME} from GitHub ({len(pbix_bytes):,} bytes)")
        except Exception as ex:
            print(f"  [ERROR] Failed to download .pbix: {ex}")

    if not pbix_bytes:
        print(f"  [ERROR] {PBIX_FILENAME} not found.")
        print(f"  Build it in Power BI Desktop (connect to {SM_NAME}),")
        print(f"  save as {PBIX_FILENAME}, and place it in payer-provider-healthcare/ in the repo.")
    else:
        print(f"  PBIX size: {len(pbix_bytes):,} bytes")

        # --- 2b. Patch PBIX connections for target workspace ---
        # The .pbix contains hardcoded payer-provider-healthcare/dataset IDs from the author's
        # environment. We rewrite the Connections file so the import works in
        # ANY workspace, not just the original one.
        import zipfile, urllib.parse
        try:
            # Build the connection string for THIS workspace
            ws_resp = requests.get(
                f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}",
                headers=headers_json
            )
            ws_name = ws_resp.json().get("displayName", "") if ws_resp.status_code == 200 else ""
            ws_name_encoded = urllib.parse.quote(ws_name) if ws_name else workspace_id
            new_conn_str = (
                f"Data Source=powerbi://api.powerbi.com/v1.0/myorg/{ws_name_encoded};"
                f"Initial Catalog={SM_NAME};Integrated Security=ClaimsToken"
            )
            new_connections = {
                "Version": 6,
                "Connections": [{
                    "Name": "EntityDataSource",
                    "ConnectionString": new_conn_str,
                    "ConnectionType": "pbiServiceXmlaStyleLive",
                    "PbiModelVirtualServerName": "sobe_wowvirtualserver",
                    "PbiModelDatabaseName": sm_id
                }],
                "RemoteArtifacts": [{"DatasetId": sm_id}],
                "OriginalWorkspaceObjectId": workspace_id
            }
            conn_json = json.dumps(new_connections, separators=(",", ":"))

            # Rebuild PBIX with patched Connections file
            old_zip = zipfile.ZipFile(io.BytesIO(pbix_bytes), "r")
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as new_zip:
                for item in old_zip.infolist():
                    if item.filename == "Connections":
                        new_zip.writestr(item, conn_json.encode("utf-8"))
                    else:
                        new_zip.writestr(item, old_zip.read(item.filename))
            old_zip.close()
            pbix_bytes = buf.getvalue()
            print(f"  Patched PBIX connections for workspace {workspace_id[:8]}...")
            print(f"  Patched PBIX size: {len(pbix_bytes):,} bytes")
        except Exception as ex:
            print(f"  [WARN] Could not patch PBIX connections: {ex}")
            print(f"  Proceeding with original PBIX (may fail in other workspaces)")



        # --- 3. Delete existing Report if any (idempotent re-run) ---
        resp = requests.get(f"{FABRIC_API}/items?type=Report", headers=headers_json)
        for item in resp.json().get("value", []):
            if item["displayName"] == REPORT_NAME:
                requests.delete(f"{FABRIC_API}/items/{item['id']}", headers=headers_json)
                print(f"  Deleted existing report: {item['id']}")
                time.sleep(5)
                break

        # --- 4. Import .pbix via Power BI Import API ---
        print(f"\n  Importing {PBIX_FILENAME}...")
        import_url = f"{PBI_API}/imports?datasetDisplayName={SM_NAME}&nameConflict=CreateOrOverwrite"

        # Multipart upload
        files = {
            "file": (PBIX_FILENAME, io.BytesIO(pbix_bytes), "application/octet-stream")
        }
        resp = requests.post(import_url, headers=headers, files=files)

        if resp.status_code in (200, 201, 202):
            import_body = resp.json()
            import_id = import_body.get("id", "")
            print(f"  Import accepted (ID: {import_id})")

            # Poll until import completes
            rpt_id = None
            for attempt in range(60):
                time.sleep(3)
                r = requests.get(f"{PBI_API}/imports/{import_id}", headers=headers)
                if r.status_code == 200:
                    ibody = r.json()
                    status = ibody.get("importState", "")
                    if status == "Succeeded":
                        reports = ibody.get("reports", [])
                        if reports:
                            rpt_id = reports[0].get("id")
                            rpt_name = reports[0].get("name", REPORT_NAME)
                            print(f"\n  Report imported: {rpt_name} ({rpt_id})")
                        else:
                            print(f"\n  Import succeeded but no reports found in result")
                        break
                    elif status == "Failed":
                        print(f"\n  Import FAILED: {json.dumps(ibody, indent=2)[:500]}")
                        break
                    elif attempt % 5 == 0:
                        print(f"    ... {status}")
            else:
                print("  Import timed out after 180s. Check workspace.")

            # --- 5. Rebind to the correct Semantic Model ---
            if rpt_id:
                print(f"\n  Rebinding report to {SM_NAME} ({sm_id})...")
                rebind_resp = requests.post(
                    f"{PBI_API}/reports/{rpt_id}/Rebind",
                    headers={**headers, "Content-Type": "application/json"},
                    json={"datasetId": sm_id}
                )
                if rebind_resp.status_code == 200:
                    print(f"  Rebind successful!")
                    # Rename report to desired display name
                    rename_resp = requests.patch(
                        f"{FABRIC_API}/items/{rpt_id}",
                        headers={**headers, "Content-Type": "application/json"},
                        json={"displayName": REPORT_NAME}
                    )
                    if rename_resp.status_code == 200:
                        print(f"  Renamed report to: {REPORT_NAME}")
                    else:
                        print(f"  Rename skipped (HTTP {rename_resp.status_code})")
                else:
                    print(f"  Rebind HTTP {rebind_resp.status_code}: {rebind_resp.text[:300]}")
                    print(f"  (Report may already be bound to the correct SM)")

                # --- 6. Verify ---
                time.sleep(3)
                token = notebookutils.credentials.getToken("pbi")
                headers["Authorization"] = f"Bearer {token}"
                r = requests.get(f"{PBI_API}/reports/{rpt_id}/pages", headers=headers)
                if r.status_code == 200:
                    pages = r.json().get("value", [])
                    print(f"\n  Verification: {len(pages)} pages")
                    for pg in pages:
                        print(f"    - {pg.get('displayName')} (order={pg.get('order')})")

                print(f"\n  Report URL: https://app.fabric.microsoft.com/groups/{workspace_id}/reports/{rpt_id}")
        else:
            print(f"  [ERROR] Import HTTP {resp.status_code}:")
            print(f"  {resp.text[:800]}")

print("\n" + "=" * 60)

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# CELL 5 — Deploy Ontology & Graph Model
# ============================================================================
# Deploys the ontology (12 entity types, 18 relationships) directly via
# the Fabric REST API. Graph Model is auto-provisioned by Fabric.
# For manual graph deploy/diagnostics, use NB_Deploy_Graph_Model notebook.
# ============================================================================
#
# ============================================================================

import json, requests, time, base64, os, re, math, uuid

print("=" * 60)
print("  ONTOLOGY -- API Deployment")
print("=" * 60)
print()

# -- Auth & Discovery -----------------------------------------
token = notebookutils.credentials.getToken("pbi")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
API = "https://api.fabric.microsoft.com/v1"

print(f"  Workspace: {workspace_id}")

# Discover lh_gold_curated lakehouse ID
resp = requests.get(f"{API}/workspaces/{workspace_id}/lakehouses", headers=headers)
resp.raise_for_status()
lh_gold_id = None
for lh in resp.json().get("value", []):
    if lh["displayName"] == "lh_gold_curated":
        lh_gold_id = lh["id"]
        break
if not lh_gold_id:
    print("  [FAIL] lh_gold_curated not found -- run pipeline first")
    raise RuntimeError("lh_gold_curated not found")
print(f"  Lakehouse: lh_gold_curated ({lh_gold_id})")

# -- Paths -----------------------------------------------------
ONTOLOGY_NAME = "Healthcare_Demo_Ontology_HLS"
GRAPH_MODEL_NAME = "Healthcare_Demo_Graph"
ONT_API = f"{API}/workspaces/{workspace_id}/ontologies"
GM_API = f"{API}/workspaces/{workspace_id}/graphModels"

# Find the extracted repo -- launcher extracts ZIP to a subdirectory
# e.g. .lakehouse/default/Files/src/Fabric-Payer-Provider-HealthCare-Demo-main/
ont_dir = None
for base in [".lakehouse/default/Files/src", "/lakehouse/default/Files/src"]:
    if not os.path.isdir(base):
        continue
    # Check direct: base/ontology/ONTOLOGY_NAME
    direct = os.path.join(base, "ontology", ONTOLOGY_NAME)
    if os.path.isdir(direct):
        ont_dir = direct
        break
    # Check one level down (extracted repo subdirectory)
    for sub in os.listdir(base):
        nested = os.path.join(base, sub, "ontology", ONTOLOGY_NAME)
        if os.path.isdir(nested):
            ont_dir = nested
            break
    if ont_dir:
        break

if not ont_dir:
    print("  [WARN] Ontology dir not found on lakehouse filesystem")
    print(f"  CWD: {os.getcwd()}")
    for p in [".lakehouse", "/lakehouse", ".lakehouse/default", "/lakehouse/default"]:
        print(f"    {p} exists: {os.path.exists(p)}")
    for base in [".lakehouse/default/Files/src", "/lakehouse/default/Files/src"]:
        if os.path.isdir(base):
            print(f"  Contents of {base}: {os.listdir(base)[:10]}")
    # Fallback: download ontology files from GitHub to a temp directory
    import tempfile
    print(f"  Downloading ontology from GitHub: {GITHUB_OWNER}/{GITHUB_REPO}@{GITHUB_BRANCH} ...")
    raw_base = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/ontology/{ONTOLOGY_NAME}"
    r_manifest = requests.get(f"{raw_base}/manifest.json")
    r_manifest.raise_for_status()
    manifest = r_manifest.json()
    ont_dir = tempfile.mkdtemp(prefix="ontology_")
    with open(os.path.join(ont_dir, "manifest.json"), "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2)
    dl_count = 0
    for part_info in manifest.get("exportedParts", []):
        part_path = part_info["path"]
        r_part = requests.get(f"{raw_base}/{part_path}")
        r_part.raise_for_status()
        dest = os.path.join(ont_dir, part_path.replace("/", os.sep))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as pf:
            pf.write(r_part.content)
        dl_count += 1
    print(f"  Downloaded {dl_count} files to temp dir: {ont_dir}")
else:
    print(f"  Ontology dir: {ont_dir}")

# -- Helper: LRO wait -----------------------------------------
def wait_lro(response, label, timeout=180):
    loc = response.headers.get("Location")
    if not loc:
        time.sleep(10)
        return True
    start = time.time()
    retry = int(response.headers.get("Retry-After", 5))
    while time.time() - start < timeout:
        time.sleep(retry)
        r = requests.get(loc, headers=headers)
        if r.status_code == 200:
            body = r.json()
            status = body.get("status", "")
            if status == "Succeeded":
                return True
            if status in ("Failed", "Cancelled"):
                err = body.get("error", {})
                err_code = err.get("code", "")
                err_msg = err.get("message", "")
                print(f"    [FAIL] {label}: {status}")
                if err_code or err_msg:
                    print(f"    Error: {err_code} - {err_msg[:500]}")
                err_details = err.get("details", [])
                if err_details:
                    print(f"    Details: {json.dumps(err_details, indent=2)[:1000]}")
                if not err_code and not err_msg and not err_details:
                    print(f"    Response: {json.dumps(body, indent=2)[:500]}")
                return False
    print(f"    [FAIL] {label}: timed out after {timeout}s")
    return False

# -- Helper: Load ontology parts from disk ---------------------
def load_ontology_parts(base_path):
    parts = []
    manifest_path = os.path.join(base_path, "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r', encoding='utf-8-sig') as f:
            manifest = json.load(f)
        for part_info in manifest.get("exportedParts", []):
            part_path = part_info["path"]
            file_path = os.path.join(base_path, part_path)
            if not os.path.exists(file_path):
                continue
            with open(file_path, 'rb') as f:
                raw = f.read()
            if raw.startswith(b'\xef\xbb\xbf'):
                raw = raw[3:]
            parts.append({"path": part_path, "payload": base64.b64encode(raw).decode("utf-8"), "payloadType": "InlineBase64"})
    else:
        for root, _dirs, files in sorted(os.walk(base_path)):
            for fname in sorted(files):
                if fname in (".platform", "manifest.json"):
                    continue
                filepath = os.path.join(root, fname)
                rel_path = os.path.relpath(filepath, base_path).replace("\\", "/")
                with open(filepath, 'rb') as f:
                    raw = f.read()
                if raw.startswith(b'\xef\xbb\xbf'):
                    raw = raw[3:]
                parts.append({"path": rel_path, "payload": base64.b64encode(raw).decode("utf-8"), "payloadType": "InlineBase64"})
    return parts

# -- Helper: Patch data binding IDs ----------------------------
def patch_bindings(parts, ws_id, lh_id):
    patched = []
    for part in parts:
        path = part["path"]
        if "DataBindings/" in path or "Contextualizations/" in path:
            try:
                content = base64.b64decode(part["payload"]).decode("utf-8")
                obj = json.loads(content)
                _patch_ids(obj, ws_id, lh_id)
                content = json.dumps(obj, indent=2, ensure_ascii=False)
                part = {**part, "payload": base64.b64encode(content.encode("utf-8")).decode("utf-8")}
            except Exception as e:
                print(f"    [WARN] Could not patch {path}: {e}")
        patched.append(part)
    return patched

def _patch_ids(obj, ws_id, lh_id):
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            val = obj[key]
            lk = key.lower()
            if lk in ("workspaceid", "workspaceguid", "workspace_id"):
                obj[key] = ws_id
            elif lk in ("itemid", "lakehouseid", "artifactid", "item_id"):
                obj[key] = lh_id
            elif isinstance(val, str) and "onelake" in val.lower():
                m = re.match(r'(abfss://)([0-9a-f-]+)(@onelake[^/]*/)([0-9a-f-]+)(.*)', val, re.I)
                if m:
                    obj[key] = f"{m.group(1)}{ws_id}{m.group(3)}{lh_id}{m.group(5)}"
            elif isinstance(val, (dict, list)):
                _patch_ids(val, ws_id, lh_id)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                _patch_ids(item, ws_id, lh_id)

# ==============================================================
# STEP 1: DEPLOY ONTOLOGY
# ==============================================================
print()
print("Step 1: Deploy Ontology")
print("-" * 40)

# Load parts
parts = load_ontology_parts(ont_dir)
et_count = sum(1 for p in parts if p["path"].startswith("EntityTypes/") and p["path"].endswith("/definition.json"))
rt_count = sum(1 for p in parts if p["path"].startswith("RelationshipTypes/") and p["path"].endswith("/definition.json"))
print(f"  Loaded {len(parts)} parts: {et_count} entities, {rt_count} relationships")

# Patch data bindings
parts = patch_bindings(parts, workspace_id, lh_gold_id)
print(f"  Patched data bindings for target environment")

# -- Pre-deploy Validation: verify bindings match actual table schemas ------
print()
print("  Pre-deploy validation (bindings vs table schemas)...")
_val_errors = []
_val_fixes = []

# Helper: get table columns using Delta path (no default lakehouse needed)
_table_cols_cache = {}
def _get_table_cols(table_name):
    if table_name in _table_cols_cache:
        return _table_cols_cache[table_name]
    cols = None
    # Try 1: Spark SQL (works if default lakehouse is attached)
    try:
        _df = spark.sql(f"DESCRIBE lh_gold_curated.{table_name}")
        cols = {r["col_name"] for r in _df.collect() if not r["col_name"].startswith("#")}
    except Exception:
        pass
    # Try 2: Read Delta schema via OneLake path (no default lakehouse needed)
    if cols is None:
        try:
            _path = f"abfss://{workspace_id}@onelake.dfs.fabric.microsoft.com/{lh_gold_id}/Tables/{table_name}"
            _df = spark.read.format("delta").load(_path)
            cols = {f.name for f in _df.schema.fields}
        except Exception:
            pass
    _table_cols_cache[table_name] = cols
    return cols

# Test if we can reach any table at all
_sample_table = None
for _p in parts:
    _pp = _p["path"]
    if "DataBindings/" in _pp:
        try:
            _b = json.loads(base64.b64decode(_p["payload"]).decode("utf-8"))
            _sample_table = _b.get("dataBindingConfiguration", {}).get("sourceTableProperties", {}).get("sourceTableName")
            if _sample_table:
                break
        except Exception:
            pass
_can_validate = _get_table_cols(_sample_table) is not None if _sample_table else False
if not _can_validate:
    print("  [INFO] Table schemas not accessible (no default lakehouse context)")
    print("         Skipping column validation -- ontology push will proceed")
    print("         The binding structure and property-name consistency will still be checked")

# Build lookup: decode definition.json and DataBinding parts
_entity_defs = {}   # entity_folder_id -> definition dict
_entity_bindings = {}  # entity_folder_id -> binding dict
for _p in parts:
    _pp = _p["path"]
    if _pp.startswith("EntityTypes/") and _pp.endswith("/definition.json"):
        _folder_id = _pp.split("/")[1]
        try:
            _entity_defs[_folder_id] = json.loads(base64.b64decode(_p["payload"]).decode("utf-8"))
        except Exception:
            pass
    elif "DataBindings/" in _pp and _pp.startswith("EntityTypes/"):
        _folder_id = _pp.split("/")[1]
        try:
            _entity_bindings[_folder_id] = json.loads(base64.b64decode(_p["payload"]).decode("utf-8"))
        except Exception:
            pass

# Validate each entity: property names vs binding sourceColumnNames vs actual table columns
for _folder_id, _defn in _entity_defs.items():
    _ename = _defn.get("name", _folder_id)
    _bnd = _entity_bindings.get(_folder_id)
    if not _bnd:
        continue
    _cfg = _bnd.get("dataBindingConfiguration", {})
    _src_table = (_cfg.get("sourceTableProperties", {}).get("sourceTableName"))
    if not _src_table:
        continue

    # Get actual table columns (Spark SQL or Delta path)
    _actual_cols = _get_table_cols(_src_table) if _can_validate else None

    # Build property id -> name lookup from definition
    _prop_id_to_name = {p["id"]: p["name"] for p in _defn.get("properties", [])}

    # Check each binding
    for _pb in _cfg.get("propertyBindings", []):
        _src_col = _pb["sourceColumnName"]
        _target_pid = _pb["targetPropertyId"]
        _prop_name = _prop_id_to_name.get(_target_pid, "?")

        # Check 1: sourceColumnName must exist in actual table (only if we can validate)
        if _actual_cols is not None and _src_col not in _actual_cols:
            _val_errors.append(f"  {_ename}: binding column '{_src_col}' not in {_src_table} (actual: {sorted(_actual_cols)[:8]}...)")

        # Check 2: property name should match sourceColumnName for auto-provisioned graph
        # Skip columns starting with '_' (metadata/system cols like _load_timestamp)
        if _prop_name != _src_col and _prop_name != "?" and not _src_col.startswith("_"):
            _val_fixes.append((_folder_id, _target_pid, _prop_name, _src_col, _ename))

# Auto-fix property name mismatches in parts (in memory)
if _val_fixes:
    print(f"  Found {len(_val_fixes)} property name mismatches -- auto-fixing in parts...")
    _fix_lookup = {}  # (folder_id, prop_id) -> new_name
    for _folder_id, _pid, _old, _new, _ename in _val_fixes:
        _fix_lookup[(_folder_id, _pid)] = _new
        print(f"    {_ename}: '{_old}' -> '{_new}'")

    # Patch definition.json parts in memory
    for _pi, _p in enumerate(parts):
        _pp = _p["path"]
        if not (_pp.startswith("EntityTypes/") and _pp.endswith("/definition.json")):
            continue
        _folder_id = _pp.split("/")[1]
        _needs_fix = any(fid == _folder_id for (fid, _) in _fix_lookup)
        if not _needs_fix:
            continue
        try:
            _d = json.loads(base64.b64decode(_p["payload"]).decode("utf-8"))
            _changed = False
            for _prop in _d.get("properties", []):
                _key = (_folder_id, _prop["id"])
                if _key in _fix_lookup:
                    _prop["name"] = _fix_lookup[_key]
                    _changed = True
            if _changed:
                parts[_pi] = {**_p, "payload": base64.b64encode(
                    json.dumps(_d, indent=2, ensure_ascii=False).encode("utf-8")
                ).decode("utf-8")}
        except Exception:
            pass

# Validate contextualization columns (only if tables are accessible)
_ctx_errors = []
if _can_validate:
    for _p in parts:
        _pp = _p["path"]
        if "Contextualizations/" not in _pp:
            continue
        try:
            _ctx = json.loads(base64.b64decode(_p["payload"]).decode("utf-8"))
            _ctx_table = _ctx.get("dataBindingTable", {}).get("sourceTableName")
            if not _ctx_table:
                continue
            _ctx_cols = _get_table_cols(_ctx_table)
            if _ctx_cols is None:
                _ctx_errors.append(f"  Contextualization table {_ctx_table} not accessible")
                continue
            for _sk in _ctx.get("sourceKeyRefBindings", []):
                if _sk["sourceColumnName"] not in _ctx_cols:
                    _ctx_errors.append(f"  {_ctx_table}: sourceKey '{_sk['sourceColumnName']}' not in columns")
            for _tk in _ctx.get("targetKeyRefBindings", []):
                if _tk["sourceColumnName"] not in _ctx_cols:
                    _ctx_errors.append(f"  {_ctx_table}: targetKey '{_tk['sourceColumnName']}' not in columns")
        except Exception:
            pass

# Print validation results
if _val_errors:
    print(f"  *** BINDING VALIDATION ERRORS ({len(_val_errors)}) ***")
    for _ve in _val_errors:
        print(f"    {_ve}")
if _ctx_errors:
    print(f"  *** CONTEXTUALIZATION ERRORS ({len(_ctx_errors)}) ***")
    for _ce in _ctx_errors:
        print(f"    {_ce}")
if not _val_errors and not _ctx_errors:
    fixes_msg = f" ({len(_val_fixes)} auto-fixed)" if _val_fixes else ""
    print(f"  All bindings and contextualizations validated OK{fixes_msg}")

# Check if ontology already exists
ont_id = None
r = requests.get(ONT_API, headers=headers)
if r.status_code == 200:
    for o in r.json().get("value", []):
        if o["displayName"] == ONTOLOGY_NAME:
            ont_id = o["id"]
            print(f"  Already exists (ID: {ont_id}) -- will update definition")
            break

# Fallback: try items endpoint
if not ont_id and r.status_code != 200:
    r2 = requests.get(f"{API}/workspaces/{workspace_id}/items?type=Ontology", headers=headers)
    if r2.status_code == 200:
        for o in r2.json().get("value", []):
            if o["displayName"] == ONTOLOGY_NAME:
                ont_id = o["id"]
                break

if not ont_id:
    # Create new ontology
    create_body = {
        "displayName": ONTOLOGY_NAME,
        "description": f"Healthcare Ontology -- {et_count} entity types, {rt_count} relationships, bound to lh_gold_curated",
    }
    r = requests.post(ONT_API, headers=headers, json=create_body)
    if r.status_code in (200, 201):
        ont_id = r.json().get("id")
        print(f"  Created: {ont_id}")
    elif r.status_code == 202:
        wait_lro(r, "create ontology")
        time.sleep(3)
        r2 = requests.get(ONT_API, headers=headers)
        for o in r2.json().get("value", []):
            if o["displayName"] == ONTOLOGY_NAME:
                ont_id = o["id"]
                break
        print(f"  Created (async): {ont_id}")
    elif "AlreadyInUse" in (r.text or ""):
        r2 = requests.get(ONT_API, headers=headers)
        for o in r2.json().get("value", []):
            if o["displayName"] == ONTOLOGY_NAME:
                ont_id = o["id"]
                break
        print(f"  Found existing: {ont_id}")
    else:
        print(f"  [FAIL] Create ontology: HTTP {r.status_code} {r.text[:300]}")

ont_result = "[FAIL]"
if ont_id:
    # Push definition
    update_url = f"{ONT_API}/{ont_id}/updateDefinition"
    r = requests.post(update_url, headers=headers, json={"definition": {"parts": parts}})
    if r.status_code in (200, 201):
        print(f"  [OK] Definition pushed")
        ont_result = "[OK]"
    elif r.status_code == 202:
        ok = wait_lro(r, "updateDefinition")
        ont_result = "[OK]" if ok else "[FAIL]"
        print(f"  {'[OK]' if ok else '[FAIL]'} Definition push {'succeeded' if ok else 'failed'}")
    else:
        print(f"  [FAIL] updateDefinition: HTTP {r.status_code} {r.text[:300]}")

# -- Ontology Summary --
print()
print("=" * 60)
print(f"  ONTOLOGY: {ONTOLOGY_NAME:<38} {ont_result}")
print("=" * 60)

# -- Post-deploy: Deploy graph model via standalone notebook ----------
if ont_result == "[OK]":
    print()
    print("Step 2: Deploy Graph Model")
    print("-" * 40)

    # Ensure NB_Deploy_Graph_Model exists in the workspace with latest content
    token = notebookutils.credentials.getToken("pbi")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    _items_r = requests.get(f"{API}/workspaces/{workspace_id}/items?type=Notebook", headers=headers)
    _nb_id = None
    if _items_r.status_code == 200:
        for _it in _items_r.json().get("value", []):
            if _it["displayName"] == "NB_Deploy_Graph_Model":
                _nb_id = _it["id"]
                break

    # Always download latest notebook source from GitHub
    _py_url = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/payer-provider-healthcare/NB_Deploy_Graph_Model.Notebook/notebook-content.py"
    _py_r = requests.get(_py_url)

    if _py_r.status_code != 200:
        if _nb_id:
            print(f"  NB_Deploy_Graph_Model exists ({_nb_id}) -- using existing version")
        else:
            print(f"  [FAIL] Could not download notebook source: HTTP {_py_r.status_code}")
    else:
            # Convert .py -> ipynb (inline converter, self-contained)
            def _py_to_ipynb_mini(py_text):
                lines = py_text.split("\n")
                cells = []
                i = 0
                while i < len(lines) and lines[i].strip() in ("", "# Fabric notebook source"):
                    i += 1
                while i < len(lines):
                    if lines[i].startswith("# METADATA **"):
                        i += 1
                        while i < len(lines) and lines[i].strip() == "":
                            i += 1
                        if i >= len(lines):
                            break
                        if lines[i].startswith("# CELL **"):
                            ct = "code"
                        elif lines[i].startswith("# MARKDOWN **"):
                            ct = "markdown"
                        else:
                            i += 1; continue
                        i += 1
                        if i < len(lines) and lines[i].strip() == "":
                            i += 1
                        cl = []
                        while i < len(lines) and not lines[i].startswith("# METADATA **"):
                            cl.append(lines[i]); i += 1
                        while cl and cl[-1].strip() == "":
                            cl.pop()
                        if ct == "markdown":
                            cl = [(l[2:] if l.startswith("# ") else ("" if l == "#" else l)) for l in cl]
                        if cl:
                            src = [l + "\n" for l in cl[:-1]] + [cl[-1]]
                            c = {"cell_type": ct, "metadata": {}, "source": src}
                            if ct == "code":
                                c["outputs"] = []; c["execution_count"] = None
                            cells.append(c)
                    else:
                        i += 1
                nb = {"nbformat": 4, "nbformat_minor": 5,
                      "metadata": {"kernel_info": {"name": "synapse_pyspark"},
                                   "kernelspec": {"name": "synapse_pyspark", "display_name": "Synapse PySpark"},
                                   "language_info": {"name": "python"}},
                      "cells": cells}
                return json.dumps(nb, indent=1, ensure_ascii=False)

            _ipynb_str = _py_to_ipynb_mini(_py_r.text)
            _ipynb_b64 = base64.b64encode(_ipynb_str.encode("utf-8")).decode("utf-8")
            _ipynb_parts = [{"path": "notebook-content.ipynb", "payload": _ipynb_b64, "payloadType": "InlineBase64"}]

            if _nb_id:
                # Notebook exists -- update its definition with latest code
                print(f"  Updating NB_Deploy_Graph_Model ({_nb_id}) with latest code...")
                _upd_body = {"definition": {"format": "ipynb", "parts": _ipynb_parts}}
                _ur = requests.post(f"{API}/workspaces/{workspace_id}/items/{_nb_id}/updateDefinition",
                                    headers=headers, json=_upd_body)
                if _ur.status_code == 202:
                    _uloc = _ur.headers.get("Location", "")
                    if _uloc:
                        for _ui in range(30):
                            time.sleep(2)
                            _ulr = requests.get(_uloc, headers=headers)
                            if _ulr.status_code == 200:
                                break
                print(f"  Definition updated")
            else:
                # Create new notebook
                print("  NB_Deploy_Graph_Model not in workspace -- creating...")
                _create_body = {
                    "displayName": "NB_Deploy_Graph_Model",
                    "type": "Notebook",
                    "definition": {
                        "format": "ipynb",
                        "parts": _ipynb_parts
                    }
                }
                _cr = requests.post(f"{API}/workspaces/{workspace_id}/items", headers=headers, json=_create_body)
                if _cr.status_code in (200, 201):
                    _nb_id = _cr.json().get("id")
                    print(f"  Created: {_nb_id}")
                elif _cr.status_code == 202:
                    _loc = _cr.headers.get("Location", "")
                    if _loc:
                        for _li in range(30):
                            time.sleep(3)
                            _lr = requests.get(_loc, headers=headers)
                            if _lr.status_code == 200:
                                _lrb = _lr.json()
                                if _lrb.get("status", "").lower() in ("succeeded", "completed"):
                                    break
                                elif _lrb.get("status", "").lower() in ("failed", "cancelled"):
                                    break
                    # Re-fetch to get ID
                    _items_r2 = requests.get(f"{API}/workspaces/{workspace_id}/items?type=Notebook", headers=headers)
                    if _items_r2.status_code == 200:
                        for _it in _items_r2.json().get("value", []):
                            if _it["displayName"] == "NB_Deploy_Graph_Model":
                                _nb_id = _it["id"]
                                break
                    if _nb_id:
                        print(f"  Created (async): {_nb_id}")
                        # Push definition explicitly (Create + 202 may not apply inline def)
                        _upd_body = {"definition": {"format": "ipynb", "parts": _ipynb_parts}}
                        _ur = requests.post(f"{API}/workspaces/{workspace_id}/items/{_nb_id}/updateDefinition",
                                            headers=headers, json=_upd_body)
                        if _ur.status_code == 202:
                            _uloc = _ur.headers.get("Location", "")
                            if _uloc:
                                for _ui in range(30):
                                    time.sleep(2)
                                    _ulr = requests.get(_uloc, headers=headers)
                                    if _ulr.status_code == 200:
                                        break
                        print(f"  Definition pushed")
                else:
                    print(f"  [FAIL] Create notebook: HTTP {_cr.status_code} {_cr.text[:300]}")

                if _nb_id:
                    print("  Waiting 15s for Fabric to index the notebook...")
                    time.sleep(15)

    if _nb_id:
        print(f"  Running NB_Deploy_Graph_Model notebook...")
        print(f"  (validates bindings, builds graph definition, deploys,")
        print(f"   waits for data load, runs smoke tests)")
        print()
        try:
            notebookutils.notebook.run("NB_Deploy_Graph_Model", 600, {"useRootDefaultLakehouse": True})
            graph_st = "[OK]"
            print()
            print(f"  [OK] NB_Deploy_Graph_Model completed successfully")
        except Exception as _gm_err:
            if "mssparkutilsrun-result+json" in str(_gm_err) or "NoSuchElementException" in str(_gm_err):
                graph_st = "[OK]"
                print()
                print(f"  [OK] NB_Deploy_Graph_Model completed (ignoring Fabric result-parse bug)")
            else:
                graph_st = "[FAIL]"
                _gm_err_str = str(_gm_err)
                print()
                if "404" in _gm_err_str or "not found" in _gm_err_str.lower():
                    print(f"  [FAIL] Fabric cannot find NB_Deploy_Graph_Model (may need more time to index)")
                    print(f"         Wait 1-2 minutes, then run NB_Deploy_Graph_Model manually from the workspace")
                else:
                    print(f"  [FAIL] NB_Deploy_Graph_Model failed: {_gm_err_str[:500]}")
                    print(f"         Open NB_Deploy_Graph_Model manually for detailed diagnostics")
    else:
        graph_st = "[FAIL]"
        print(f"  [FAIL] Could not create NB_Deploy_Graph_Model in workspace")
        print(f"         Deploy it manually from the workspace folder, then run it")

    print()
    print("=" * 60)
    print(f"  ONTOLOGY:    {ONTOLOGY_NAME:<36} {ont_result}")
    print(f"  GRAPH:       NB_Deploy_Graph_Model{' ':>16} {graph_st}")
    print("=" * 60)

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# CELL 6 — Patch Data Agent sources with real workspace artifact IDs
# ============================================================================
# The Jumpstart installer deploys the DataAgent from the repo's exported definition,
# but datasource.json files contain placeholder IDs:
#   artifactId:  a1000001-0001-0001-0001-000000000004
#   workspaceId: 00000000-0000-0000-0000-000000000000
#
# This cell patches those placeholders with the REAL lakehouse and semantic
# model IDs discovered at runtime, then pushes the updated definition.
# Also adds dataSourceInstructions to the semantic model datasource.
# ============================================================================

import requests, json, base64, time, os

print("Patching Data Agent sources with real IDs...\n")

token = notebookutils.credentials.getToken("pbi")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
api_base = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}"

# --- 1. Find the DataAgent and data sources in workspace ---
resp = requests.get(f"{api_base}/items", headers=headers)
items = resp.json().get("value", []) if resp.status_code == 200 else []

agent_id = None
lh_gold_id = None
sm_id = None

for item in items:
    if item["type"] == "DataAgent" and item["displayName"] == "HealthcareHLSAgent":
        agent_id = item["id"]
    elif item["type"] == "Lakehouse" and item["displayName"] == "lh_gold_curated":
        lh_gold_id = item["id"]
    elif item["type"] == "SemanticModel" and item["displayName"] == "HealthcareDemoHLS":
        sm_id = item["id"]

if not agent_id:
    print("[SKIP] HealthcareHLSAgent not found in workspace")
elif not lh_gold_id:
    print("[SKIP] lh_gold_curated lakehouse not found")
else:
    print(f"  Agent:          {agent_id}")
    print(f"  Lakehouse:      {lh_gold_id}")
    print(f"  Semantic Model: {sm_id or '(not found -- will skip SM source)'}")

    # --- 2. Get current agent definition ---
    get_def_url = f"{api_base}/DataAgents/{agent_id}/getDefinition"
    r = requests.post(get_def_url, headers=headers)
    print(f"  getDefinition: HTTP {r.status_code}")

    parts = None
    if r.status_code == 200:
        parts = r.json().get("definition", {}).get("parts", [])
    elif r.status_code == 202:
        # LRO -- poll for completion
        op_url = r.headers.get("Location", "")
        retry_after = int(r.headers.get("Retry-After", 5))
        for _ in range(60):
            time.sleep(retry_after)
            op_r = requests.get(op_url, headers=headers)
            if op_r.status_code == 200:
                body = op_r.json()
                if body.get("status") == "Succeeded":
                    # Try resourceLocation first, then /result
                    res_loc = body.get("resourceLocation", "")
                    for result_url in [f"{op_url}/result", res_loc]:
                        if not result_url:
                            continue
                        rr = requests.get(result_url, headers=headers)
                        if rr.status_code == 200:
                            p = rr.json().get("definition", {}).get("parts", [])
                            if p:
                                parts = p
                                break
                    if not parts:
                        # Body itself might have parts
                        parts = body.get("definition", {}).get("parts", [])
                    break
                elif body.get("status") in ("Failed", "Cancelled"):
                    print(f"  [FAIL] getDefinition LRO: {body.get('status')}")
                    break
    else:
        print(f"  [FAIL] getDefinition: {r.status_code} {r.text[:200]}")

    if not parts:
        print("  [FAIL] Could not get agent definition parts")
    else:
        print(f"  Definition parts: {len(parts)}")

        # --- 3. Mapping: datasource displayName -> real IDs ---
        ds_type_map = {
            "lakehouse_tables": {"artifactId": lh_gold_id, "workspaceId": workspace_id},
        }
        if sm_id:
            ds_type_map["semantic_model"] = {"artifactId": sm_id, "workspaceId": workspace_id}

        # --- 4. Patch datasource.json parts ---
        patched_count = 0
        patched_parts = []

        for part in parts:
            part_path = part.get("path", "")
            payload = part.get("payload", "")
            payload_type = part.get("payloadType", "InlineBase64")

            if "datasource.json" in part_path and payload_type == "InlineBase64" and payload:
                try:
                    content = base64.b64decode(payload).decode("utf-8")
                    ds = json.loads(content)
                    ds_name = ds.get("displayName", "")
                    ds_type = ds.get("type", "")
                    old_artifact = ds.get("artifactId", "")
                    old_workspace = ds.get("workspaceId", "")

                    if ds_type in ds_type_map:
                        new_ids = ds_type_map[ds_type]
                        new_artifact = new_ids["artifactId"]
                        new_workspace = new_ids["workspaceId"]

                        if old_artifact != new_artifact:
                            print(f"    Patch {ds_name} artifactId: {old_artifact[:20]}... -> {new_artifact[:20]}...")
                            ds["artifactId"] = new_artifact
                        if old_workspace != new_workspace:
                            print(f"    Patch {ds_name} workspaceId: {old_workspace[:20]}... -> {new_workspace[:20]}...")
                            ds["workspaceId"] = new_workspace

                        content = json.dumps(ds, indent=2, ensure_ascii=False)
                        payload = base64.b64encode(content.encode("utf-8")).decode("utf-8")
                        patched_count += 1
                    else:
                        # Preserve datasource types we don't need to patch (e.g., graph sources configured via UI)
                        zero_guid = "00000000-0000-0000-0000-000000000000"
                        if ds.get("artifactId", "") == zero_guid or ds.get("workspaceId", "") == zero_guid:
                            print(f"    [DROP] {ds_name} ({ds_type}) -- unpatched placeholder GUIDs, removing from definition")
                            continue
                        else:
                            print(f"    [KEEP] {ds_name} ({ds_type}) -- already has valid IDs, preserving")
                except Exception as e:
                    print(f"    [WARN] Could not patch {part_path}: {e}")

            patched_parts.append({
                "path": part_path,
                "payload": payload,
                "payloadType": payload_type,
            })

        print(f"  Patched {patched_count} datasource files")

        # --- 5. Push updated definition ---
        if patched_count > 0:
            update_url = f"{api_base}/DataAgents/{agent_id}/updateDefinition"
            update_body = {"definition": {"parts": patched_parts}}
            r = requests.post(update_url, headers=headers, json=update_body)
            print(f"  updateDefinition: HTTP {r.status_code}")

            if r.status_code == 200:
                print("  [OK] Agent definition updated successfully")
            elif r.status_code == 202:
                # LRO -- wait for completion
                op_url = r.headers.get("Location", "")
                retry_after = int(r.headers.get("Retry-After", 5))
                for _ in range(60):
                    time.sleep(retry_after)
                    op_r = requests.get(op_url, headers=headers)
                    if op_r.status_code == 200:
                        body = op_r.json()
                        if body.get("status") == "Succeeded":
                            print("  [OK] Agent definition updated (LRO succeeded)")
                            break
                        elif body.get("status") in ("Failed", "Cancelled"):
                            err = body.get("error", {}).get("message", "")
                            print(f"  [FAIL] updateDefinition LRO: {body.get('status')} -- {err}")
                            break
                else:
                    print("  [WARN] updateDefinition LRO timed out")
            else:
                print(f"  [FAIL] updateDefinition: {r.text[:300]}")
        else:
            print("  [SKIP] No datasource files needed patching")

print("\nData Agent source patching complete.")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# CELL 7 — Deploy Real-Time Intelligence (RTI) streaming topology
# ============================================================================
# Eventhouse + KQL Database are already deployed as Git artifacts (Stage 2).
# This cell:
#   1. Patches RTI notebooks with lakehouse metadata
#   2. Runs NB_RTI_Setup_Eventhouse (creates KQL tables, discovers Kusto URI)
#   3. Wires Eventstream full topology via API:
#      Custom Endpoint → Stream → Eventhouse + Lakehouse + Activator
#   4. Prints instruction: copy connection string from portal
#
# After this cell, the user:
#   - Copies the connection string from the Eventstream portal
#   - Pastes it into NB_RTI_Event_Simulator → ES_CONNECTION_STRING
#   - Runs NB_RTI_Event_Simulator → events stream continuously
#   - Then runs scoring notebooks (Fraud, Care Gap, HighCost) on the live data
# ============================================================================

if DEPLOY_STREAMING:
    print("=" * 60)
    print("  REAL-TIME INTELLIGENCE DEPLOYMENT")
    print("=" * 60)

    # -- Attach lh_gold_curated to RTI notebooks -------------------------
    # Notebooks run via notebookutils.notebook.run() do not inherit the
    # caller's lakehouse context.  The child notebook MUST either have a matching default
    # lakehouse in its metadata, otherwise Fabric blocks ALL Spark SQL
    # with "No default context found" or "Cannot reference a Notebook that attaching to a different default lakehouse".
    # We patch each notebook's ipynb definition here before running them.
    # ---------------------------------------------------------------------
    import requests, base64, time as _time

    _token = notebookutils.credentials.getToken("pbi")
    _hdrs = {"Authorization": f"Bearer {_token}", "Content-Type": "application/json"}
    _api = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}"

    # Get all workspace items
    _items_resp = requests.get(f"{_api}/items", headers=_hdrs)
    _name_to_id = {(it["type"], it["displayName"]): it["id"] for it in _items_resp.json().get("value", [])}
    _lh_id = _name_to_id.get(("Lakehouse", "lh_gold_curated"), "")

    _lh_deps = {
        "lakehouse": {
            "default_lakehouse": _lh_id,
            "default_lakehouse_name": "lh_gold_curated",
            "default_lakehouse_workspace_id": workspace_id,
            "known_lakehouses": [
                {"id": _lh_id, "displayName": "lh_gold_curated", "isDefault": True}
            ],
        }
    }

    _needs_lh = ["NB_RTI_Setup_Eventhouse", "NB_RTI_Event_Simulator",
                 "NB_RTI_Fraud_Detection", "NB_RTI_Care_Gap_Alerts",
                 "NB_RTI_HighCost_Trajectory"]

    def _get_nb_definition(nb_id, hdrs, api_base):
        """Get notebook definition in ipynb format, handling LRO."""
        # Use notebook-specific endpoint with explicit ipynb format
        url = f"{api_base}/notebooks/{nb_id}/getDefinition?format=ipynb"
        r = requests.post(url, headers=hdrs)
        print(f"      getDefinition: HTTP {r.status_code}")

        if r.status_code == 200:
            return r.json()

        if r.status_code != 202:
            print(f"      Unexpected status: {r.text[:200]}")
            return None

        # LRO - poll operation status
        loc = r.headers.get("Location", "")
        retry_secs = int(r.headers.get("Retry-After", "2"))
        if not loc:
            print(f"      No Location header in 202 response")
            return None

        print(f"      LRO polling ({retry_secs}s interval)...")
        for attempt in range(60):
            _time.sleep(retry_secs)
            poll_r = requests.get(loc, headers=hdrs)
            if poll_r.status_code == 202:
                continue
            if poll_r.status_code != 200:
                print(f"      LRO poll: HTTP {poll_r.status_code}")
                return None

            body = poll_r.json()
            status = body.get("status", "")
            if status == "Running" or status == "NotStarted":
                continue
            if status != "Succeeded":
                print(f"      LRO status: {status}")
                return None

            # LRO succeeded - fetch the actual result
            # Try {loc}/result FIRST (most reliable)
            result_url = f"{loc}/result"
            print(f"      LRO succeeded, fetching /result...")
            result_r = requests.get(result_url, headers=hdrs)
            if result_r.status_code == 200:
                result_body = result_r.json()
                parts = result_body.get("definition", {}).get("parts", [])
                if not parts:
                    parts = result_body.get("parts", [])
                if parts:
                    print(f"      Got {len(parts)} parts from /result")
                    return result_body

            # Try resourceLocation (sometimes points to item URL, not definition)
            res_loc = body.get("resourceLocation", "")
            if res_loc and res_loc != result_url:
                print(f"      Trying resourceLocation...")
                res_r = requests.get(res_loc, headers=hdrs)
                if res_r.status_code == 200:
                    res_body = res_r.json()
                    parts = res_body.get("definition", {}).get("parts", [])
                    if not parts:
                        parts = res_body.get("parts", [])
                    if parts:
                        print(f"      Got {len(parts)} parts from resourceLocation")
                        return res_body

            # Try the poll body itself (some APIs embed result in final status)
            parts = body.get("definition", {}).get("parts", [])
            if not parts:
                parts = body.get("parts", [])
            if parts:
                print(f"      Got {len(parts)} parts from poll body")
                return body

            print(f"      WARNING: LRO succeeded but no parts found in any endpoint")
            return None

        print(f"      LRO timed out after 60 polls")
        return None

    def _convert_pip_cells(nb_json):
        """Convert %pip/%conda cells to subprocess + module reload equivalents.

        Fabric blocks %pip/%conda magic in child notebooks called via
        notebookutils.notebook.run(). Converting to subprocess calls
        achieves the same package installation and works in child notebooks.
        After install, purges azure.* from sys.modules so the new
        versions load on next import (subprocess doesn't restart kernel).
        Returns the number of cells converted.
        """
        if "cells" not in nb_json:
            return 0
        converted = 0
        for cell in nb_json["cells"]:
            src_text = "".join(cell.get("source", []))
            stripped = src_text.strip()
            if not stripped:
                continue
            lines = stripped.split("\n")
            if not all(
                line.strip().startswith(("%pip ", "%conda "))
                or line.strip() == ""
                for line in lines
            ):
                continue
            # Build subprocess equivalent
            new_lines = ["import subprocess, sys\n"]
            for line in lines:
                line = line.strip()
                if line.startswith("%pip install "):
                    pkgs = line[len("%pip install "):].split()
                    # Strip existing quotes to avoid double-quoting
                    pkgs = [p.strip("'\"") for p in pkgs]
                    pkg_str = ", ".join(f'"{p}"' for p in pkgs)
                    new_lines.append(
                        f'subprocess.check_call([sys.executable, "-m", "pip", "install", {pkg_str}])\n'
                    )
                elif line.startswith("%conda install "):
                    pkgs = line[len("%conda install "):].split()
                    pkgs = [p.strip("'\"") for p in pkgs]
                    pkg_str = ", ".join(f'"{p}"' for p in pkgs)
                    new_lines.append(
                        f'subprocess.check_call(["conda", "install", "-y", {pkg_str}])\n'
                    )
            # Purge cached azure.* modules so re-import picks up new versions
            new_lines.append("# Purge old azure modules so fresh versions load\n")
            new_lines.append("for _mod in sorted(sys.modules):\n")
            new_lines.append("    if _mod.startswith('azure'):\n")
            new_lines.append("        del sys.modules[_mod]\n")
            cell["source"] = new_lines
            cell["cell_type"] = "code"
            converted += 1
        return converted

    def _fix_subprocess_quotes(nb_json):
        """Fix double-quoted packages in already-converted subprocess cells.

        If a previous run converted %pip cells with a bug that produced
        ""pkg"" instead of "pkg", this pass cleans them up.
        Returns the number of cells fixed.
        """
        import re as _re
        if 'cells' not in nb_json:
            return 0
        fixed = 0
        for cell in nb_json['cells']:
            src_text = ''.join(cell.get('source', []))
            if 'subprocess.check_call' not in src_text:
                continue
            if '""' not in src_text:
                continue
            # Skip cells with triple-quote docstrings (regex would corrupt them)
            if '"""' in src_text:
                continue
            new_src = _re.sub(r'""([^"]+)""', r'"\1"', src_text)
            if new_src != src_text:
                parts = new_src.split('\n')
                cell['source'] = [ln + '\n' for ln in parts[:-1]] + [parts[-1]]
                fixed += 1
        return fixed

    def _fix_setDefaultLakehouse(nb_json):
        """Replace setDefaultLakehouse block with spark.sql monkey-patch fallback.
        When setDefaultLakehouse is unavailable, monkey-patch spark.sql to
        rewrite lh_gold_curated.table -> delta.`abfss://...table` so SQL
        queries resolve without a Fabric lakehouse context.
        """
        if 'cells' not in nb_json:
            return 0
        fixed = 0
        # The ABFSS monkey-patch block to inject
        _new_block = (
            '            if not _attached:\n'
            '                import re as _re_mod\n'
            '                _abfss = f"abfss://{_ws_id}@onelake.dfs.fabric.microsoft.com/{_lh_id}/Tables"\n'
            '                _orig_sql = spark.sql\n'
            '                def _patched_sql(query, _base=_abfss, _orig=_orig_sql):\n'
            '                    query = _re_mod.sub(\n'
            "                        r'\\blh_gold_curated\\.(\\w+)\\b',\n"
            "                        lambda m: f'delta.`{_base}/{m.group(1)}`',\n"
            '                        query\n'
            '                    )\n'
            '                    return _orig(query)\n'
            '                spark.sql = _patched_sql\n'
            '                # Also patch saveAsTable for DataFrame writes\n'
            '                from pyspark.sql import DataFrameWriter as _DFW\n'
            '                _orig_sat = _DFW.saveAsTable\n'
            '                def _patched_sat(self, name, _base=_abfss, _orig=_orig_sat, **kwargs):\n'
            "                    if name.startswith('lh_gold_curated.'):\n"
            "                        tbl = name.split('.', 1)[1]\n"
            "                        self.save(f'{_base}/{tbl}')\n"
            '                        return\n'
            '                    return _orig(self, name, **kwargs)\n'
            '                _DFW.saveAsTable = _patched_sat\n'
            '                # Also patch spark.table() for reading\n'
            '                _orig_table = spark.table\n'
            '                def _patched_table(name, _base=_abfss, _orig=_orig_table):\n'
            "                    if name.startswith('lh_gold_curated.'):\n"
            "                        tbl = name.split('.', 1)[1]\n"
            "                        return spark.read.format('delta').load(f'{_base}/{tbl}')\n"
            '                    return _orig(name)\n'
            '                spark.table = _patched_table\n'
            '                print(f"  Registered lh_gold_curated via ABFSS path rewriter ({_lh_id[:8]}...)")\n'
            '                _attached = True\n'
            '            if not _attached:'
        )
        # Patterns to detect and replace
        _old_patterns = [
            # Pattern 1: CREATE SCHEMA fallback
            (
                '            if not _attached:\n'
                '                _abfss = f"abfss://{_ws_id}@onelake.dfs.fabric.microsoft.com/{_lh_id}/Tables"\n'
                '                try:\n'
                "                    spark.sql(f\"CREATE SCHEMA IF NOT EXISTS lh_gold_curated LOCATION '{_abfss}'\")\n"
                '                    print(f"  Registered lh_gold_curated via ABFSS ({_lh_id[:8]}...)")\n'
                '                    _attached = True\n'
                '                except Exception as _ex:\n'
                '                    print(f"  ABFSS fallback failed: {_ex}")\n'
                '            if not _attached:'
            ),
            # Pattern 2: bare call (original, no try/except)
            (
                '            notebookutils.lakehouse.setDefaultLakehouse(_ws_id, _lh_id)\n'
                '            print(f"  Attached lh_gold_curated ({_lh_id[:8]}...)")'
            ),
            # Pattern 3: simple try/except AttributeError
            (
                '            try:\n'
                '                notebookutils.lakehouse.setDefaultLakehouse(_ws_id, _lh_id)\n'
                '                print(f"  Attached lh_gold_curated ({_lh_id[:8]}...)")\n'
                '            except AttributeError:\n'
                '                print(f"  lh_gold_curated found ({_lh_id[:8]}...) -- lakehouse set via notebook metadata")'
            ),
        ]
        _full_block = (
            '            _attached = False\n'
            '            try:\n'
            '                notebookutils.lakehouse.setDefaultLakehouse(_ws_id, _lh_id)\n'
            '                print(f"  Attached lh_gold_curated ({_lh_id[:8]}...)")\n'
            '                _attached = True\n'
            '            except (AttributeError, Exception):\n'
            '                pass\n'
            + _new_block
        )
        for cell in nb_json['cells']:
            src_text = ''.join(cell.get('source', []))
            if 'setDefaultLakehouse' not in src_text:
                continue
            if '_patched_table' in src_text:
                continue  # already has full monkey-patch (sql + saveAsTable + table)
            replaced = False
            for pattern in _old_patterns:
                if pattern in src_text:
                    if 'if not _attached' in pattern:
                        # Pattern 1: just replace the CREATE SCHEMA block
                        src_text = src_text.replace(pattern, _new_block)
                    else:
                        # Patterns 2/3: replace the whole call with full block
                        src_text = src_text.replace(pattern, _full_block)
                    replaced = True
                    break
            if replaced:
                parts = src_text.split('\n')
                cell['source'] = [ln + '\n' for ln in parts[:-1]] + [parts[-1]]
                fixed += 1
        return fixed

    if _lh_id:
        print(f"\n  Attaching lh_gold_curated ({_lh_id[:8]}...) to RTI notebooks...")
        for _nb_name in _needs_lh:
            _nb_id = _name_to_id.get(("Notebook", _nb_name))
            if not _nb_id:
                print(f"    {_nb_name}: not found in workspace, skipping")
                continue

            print(f"    {_nb_name}:")
            result = _get_nb_definition(_nb_id, _hdrs, _api)

            if result is None:
                print(f"      SKIP - could not get definition")
                continue

            # Extract parts from response (handle both nesting patterns)
            _defn = result.get("definition", result)
            _parts = _defn.get("parts", [])

            if not _parts:
                print(f"      SKIP - 0 parts in response")
                print(f"      Response keys: {list(result.keys())}")
                if "definition" in result:
                    print(f"      definition keys: {list(result['definition'].keys())}")
                continue

            print(f"      Parts: {[p.get('path','?') for p in _parts]}")

            # Find and patch the notebook content part
            _patched = False
            for _part in _parts:
                _path = _part.get("path", "")
                # Match ipynb content parts (various naming patterns)
                if _path.endswith(".ipynb") or "content" in _path.lower() or _path == "artifact.content.ipynb":
                    try:
                        _raw = base64.b64decode(_part["payload"]).decode("utf-8")
                        _nb_json = json.loads(_raw)
                        # Patch metadata with lakehouse dependency
                        _meta = _nb_json.setdefault("metadata", {})
                        _meta["trident"] = _lh_deps
                        _meta["dependencies"] = _lh_deps
                        # Strip %pip/%conda cells (blocked in notebook.run())
                        _converted = _convert_pip_cells(_nb_json)
                        _fixed_dq = _fix_subprocess_quotes(_nb_json)
                        _fix_setDefaultLakehouse(_nb_json)
                        _part["payload"] = base64.b64encode(
                            json.dumps(_nb_json).encode("utf-8")
                        ).decode("utf-8")
                        _patched = True
                        print(f"      Patched lakehouse into {_path}")
                        if _converted:
                            print(f"      Converted {_converted} %pip/%conda cell(s) to subprocess")
                            if _fixed_dq:
                                print(f"      Fixed {_fixed_dq} cell(s) with double-quoted packages")
                    except json.JSONDecodeError:
                        # Not JSON (probably .py format) -- skip this part
                        print(f"      {_path} is not JSON, trying next part...")
                        continue
                    except Exception as _ex:
                        print(f"      Failed to patch {_path}: {_ex}")
                        continue
                    break

            if not _patched:
                print(f"      Could not patch any part (no ipynb content found)")
                # As a last resort, try to find ANY JSON part we can decode
                for _part in _parts:
                    _path = _part.get("path", "")
                    if _path == ".platform":
                        continue
                    try:
                        _raw = base64.b64decode(_part["payload"]).decode("utf-8")
                        _nb_json = json.loads(_raw)
                        if "cells" in _nb_json or "nbformat" in _nb_json:
                            _meta = _nb_json.setdefault("metadata", {})
                            _meta["trident"] = _lh_deps
                            _meta["dependencies"] = _lh_deps
                            _converted = _convert_pip_cells(_nb_json)
                            _fixed_dq = _fix_subprocess_quotes(_nb_json)
                            _fix_setDefaultLakehouse(_nb_json)
                            _part["payload"] = base64.b64encode(
                                json.dumps(_nb_json).encode("utf-8")
                            ).decode("utf-8")
                            _patched = True
                            print(f"      Patched lakehouse into {_path} (by content detection)")
                            if _converted:
                                print(f"      Converted {_converted} %pip/%conda cell(s) to subprocess")
                                if _fixed_dq:
                                    print(f"      Fixed {_fixed_dq} cell(s) with double-quoted packages")
                            break
                    except Exception:
                        continue

            if not _patched:
                print(f"      SKIP - no patchable content part found")
                continue

            # Push updated definition back
            _update_body = {"definition": {"format": "ipynb", "parts": _parts}}
            _ur = requests.post(
                f"{_api}/notebooks/{_nb_id}/updateDefinition?updateMetadata=true",
                headers=_hdrs,
                json=_update_body,
            )
            if _ur.status_code == 200:
                print(f"      Lakehouse attached (200)")
            elif _ur.status_code == 202:
                _uloc = _ur.headers.get("Location", "")
                _update_ok = False
                if _uloc:
                    for _poll_i in range(30):
                        _time.sleep(2)
                        _pr = requests.get(_uloc, headers=_hdrs)
                        if _pr.status_code == 200:
                            _pstatus = _pr.json().get("status", "")
                            if _pstatus == "Succeeded":
                                _update_ok = True
                                break
                            elif _pstatus in ("Failed", "Cancelled"):
                                _perr = _pr.json().get("error", {})
                                print(f"      updateDefinition {_pstatus}: "
                                      f"{_perr.get('message', '')[:200]}")
                                break
                        elif _pr.status_code != 202:
                            # Non-standard status, assume done
                            _update_ok = True
                            break
                else:
                    _update_ok = True
                if _update_ok:
                    print(f"      Lakehouse attached (202->done)")
                else:
                    print(f"      updateDefinition may have failed "
                          f"-- notebook may not pick up lakehouse")
            else:
                print(f"      updateDefinition failed: HTTP {_ur.status_code} {_ur.text[:300]}")
    else:
        print("  WARNING: lh_gold_curated not found in workspace -- cannot attach lakehouse")

    # -- Run RTI notebooks ------------------------------------------------
    # Brief delay to let Fabric propagate the updateDefinition changes
    # (lakehouse metadata + %pip cell removal) before running child notebooks.
    print("\n  Waiting 15s for notebook metadata propagation...")
    _time.sleep(15)

    rti_notebooks = [
        "NB_RTI_Setup_Eventhouse",
    ]

    for nb_name in rti_notebooks:
        print(f"\n  Running {nb_name}...")
        try:
            notebookutils.notebook.run(nb_name, 1200, {"useRootDefaultLakehouse": True})
            print(f"  -> {nb_name}: OK")
        except Exception as e:
            if "mssparkutilsrun-result+json" in str(e) or "NoSuchElementException" in str(e):
                print(f"  -> {nb_name}: OK (ignoring Fabric result-parse bug)")
            else:
                print(f"  -> {nb_name}: FAILED -- {e}")
                print(f"    You can run this notebook manually from the workspace.")

    print("\n" + "=" * 60)
    print("  RTI DEPLOYMENT COMPLETE")
    print("=" * 60)
    print("  Delta tables in lh_gold_curated:")
    print("    - rti_claims_events, rti_adt_events, rti_rx_events")
    print("  RTI SETUP COMPLETE — Eventhouse + KQL tables ready")
    print()
    print("  KQL tables created in Healthcare_RTI_Eventhouse:")
    print("    - claims_events, adt_events, rx_events")
    print("    - fraud_scores, care_gap_alerts, highcost_alerts")
    print("    - rti_fraud_scores, rti_care_gap_alerts, rti_highcost_alerts")

    # ── Wire Eventstream — Full Topology via API ────────────────────
    # The Fabric REST API can create the Eventstream AND wire its full
    # topology: Custom Endpoint source → Default Stream → destinations.
    # The only manual step is copying the connection string from the
    # portal (CustomEndpointSourceProperties is empty in the API schema).
    #
    # Topology:
    #   CustomEndpoint (source)
    #       │
    #       ├──► Eventhouse / KQL DB     (real-time dashboards, scoring)
    #       ├──► Lakehouse (lh_bronze_raw) (raw archival, medallion)
    #       └──► Activator (Reflex)      (alerts — if item exists)
    # ─────────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  EVENTSTREAM — FULL TOPOLOGY WIRING VIA API")
    print("=" * 60)

    _es_name = "Healthcare_RTI_Eventstream"
    _es_id = None
    _bronze_lh_id = None
    _activator_id = None

    # Discover items needed for topology
    for item in items:
        _itype = item.get("type", "")
        _iname = item.get("displayName", "")
        if _itype == "Eventstream" and _iname == _es_name:
            _es_id = item["id"]
        elif _itype == "Lakehouse" and _iname == "lh_bronze_raw":
            _bronze_lh_id = item["id"]
        elif _itype == "Reflex":
            _activator_id = item["id"]
        _iname = item.get("displayName", "")
    # Create Eventstream if it doesn't exist
    if not _es_id:
        try:
            r = requests.post(
                f"{api_base}/items",
                headers=headers,
                json={"displayName": _es_name, "type": "Eventstream"}
            )
            if r.status_code in (200, 201):
                _es_id = r.json().get("id", "")
                print(f"  [OK] Created Eventstream: {_es_name} ({_es_id[:8]}...)")
            elif r.status_code == 202:
                _wait_for_lro(r, "createEventstream")
                r2 = requests.get(f"{api_base}/items?type=Eventstream", headers=headers)
                if r2.status_code == 200:
                    for it in r2.json().get("value", []):
                        if it["displayName"] == _es_name:
                            _es_id = it["id"]
                            break
                if _es_id:
                    print(f"  [OK] Created Eventstream (LRO): {_es_name} ({_es_id[:8]}...)")
            elif r.status_code == 409:
                r2 = requests.get(f"{api_base}/items?type=Eventstream", headers=headers)
                if r2.status_code == 200:
                    for it in r2.json().get("value", []):
                        if it["displayName"] == _es_name:
                            _es_id = it["id"]
                            break
                print(f"  [OK] Eventstream already exists ({_es_id[:8]}...)")
            else:
                print(f"  [WARN] Could not create Eventstream: HTTP {r.status_code}")
        except Exception as e:
            print(f"  [WARN] Eventstream creation failed: {e}")
    else:
        print(f"  [OK] Eventstream exists: {_es_id[:8]}...")

    if _es_id and kql_db_id:
        # ── Build Eventstream topology (single landing table) ───────
        # All events → rti_all_events. KQL update policies split into
        # rti_claims_events, rti_adt_events, rti_rx_events.
        print("\n  Building Eventstream topology...")

        _es_sources = [{
            "name": "HealthcareCustomEndpoint",
            "type": "CustomEndpoint",
            "properties": {}
        }]

        _es_streams = [{
            "name": "HealthcareRTI-stream",
            "type": "DefaultStream",
            "properties": {},
            "inputNodes": [{"name": "HealthcareCustomEndpoint"}]
        }]

        _kql_db_name = "Healthcare_RTI_DB"
        for item in items:
            if item.get("type") == "KQLDatabase":
                _kql_db_name = item["displayName"]
                break

        _es_destinations = [{
            "name": "HealthcareEventhouse",
            "type": "Eventhouse",
            "properties": {
                "dataIngestionMode": "ProcessedIngestion",
                "workspaceId": workspace_id,
                "itemId": kql_db_id,
                "databaseName": _kql_db_name,
                "tableName": "rti_all_events",
                "inputSerialization": {"type": "Json", "properties": {"encoding": "UTF8"}}
            },
            "inputNodes": [{"name": "HealthcareRTI-stream"}]
        }]
        print(f"    + Eventhouse: rti_all_events (KQL update policies split from here)")

        if _bronze_lh_id:
            _es_destinations.append({
                "name": "BronzeLakehouse",
                "type": "Lakehouse",
                "properties": {
                    "workspaceId": workspace_id,
                    "itemId": _bronze_lh_id,
                    "schema": "",
                    "deltaTable": "rti_raw_events",
                    "minimumRows": 1000,
                    "maximumDurationInSeconds": 120,
                    "inputSerialization": {"type": "Json", "properties": {"encoding": "UTF8"}}
                },
                "inputNodes": [{"name": "HealthcareRTI-stream"}]
            })
            print(f"    + Lakehouse: lh_bronze_raw → rti_raw_events")
        else:
            print(f"    - Lakehouse: lh_bronze_raw not found (skipping)")

        if _activator_id:
            _es_destinations.append({
                "name": "HealthcareActivator",
                "type": "Activator",
                "properties": {
                    "workspaceId": workspace_id,
                    "itemId": _activator_id,
                    "inputSerialization": {"type": "Json", "properties": {"encoding": "UTF8"}}
                },
                "inputNodes": [{"name": "HealthcareRTI-stream"}]
            })
            print(f"    + Activator: Healthcare Reflex")
        else:
            print(f"    - Activator: no Reflex item found")

        _es_def = {
            "sources": _es_sources,
            "destinations": _es_destinations,
            "streams": _es_streams,
            "operators": [],
            "compatibilityLevel": "1.1"
        }

        _dest_names = [d["name"] for d in _es_destinations]
        print(f"    Topology: CustomEndpoint → Stream → {' + '.join(_dest_names)}")
        # ── Push definition via updateDefinition API ────────────────
        print("\n  Pushing Eventstream definition...")
        _es_json_b64 = base64.b64encode(json.dumps(_es_def, indent=2).encode()).decode()
        _props_b64 = base64.b64encode(json.dumps({
            "retentionTimeInDays": 1, "eventThroughputLevel": "Low"
        }).encode()).decode()
        _platform_b64 = base64.b64encode(json.dumps({
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": "Eventstream", "displayName": _es_name},
            "config": {"version": "2.0", "logicalId": _es_id}
        }).encode()).decode()

        _update_body = {"definition": {"parts": [
            {"path": "eventstream.json", "payload": _es_json_b64, "payloadType": "InlineBase64"},
            {"path": "eventstreamProperties.json", "payload": _props_b64, "payloadType": "InlineBase64"},
            {"path": ".platform", "payload": _platform_b64, "payloadType": "InlineBase64"},
        ]}}

        r = requests.post(
            f"{api_base}/eventstreams/{_es_id}/updateDefinition?updateMetadata=true",
            headers=headers, json=_update_body
        )
        print(f"    updateDefinition: HTTP {r.status_code}")

        _wire_ok = False
        if r.status_code == 200:
            _wire_ok = True
            print(f"  [OK] Eventstream topology wired!")
        elif r.status_code == 202:
            _wire_ok = _wait_for_lro(r, "updateDefinition")
        else:
            print(f"    Error: {r.text[:500]}")

        if _wire_ok:
            # ── Verify topology status ──────────────────────────────
            time.sleep(5)
            _topo_r = requests.get(f"{api_base}/eventstreams/{_es_id}/topology", headers=headers)
            if _topo_r.status_code == 200:
                _topo = _topo_r.json()
                for _kind in ("sources", "destinations", "streams"):
                    _nodes = _topo.get(_kind, [])
                    for _n in _nodes:
                        print(f"    {_n['name']} ({_n['type']}) — {_n.get('status', '?')}")
            _topo_r = requests.get(f"{api_base}/eventstreams/{_es_id}/topology", headers=headers)
        # ── Print the ONE remaining manual step ─────────────────────
        _es_url = f"https://app.fabric.microsoft.com/groups/{workspace_id}/eventstreams/{_es_id}"
        print(f"\n  Eventstream URL: {_es_url}")
        print()
        print("  ┌──────────────────────────────────────────────────────────────┐")
        print("  │  EVENTSTREAM TOPOLOGY WIRED — ONE STEP REMAINING             │")
        print("  │                                                              │")
        print("  │  STEP A — Enable OneLake Availability (one-time, in portal)  │")
        print("  │    1. Open Healthcare_RTI_DB in the Fabric portal            │")
        print("  │    2. In the Database details pane → OneLake section         │")
        print("  │    3. Set Availability → Enabled                             │")
        print("  │    4. Check 'Apply to existing tables' → confirm             │")
        print("  │    This exposes KQL tables as Delta in OneLake so scoring    │")
        print("  │    notebooks can read them via Spark.                        │")
        print("  │                                                              │")
        print("  │  STEP B — Copy the Eventstream connection string             │")
        print("  │    1. Open the Eventstream URL above in your browser         │")
        print("  │    2. Click HealthcareCustomEndpoint → copy Conn String      │")
        print("  │    3. Paste into the NEXT CELL → run it                      │")
        print("  │                                                              │")
        print("  │  That cell creates OneLake shortcuts + triggers the          │")
        print("  │  PL_Healthcare_RTI pipeline (Simulator → Scoring).           │")
        print("  │                                                              │")
        print("  │  Two steps, then everything else is automatic.               │")
        print("  └──────────────────────────────────────────────────────────────┘")
    elif _es_id:
        print("  [WARN] KQL Database not found — cannot wire Eventstream topology")
        print("  Eventstream created but empty. Wire manually in the portal.")
    else:
        print("  [WARN] Eventstream not available — use Direct Kusto (zero-config)")


    # ── Deploy RTI Dashboard ───────────────────────────────────────
    # KQL Real-Time Dashboards don't sync via Git — deploy via REST API.
    print()
    print("=" * 60)
    print("  DEPLOYING RTI DASHBOARD")
    print("=" * 60)

    _dash_deployed = False
    try:
        import urllib.request, zipfile, io as _io

        # Load dashboard template from repo (downloaded in Cell 3)
        _dash_json_path = None
        for _candidate in [
            os.path.join(ws_dir, "..", "rti_dashboard", "healthcare_rti_dashboard.json") if ws_dir else "",
            os.path.join("/tmp/healthcare-demo", "rti_dashboard", "healthcare_rti_dashboard.json"),
        ]:
            if _candidate and os.path.exists(_candidate):
                _dash_json_path = _candidate
                break

        # Also try fetching from repo URL if not found locally
        if not _dash_json_path:
            _repo_url = "https://raw.githubusercontent.com/rasgiza/Fabric-Payer-Provider-HealthCare-Demo/main/rti_dashboard/healthcare_rti_dashboard.json"
            try:
                _dash_resp = requests.get(_repo_url, timeout=30)
                if _dash_resp.status_code == 200:
                    _dash_json_path = "/tmp/_rti_dashboard.json"
                    with open(_dash_json_path, "w", encoding="utf-8") as _f:
                        _f.write(_dash_resp.text)
                    print("  Downloaded dashboard template from GitHub")
            except Exception:
                pass

        if not _dash_json_path:
            print("  [SKIP] Dashboard template not found in extracted repo")
            print("         Create manually in the Fabric portal using RTI_DASHBOARD_GUIDE.md")
        else:
            with open(_dash_json_path, "r", encoding="utf-8") as _f:
                _dash_raw = _f.read()

            # Resolve placeholders using discovered values from this cell
            _kql_db_id_val = kql_db_id if kql_db_id else ""
            _kql_db_name_val = "Healthcare_RTI_DB"

            # Get Eventhouse query URI
            _query_uri_val = ""
            if _kql_db_id_val:
                _kql_detail = requests.get(
                    f"{api_base}/kqlDatabases/{_kql_db_id_val}",
                    headers=headers
                )
                if _kql_detail.status_code == 200:
                    _kql_props = _kql_detail.json().get("properties", {})
                    _query_uri_val = (_kql_props.get("queryUri")
                                      or _kql_props.get("parentEventhouseUri")
                                      or "")

            if not _query_uri_val:
                # Try from Eventhouse item
                _eh_resp = requests.get(f"{api_base}/items?type=Eventhouse", headers=headers)
                if _eh_resp.status_code == 200:
                    for _eh in _eh_resp.json().get("value", []):
                        if "Healthcare" in _eh["displayName"] or "RTI" in _eh["displayName"]:
                            _eh_detail = requests.get(
                                f"{api_base}/eventhouses/{_eh['id']}",
                                headers=headers
                            )
                            if _eh_detail.status_code == 200:
                                _query_uri_val = _eh_detail.json().get("properties", {}).get("queryServiceUri", "")
                            break

            print(f"  KQL DB ID:   {_kql_db_id_val[:8]}...")
            print(f"  KQL DB Name: {_kql_db_name_val}")
            print(f"  Query URI:   {_query_uri_val[:50]}..." if _query_uri_val else "  Query URI:   (not found)")

            # Patch placeholders
            _dash_raw = _dash_raw.replace("__KQL_DB_ID__", _kql_db_id_val)
            _dash_raw = _dash_raw.replace("__KQL_DB_NAME__", _kql_db_name_val)
            if _query_uri_val:
                _dash_raw = _dash_raw.replace("__EVENTHOUSE_QUERY_URI__", _query_uri_val)

            # Validate JSON
            _dash_def = json.loads(_dash_raw)
            _pages = _dash_def.get("pages", [])
            print(f"  Dashboard: {len(_pages)} pages, auto-refresh 30s")

            # Check if dashboard already exists
            _existing_dash_id = None
            for _dtype in ["RealTimeDashboard", "KQLDashboard"]:
                _dr = requests.get(f"{api_base}/items?type={_dtype}", headers=headers)
                if _dr.status_code == 200:
                    for _d in _dr.json().get("value", []):
                        if _d["displayName"] == "Healthcare RTI Dashboard":
                            _existing_dash_id = _d["id"]
                            break
                if _existing_dash_id:
                    break

            # Encode definition
            _dash_b64 = base64.b64encode(_dash_raw.encode("utf-8")).decode("utf-8")
            _def_parts = [{"path": "RealTimeDashboard.json", "payload": _dash_b64, "payloadType": "InlineBase64"}]

            if _existing_dash_id:
                # Update existing dashboard
                print(f"  Updating existing dashboard ({_existing_dash_id[:8]}...)...")
                _ur = requests.post(
                    f"{api_base}/items/{_existing_dash_id}/updateDefinition",
                    headers=headers,
                    json={"definition": {"parts": _def_parts}}
                )
                if _ur.status_code in (200, 202):
                    if _ur.status_code == 202:
                        _uloc = _ur.headers.get("Location", "")
                        _retry_after = int(_ur.headers.get("Retry-After", 5))
                        for _ in range(30):
                            time.sleep(_retry_after)
                            _pr = requests.get(_uloc, headers=headers)
                            if _pr.status_code == 200 and _pr.json().get("status") == "Succeeded":
                                break
                    print("  [OK] RTI Dashboard updated")
                    _dash_deployed = True
                else:
                    print(f"  [WARN] Update failed: HTTP {_ur.status_code} {_ur.text[:200]}")
            else:
                # Create new dashboard
                print("  Creating Healthcare RTI Dashboard...")
                _create_body = {
                    "displayName": "Healthcare RTI Dashboard",
                    "type": "KQLDashboard",
                    "definition": {"parts": _def_parts}
                }
                _cr = requests.post(f"{api_base}/items", headers=headers, json=_create_body)

                if _cr.status_code in (200, 201):
                    _new_id = _cr.json().get("id", "")
                    print(f"  [OK] Created: Healthcare RTI Dashboard ({_new_id[:8]}...)")
                    _dash_deployed = True
                elif _cr.status_code == 202:
                    _cloc = _cr.headers.get("Location", "")
                    _retry_after = int(_cr.headers.get("Retry-After", 5))
                    for _ in range(30):
                        time.sleep(_retry_after)
                        _pr = requests.get(_cloc, headers=headers)
                        if _pr.status_code == 200:
                            _pstatus = _pr.json().get("status", "")
                            if _pstatus == "Succeeded":
                                print("  [OK] Created: Healthcare RTI Dashboard (LRO)")
                                _dash_deployed = True
                                break
                            elif _pstatus in ("Failed", "Cancelled"):
                                _perr = _pr.json().get("error", {}).get("message", "")
                                print(f"  [FAIL] {_pstatus}: {_perr[:200]}")
                                break
                elif _cr.status_code == 409:
                    print("  [OK] Dashboard already exists (409 conflict)")
                    _dash_deployed = True
                else:
                    # Try alternate type name
                    _create_body["type"] = "RealTimeDashboard"
                    _cr2 = requests.post(f"{api_base}/items", headers=headers, json=_create_body)
                    if _cr2.status_code in (200, 201, 202):
                        print("  [OK] Created with type RealTimeDashboard")
                        _dash_deployed = True
                    else:
                        print(f"  [FAIL] Create failed: HTTP {_cr.status_code} {_cr.text[:200]}")

    except Exception as _dash_err:
        print(f"  [WARN] Dashboard deploy failed: {_dash_err}")
        print("  You can create it manually — see RTI_DASHBOARD_GUIDE.md")

    if not _dash_deployed:
        print("  Dashboard not deployed. Create manually via Fabric portal.")
        print("  Reference: RTI_DASHBOARD_GUIDE.md in the repo")

    print()
    print("RTI deployment complete.")
    print("  Eventstream topology wired — copy connection string to start streaming")
    print()
    print("  NEXT: Paste the connection string into the next cell and run it.")
    print("  PL_Healthcare_RTI orchestrates: Simulator → Scoring (parallel)")

else:
    print("Skipping RTI deployment (DEPLOY_STREAMING=False)")
    print("Set DEPLOY_STREAMING = True in the CONFIG cell to enable Eventhouse + scoring.")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# CELL 8 — Run RTI Streaming Pipeline (Eventstream → KQL → Scoring)
# ============================================================================
# Orchestrates the full RTI pipeline:
#   1. Run NB_RTI_Event_Simulator (streams events → Eventstream → KQL)
#   2. Verify data landed in KQL tables (poll until non-empty)
#   3. Run scoring notebooks (Fraud, CareGap, HighCost)
#
# Architecture note:
#   KQL Eventhouse = real-time hot path (KQL Dashboard + scoring notebooks)
#   Lakehouse gold = batch archive (historical analytics, star schema)
#   The two stores are queried independently — KQL via native Kusto, Lakehouse
#   via Direct Lake. OneLake availability on the KQL DB is intentionally NOT
#   enabled because it negates the latency advantage that makes RTI valuable.
# ============================================================================


# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                                   ║
# ║   ⚠️  ACTION REQUIRED — PASTE EVENTSTREAM CONNECTION STRING BELOW              ║
# ║                                                                                   ║
# ║   This is the ONLY manual step in the entire demo. Fabric does not expose         ║
# ║   the Eventstream Custom Endpoint connection string via REST API, so it must     ║
# ║   be copied from the portal.                                                      ║
# ║                                                                                   ║
# ║   1. Cell 7 already created the Eventstream + KQL Dashboard.                      ║
# ║   2. Open the workspace in the Fabric portal.                                     ║
# ║   3. Click into 'Healthcare_RTI_Eventstream'.                                     ║
# ║   4. Click the 'HealthcareCustomEndpoint' source node → Details panel opens.      ║
# ║   5. Copy the 'Connection string-primary key' value.                              ║
# ║   6. Paste it between the quotes in ES_CONNECTION_STRING below.                   ║
# ║   7. Re-run this cell.                                                            ║
# ║                                                                                   ║
# ╚══════════════════════════════════════════════════════════════════╝

ES_CONNECTION_STRING = ""   # ◀── PASTE EVENTSTREAM CONNECTION STRING HERE

if not DEPLOY_STREAMING:
    print("Skipping RTI streaming (DEPLOY_STREAMING=False)")
    print("Set DEPLOY_STREAMING = True in the CONFIG cell to enable.")

elif not ES_CONNECTION_STRING:
    print("=" * 60)
    print("  ES_CONNECTION_STRING is empty.")
    print()
    print("  To get the connection string:")
    print("  1. Open Healthcare_RTI_Eventstream in the Fabric portal")
    print("  2. Click the HealthcareCustomEndpoint source node")
    print("  3. Copy the Connection String")
    print("  4. Paste it into ES_CONNECTION_STRING above")
    print("  5. Re-run this cell")
    print("=" * 60)

else:
    import requests, time, json

    _token = notebookutils.credentials.getToken("pbi")
    _hdrs = {"Authorization": f"Bearer {_token}", "Content-Type": "application/json"}
    _api = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}"

    # ── Resolve KQL DB for verification ────────────────────────────
    _kql_db = None
    _r = requests.get(f"{_api}/items?type=KQLDatabase", headers=_hdrs)
    if _r.status_code == 200:
        _kql_db = next((i for i in _r.json().get("value", [])
                        if i["displayName"] == "Healthcare_RTI_DB"), None)
        if not _kql_db:
            _kql_db = next((i for i in _r.json().get("value", [])
                            if i["displayName"] == "Healthcare_RTI_Eventhouse"), None)

    _query_url = f"{_api}/kqlDatabases/{_kql_db['id']}/queryRun" if _kql_db else None

    # ── Step 0: Run Setup Eventhouse (create KQL tables + update policies) ──
    print("=" * 60)
    print("  STEP 0: RUNNING NB_RTI_Setup_Eventhouse")
    print("=" * 60)
    print("  Creates rti_all_events, typed tables, update policies, and JSON mappings")
    print()

    _setup_ok = False
    try:
        notebookutils.notebook.run("NB_RTI_Setup_Eventhouse", 600, {"useRootDefaultLakehouse": True})
        _setup_ok = True
        print("  [OK] Setup Eventhouse completed — KQL schema ready")
    except Exception as _setup_err:
        if "mssparkutilsrun-result+json" in str(_setup_err) or "NoSuchElementException" in str(_setup_err):
            _setup_ok = True
            print("  [OK] Setup Eventhouse completed (ignoring Fabric result-parse bug)")
        else:
            print(f"  [WARN] Setup Eventhouse: {_setup_err}")
            print("         Tables may already exist. Continuing...")
            _setup_ok = True  # non-fatal — tables might already exist

    print()

    # ── Step 1: Run Event Simulator ────────────────────────────────
    print("=" * 60)
    print("  STEP 1: RUNNING EVENT SIMULATOR")
    print("=" * 60)
    print("  Events → Eventstream → Eventhouse (KQL update policies route to typed tables)")
    print()

    _sim_ok = False
    try:
        notebookutils.notebook.run("NB_RTI_Event_Simulator", 1200, {
            "ES_CONNECTION_STRING": ES_CONNECTION_STRING,
            "STREAM_BATCHES": 10,
            "useRootDefaultLakehouse": True,
        })
        _sim_ok = True
        print("  [OK] Event Simulator completed")
    except Exception as _sim_err:
        if "mssparkutilsrun-result+json" in str(_sim_err) or "NoSuchElementException" in str(_sim_err):
            _sim_ok = True
            print("  [OK] Event Simulator completed (ignoring Fabric result-parse bug)")
        else:
            print(f"  [FAIL] Event Simulator: {_sim_err}")
            print("  Check the notebook run history for details.")

    if _sim_ok and _kql_db:
        # ── Step 2: Verify data landed in KQL ──────────────────────
        print()
        print("=" * 60)
        print("  STEP 2: VERIFYING DATA IN KQL TABLES")
        print("=" * 60)

        _tables_to_check = ["claims_events", "adt_events", "rx_events"]
        _tables_with_data = set()
        _max_retries = 12  # 12 * 10s = 2 min max wait
        for _retry in range(_max_retries):
            _token = notebookutils.credentials.getToken("pbi")
            _hdrs = {"Authorization": f"Bearer {_token}", "Content-Type": "application/json"}
            for _tbl in _tables_to_check:
                if _tbl in _tables_with_data:
                    continue
                _count_cmd = f"{_tbl} | count"
                _cr = requests.post(_query_url, headers=_hdrs, json={"query": _count_cmd, "queryKind": "mgmt"})
                if _cr.status_code == 200:
                    try:
                        _frames = _cr.json().get("results", [{}])
                        _rows = _frames[0].get("rows", []) if _frames else []
                        _cnt = int(_rows[0][0]) if _rows and _rows[0] else 0
                        if _cnt > 0:
                            _tables_with_data.add(_tbl)
                            print(f"  [OK] {_tbl}: {_cnt} rows")
                    except Exception:
                        pass
            if len(_tables_with_data) == len(_tables_to_check):
                break
            if _retry < _max_retries - 1:
                _remaining = [t for t in _tables_to_check if t not in _tables_with_data]
                print(f"  Waiting for data in: {', '.join(_remaining)} ({(_retry+1)*10}s)")
                time.sleep(10)

        if len(_tables_with_data) < len(_tables_to_check):
            _missing = [t for t in _tables_to_check if t not in _tables_with_data]
            print(f"  [WARN] No data in: {', '.join(_missing)} after {_max_retries*10}s")
            print(f"         Check Eventstream topology and KQL update policies.")

        # ── Step 3: Run Scoring Notebooks ──────────────────────────
        print()
        print("=" * 60)
        print("  STEP 3: RUNNING SCORING NOTEBOOKS")
        print("=" * 60)
        print("  Fraud Detection + Care Gap Alerts + HighCost Trajectory")
        print()

        _scoring_nbs = [
            "NB_RTI_Fraud_Detection",
            "NB_RTI_Care_Gap_Alerts",
            "NB_RTI_HighCost_Trajectory",
        ]
        _scoring_ok = 0
        for _nb in _scoring_nbs:
            print(f"  Running {_nb}...")
            try:
                notebookutils.notebook.run(_nb, 1200, {"useRootDefaultLakehouse": True})
                print(f"  [OK] {_nb}")
                _scoring_ok += 1
            except Exception as _sc_err:
                if "mssparkutilsrun-result+json" in str(_sc_err) or "NoSuchElementException" in str(_sc_err):
                    print(f"  [OK] {_nb} (ignoring Fabric result-parse bug)")
                    _scoring_ok += 1
                else:
                    print(f"  [WARN] {_nb}: {_sc_err}")
                    print(f"         Run manually from the workspace if needed.")

        # ── Summary ────────────────────────────────────────────────
        print()
        print("=" * 60)
        print("  RTI STREAMING PIPELINE COMPLETE")
        print("=" * 60)
        print(f"  Simulator:  {'OK' if _sim_ok else 'FAILED'}")
        print(f"  KQL Data:   {len(_tables_with_data)}/{len(_tables_to_check)} tables populated")
        print(f"  Scoring:    {_scoring_ok}/{len(_scoring_nbs)}")
        print()
        print("  Data flow:")
        print("    Simulator → Eventstream → rti_all_events (KQL)")
        print("    KQL update policies → claims_events, adt_events, rx_events")
        print("    Scoring notebooks → fraud_scores, care_gap_alerts, highcost_alerts")
        print()
        print("  NOTE: KQL Eventhouse is the real-time query surface.")
        print("  For unified lakehouse access, enable OneLake Availability")
        print("  on the KQL DB and create shortcuts manually in the portal.")
        print("=" * 60)

    elif not _sim_ok:
        print("\n  Simulator failed — skipping verification and scoring.")
        print("  Fix the issue and re-run this cell.")
    else:
        print("\n  KQL Database not found — cannot verify data or run scoring.")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# CELL 9 — Organize Workspace Items into Folders
# ============================================================================
# Moves deployed items into folders matching logical categories.
# Safe to re-run — items already in correct folders are skipped.
#
# Folder structure:
#   Lakehouses/              — lh_bronze_raw, lh_silver_stage, lh_silver_ods,
#                              lh_gold_curated
#   Semantic Models/         — HealthcareDemoHLS
#   Notebooks/               — ETL notebooks, data gen, graph deploy
#   Pipelines/               — PL_Healthcare_Full_Load, PL_Healthcare_Master
#   Agents/                  — HealthcareHLSAgent
#   Reports/                 — Healthcare Analytics Dashboard
#   Ontology/                — Healthcare_Demo_Ontology_HLS, Healthcare_Demo_Graph
#   Real-Time Intelligence/  — Eventhouse, KQL DB, RTI notebooks, RTI pipeline
#                              (DEPLOY_STREAMING only)
#
# Items not in any folder stay at workspace root (e.g. this launcher notebook).
# ============================================================================

import requests, time, re as _re
from datetime import datetime, timezone

token = notebookutils.credentials.getToken("pbi")
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}
api_base = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}"

# ── Helper functions ──────────────────────────────────────────

def get_or_create_folder(name):
    """Get existing folder by name or create it. Returns folder ID."""
    r = requests.get(f"{api_base}/folders", headers=headers)
    if r.status_code == 200:
        for f in r.json().get("value", []):
            if f["displayName"] == name:
                return f["id"]
    r = requests.post(f"{api_base}/folders", headers=headers,
                      json={"displayName": name})
    if r.status_code in (200, 201):
        return r.json()["id"]
    elif r.status_code == 409 or "AlreadyInUse" in r.text:
        r2 = requests.get(f"{api_base}/folders", headers=headers)
        for f in r2.json().get("value", []):
            if f["displayName"] == name:
                return f["id"]
    elif r.status_code == 429:
        retry_after = int(r.headers.get("Retry-After", 10))
        print(f"  [WAIT] Rate limited creating '{name}', retrying in {retry_after}s...")
        time.sleep(retry_after)
        token_r = notebookutils.credentials.getToken("pbi")
        headers["Authorization"] = f"Bearer {token_r}"
        r2 = requests.post(f"{api_base}/folders", headers=headers,
                           json={"displayName": name})
        if r2.status_code in (200, 201):
            return r2.json()["id"]
    print(f"  [WARN] Could not create folder '{name}': {r.status_code}")
    return None


def move_item(item_id, item_name, folder_id, max_retries=3):
    """Move an item into a folder with retry on 429 rate limiting."""
    for attempt in range(max_retries + 1):
        r = requests.post(f"{api_base}/items/{item_id}/move",
                          headers=headers,
                          json={"targetFolderId": folder_id})
        if r.status_code == 200:
            return "moved"
        elif r.status_code == 400 and "already" in r.text.lower():
            return "moved"  # already in folder
        elif r.status_code == 429:
            retry_after = int(r.headers.get("Retry-After", 5)) * (2 ** attempt)
            try:
                match = _re.search(r'until:\s*([\d/]+\s+[\d:]+\s+\w+)', r.text)
                if match:
                    blocked_until = datetime.strptime(match.group(1), "%m/%d/%Y %I:%M:%S %p")
                    blocked_until = blocked_until.replace(tzinfo=timezone.utc)
                    wait_secs = max(1, (blocked_until - datetime.now(timezone.utc)).total_seconds() + 2)
                    retry_after = min(wait_secs, 120)
            except Exception:
                pass
            if attempt < max_retries:
                print(f"    [WAIT] {item_name} — rate limited, retrying in {int(retry_after)}s "
                      f"(attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_after)
                _tok = notebookutils.credentials.getToken("pbi")
                headers["Authorization"] = f"Bearer {_tok}"
            else:
                print(f"    [FAIL] {item_name} — rate limited after {max_retries} retries")
                return "failed"
        elif r.status_code == 400 and "CannotMoveChildOnly" in r.text:
            return "child"  # KQLDatabase moves with Eventhouse parent
        else:
            print(f"    [FAIL] {item_name}: {r.status_code} {r.text[:150]}")
            return "failed"
    return "failed"


# ── Folder → item mapping ────────────────────────────────────
# Each folder explicitly lists items by displayName.
# For type disambiguation, use (name, type) tuples.

FOLDER_MAP = {
    "Lakehouses": [
        "lh_bronze_raw",
        "lh_silver_stage",
        "lh_silver_ods",
        "lh_gold_curated",
    ],
    "Semantic Models": [
        ("HealthcareDemoHLS", "SemanticModel"),
    ],
    "Notebooks": [
        "01_Bronze_Ingest_CSV",
        "02_Silver_Stage_Clean",
        "03_Silver_ODS_Enrich",
        "06a_Create_Gold_Lakehouse_Tables",
        "06b_Gold_Transform_Load_v2",
        "NB_Generate_Sample_Data",
        "NB_Generate_Incremental_Data",
        "NB_Deploy_Graph_Model",
        "NB_Refresh_Graph_Model",
    ],
    "Pipelines": [
        "PL_Healthcare_Full_Load",
        "PL_Healthcare_Master",
    ],
    "Agents": [
        "HealthcareHLSAgent",
    ],
    "Reports": [
        ("HealthcareAnalyticsDashboard", "Report"),
    ],
    "Ontology": [
        "Healthcare_Demo_Ontology_HLS",
        "Healthcare_Demo_Graph",
    ],
}

# Streaming-only items — added when DEPLOY_STREAMING is enabled
if DEPLOY_STREAMING:
    FOLDER_MAP["Real-Time Intelligence"] = [
        ("Healthcare_RTI_Eventhouse", "Eventhouse"),
        ("Healthcare_RTI_Eventstream", "Eventstream"),
        "NB_RTI_Setup_Eventhouse",
        "NB_RTI_Event_Simulator",
        "NB_RTI_Fraud_Detection",
        "NB_RTI_Care_Gap_Alerts",
        "NB_RTI_HighCost_Trajectory",
        "PL_Healthcare_RTI",
    ]

# ── Build item lookup ─────────────────────────────────────────
print("=" * 60)
print("  ORGANIZE WORKSPACE FOLDERS")
print("=" * 60)

print("\nRefreshing workspace items list...")
all_items_resp = requests.get(f"{api_base}/items?maxResults=500", headers=headers)
all_items = all_items_resp.json().get("value", []) if all_items_resp.status_code == 200 else []
print(f"  Found {len(all_items)} items in workspace\n")

# Primary lookup: name → id
item_lookup = {}
# Type-aware lookup: (name, type) → id
item_type_lookup = {}
for i in all_items:
    item_lookup[i["displayName"]] = i["id"]
    item_type_lookup[(i["displayName"], i["type"])] = i["id"]

# ── Execute moves ─────────────────────────────────────────────
moved = 0
skipped = 0
not_found = 0

for folder_name, item_entries in FOLDER_MAP.items():
    folder_id = get_or_create_folder(folder_name)
    if not folder_id:
        continue
    print(f"  [{folder_name}]")

    for entry in item_entries:
        # Support both "name" and ("name", "Type") formats
        if isinstance(entry, tuple):
            name, item_type = entry
            item_id = item_type_lookup.get((name, item_type))
        else:
            name = entry
            item_id = item_lookup.get(name)

        if not item_id:
            print(f"    - {name} — not found (may not be deployed yet)")
            not_found += 1
            continue

        result = move_item(item_id, name, folder_id)
        if result == "moved":
            print(f"    + {name}")
            moved += 1
        elif result == "child":
            print(f"    ~ {name} — child item, moves with parent")
            moved += 1
        else:
            skipped += 1

        # Small delay between moves to avoid rate limiting
        time.sleep(1.5)

print(f"\n  Done: {moved} moved, {skipped} failed, {not_found} not found")

# ── Deployment Summary ────────────────────────────────────────
print()

# Re-fetch items to get updated folder assignments
token = notebookutils.credentials.getToken("pbi")
headers["Authorization"] = f"Bearer {token}"
resp = requests.get(f"{api_base}/items", headers=headers)
items = resp.json().get("value", []) if resp.status_code == 200 else []

# Build folder_id → folder_name from created folders
fr = requests.get(f"{api_base}/folders", headers=headers)
fid_to_name = {}
if fr.status_code == 200:
    for f in fr.json().get("value", []):
        fid_to_name[f["id"]] = f["displayName"]

# Group by folder, then by type
by_folder = {}
for it in items:
    fid = it.get("folderId")
    folder = fid_to_name.get(fid, "(root)")
    by_folder.setdefault(folder, {})
    t = it.get("type", "Unknown")
    by_folder[folder].setdefault(t, []).append(it["displayName"])

print("=" * 60)
print("  DEPLOYMENT COMPLETE")
print("=" * 60)
print(f"  Workspace: {workspace_id}")
print(f"  Total items: {len(items)}")
print()

# Print organized by folder
for folder_name in list(FOLDER_MAP.keys()) + ["(root)"]:
    types = by_folder.get(folder_name, {})
    if not types:
        continue
    total = sum(len(v) for v in types.values())
    print(f"  [{folder_name}] ({total} items)")
    for item_type in sorted(types.keys()):
        names = types[item_type]
        print(f"    {item_type} ({len(names)}):")
        for n in sorted(names):
            print(f"      - {n}")
    print()

# RTI table counts (only when streaming is enabled)
if DEPLOY_STREAMING:
    print("  RTI Delta Tables (lh_gold_curated):")
    try:
        for tbl in ["rti_claims_events", "rti_adt_events", "rti_rx_events",
                    "rti_fraud_scores", "rti_care_gap_alerts",
                    "rti_highcost_alerts"]:
            try:
                cnt = spark.table(tbl).count()
                print(f"    - {tbl}: {cnt:,} rows")
            except Exception:
                print(f"    - {tbl}: (not created yet)")
    except Exception:
        print("    (could not query RTI tables)")
    print()

print("=" * 60)
print("  NEXT STEPS")
print("=" * 60)
print("  1. Open the HealthcareDemoHLS semantic model -> verify tables loaded")
print("  2. Open the HealthcareHLSAgent -> ask: 'What are the top denial reasons?'")
print("  3. Create the Healthcare Ontology Agent via UI (see Cell 11 for instructions)")
print("  3b. Open Healthcare Analytics Dashboard (Power BI) -> 6 pages, 60+ visuals")
print("  4. Verify the Ontology + Graph Model (auto-provisioned, or run NB_Deploy_Graph_Model)")
print("     -> Open Healthcare_Demo_Ontology_HLS in workspace to explore")
print("  5. For incremental loads: run PL_Healthcare_Master with load_mode=incremental")
print("     (auto-generates incremental data + runs full ETL in one shot)")
if DEPLOY_STREAMING:
    print("  6. RTI Dashboard: Open Healthcare_RTI_Dashboard for live KQL visuals")
    print("     - NB_RTI_Fraud_Detection: View rti_fraud_scores for flagged claims")
    print("     - NB_RTI_Care_Gap_Alerts: View rti_care_gap_alerts for HEDIS gap closures")
    print("     - NB_RTI_HighCost_Trajectory: View rti_highcost_alerts for cost trends")
    print("  7. For live streaming: set MODE='stream' in NB_RTI_Event_Simulator")
    print("     and configure the Eventstream Custom App connection string")
print("=" * 60)

