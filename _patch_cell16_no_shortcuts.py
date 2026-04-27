"""Patch Cell 16 (CELL 13 — RTI Pipeline) to remove OneLake shortcuts.
New flow: Simulator → Verify KQL → Scoring (no shortcut, no OneLake enable)
"""
import json

NB_PATH = "Healthcare_Launcher.ipynb"

NEW_CELL_SOURCE = '''# ============================================================================
# CELL 13 — Run RTI Streaming Pipeline (Eventstream → KQL → Scoring)
# ============================================================================
# Orchestrates the full RTI pipeline:
#   1. Run NB_RTI_Event_Simulator (streams events → Eventstream → KQL)
#   2. Verify data landed in KQL tables (poll until non-empty)
#   3. Run scoring notebooks (Fraud, CareGap, HighCost)
#
# Architecture note:
#   KQL Eventhouse = real-time hot path (live dashboards, scoring, OpsAgent)
#   Lakehouse gold = batch archive (historical analytics, star schema)
#   In production, you would enable OneLake Availability on the KQL DB and
#   create OneLake shortcuts to unify both stores in a single Lakehouse view.
#   For this demo, we skip shortcuts to avoid manual portal steps and
#   propagation delays that break one-click automation.
#
# The ES_CONNECTION_STRING must be set below before running.
# This is the only manual step — Fabric does not expose the Custom
# Endpoint connection string via REST API.
# ============================================================================


ES_CONNECTION_STRING = ""   # <── PASTE connection string here

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
        print("\\n  Simulator failed — skipping verification and scoring.")
        print("  Fix the issue and re-run this cell.")
    else:
        print("\\n  KQL Database not found — cannot verify data or run scoring.")
'''

# Load notebook
with open(NB_PATH, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Find cell 16 (index 15) and replace its source
cell = nb['cells'][15]
assert 'CELL 13' in ''.join(cell['source']), f"Cell 16 is not CELL 13! Got: {''.join(cell['source'])[:60]}"

# Convert to list of lines (ipynb format: each element is a line with \n)
lines = NEW_CELL_SOURCE.split('\n')
cell['source'] = [line + '\n' for line in lines[:-1]] + [lines[-1]]  # Last line has no trailing \n

# Write back
with open(NB_PATH, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("OK — Cell 16 rewritten (removed OneLake enable + shortcuts, simplified to 3 steps)")
