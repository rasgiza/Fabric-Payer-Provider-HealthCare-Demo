# ============================================================================
# CELL 13 — Run RTI Streaming Pipeline (Eventstream → KQL → Scoring)
# ============================================================================
# Orchestrates the full RTI pipeline:
#   1. Enable OneLake Availability on KQL DB (programmatic — no portal toggle)
#   2. Run NB_RTI_Event_Simulator (streams events → Eventstream → KQL)
#   3. Verify data landed in KQL tables (poll until non-empty)
#   4. Create OneLake shortcuts (KQL → lh_gold_curated) with retry
#   5. Run scoring notebooks (Fraud, CareGap, HighCost) in parallel
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
    print("  4. Paste it into ES_CONNECTION_STRING below")
    print("  5. Re-run from Cell 1 or re-run this cell")
    print("=" * 60)

else:
    import requests, time, json

    _token = notebookutils.credentials.getToken("pbi")
    _hdrs = {"Authorization": f"Bearer {_token}", "Content-Type": "application/json"}
    _api = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}"

    # ── Resolve lh_gold_id if not already set ───────────────────────
    if "lh_gold_id" not in dir() or not lh_gold_id:
        _lh_r = requests.get(f"{_api}/lakehouses", headers=_hdrs)
        if _lh_r.status_code == 200:
            _lh_match = next((lh for lh in _lh_r.json().get("value", [])
                              if lh["displayName"] == "lh_gold_curated"), None)
            if _lh_match:
                lh_gold_id = _lh_match["id"]
                print(f"  Resolved lh_gold_curated: {lh_gold_id}")
            else:
                print("  [WARN] lh_gold_curated not found — shortcuts will fail")
                lh_gold_id = None

    # ── Step 1: Enable OneLake Availability on KQL DB ───────────────
    print("=" * 60)
    print("  STEP 1: ENABLING ONELAKE AVAILABILITY ON KQL DATABASE")
    print("=" * 60)

    _kql_db_for_onelake = None
    _r = requests.get(f"{_api}/items?type=KQLDatabase", headers=_hdrs)
    if _r.status_code == 200:
        _kql_db_for_onelake = next((i for i in _r.json().get("value", [])
                                    if i["displayName"] == "Healthcare_RTI_DB"), None)
        if not _kql_db_for_onelake:
            _kql_db_for_onelake = next((i for i in _r.json().get("value", [])
                                        if i["displayName"] == "Healthcare_RTI_Eventhouse"), None)

    if _kql_db_for_onelake:
        _db_id = _kql_db_for_onelake["id"]
        _db_name = _kql_db_for_onelake["displayName"]
        _query_url = f"{_api}/kqlDatabases/{_db_id}/queryRun"

        # Enable database-level OneLake availability via PATCH
        _onelake_patch_url = f"{_api}/kqlDatabases/{_db_id}"
        _olr = requests.patch(_onelake_patch_url, headers=_hdrs, json={
            "properties": {"oneLakeStandardAvailability": "Enabled"}
        })
        if _olr.status_code in (200, 201, 204):
            print(f"  [OK] OneLake Availability enabled on {_db_name}")
        else:
            # Fallback: try management command via queryRun
            _onelake_cmd = f".alter-merge database {_db_name} policy mirroring dataformat=parquet with (IsEnabled=true)"
            _olr2 = requests.post(_query_url, headers=_hdrs, json={"query": _onelake_cmd, "queryKind": "mgmt"})
            if _olr2.status_code in (200, 201):
                print(f"  [OK] OneLake Availability enabled on {_db_name}")
            else:
                print(f"  [WARN] OneLake enable: HTTP {_olr.status_code} / {_olr2.status_code}")
                print(f"         Enable OneLake Availability manually in portal if shortcuts fail.")

        # Set 5-minute flush on all tables for fast demo experience
        for _tbl in ["claims_events", "adt_events", "rx_events",
                      "fraud_scores", "care_gap_alerts", "highcost_alerts"]:
            _mir_cmd = f".alter-merge table {_tbl} policy mirroring dataformat=parquet with (IsEnabled=true, TargetLatencyInMinutes=5)"
            _mir_r = requests.post(_query_url, headers=_hdrs, json={"query": _mir_cmd, "queryKind": "mgmt"})
            if _mir_r.status_code in (200, 201):
                print(f"  [OK] Mirroring (5-min flush): {_tbl}")
            else:
                print(f"  [WARN] Mirroring {_tbl}: HTTP {_mir_r.status_code}")
        print()
    else:
        print("  [WARN] Healthcare_RTI_DB not found — skipping OneLake enable")
        print()

    # ── Step 2: Run Event Simulator (stream events → Eventstream → KQL) ──
    print("=" * 60)
    print("  STEP 2: RUNNING EVENT SIMULATOR")
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

    if _sim_ok and _kql_db_for_onelake:
        # ── Step 3: Verify data landed in KQL ───────────────────────
        print()
        print("=" * 60)
        print("  STEP 3: VERIFYING DATA IN KQL TABLES")
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
            print(f"         Shortcuts may fail for these tables.")

        # ── Step 4: Create OneLake Shortcuts (KQL → lh_gold_curated) ──
        print()
        print("=" * 60)
        print("  STEP 4: CREATING ONELAKE SHORTCUTS (KQL → lh_gold_curated)")
        print("=" * 60)

        _kql_db_id = _kql_db_for_onelake["id"]
        _shortcut_map = {
            "rti_claims_events": "claims_events",
            "rti_adt_events":    "adt_events",
            "rti_rx_events":     "rx_events",
        }
        _sc_ok = 0

        # Retry loop — OneLake paths may take a moment to appear after mirroring
        for _sc_attempt in range(3):
            if _sc_ok == len(_shortcut_map):
                break
            if _sc_attempt > 0:
                print(f"  Retry {_sc_attempt}/2 after 30s (waiting for OneLake propagation)...")
                time.sleep(30)
                _token = notebookutils.credentials.getToken("pbi")
                _hdrs = {"Authorization": f"Bearer {_token}", "Content-Type": "application/json"}

            for _sc_name, _kql_table in _shortcut_map.items():
                if _sc_attempt > 0:
                    # Check if already created in a previous attempt
                    _chk = requests.get(
                        f"{_api}/items/{lh_gold_id}/shortcuts/Tables/{_sc_name}",
                        headers=_hdrs
                    )
                    if _chk.status_code == 200:
                        continue

                _sc_body = {
                    "name": _sc_name,
                    "path": "Tables",
                    "target": {
                        "oneLake": {
                            "workspaceId": workspace_id,
                            "itemId": _kql_db_id,
                            "path": f"Tables/{_kql_table}"
                        }
                    }
                }
                _sc_r = requests.post(
                    f"{_api}/items/{lh_gold_id}/shortcuts",
                    headers=_hdrs,
                    json=_sc_body
                )
                if _sc_r.status_code in (200, 201):
                    print(f"  [OK] Shortcut: lh_gold_curated.{_sc_name} → KQL {_kql_table}")
                    _sc_ok += 1
                elif _sc_r.status_code == 409:
                    print(f"  [OK] Shortcut already exists: {_sc_name}")
                    _sc_ok += 1
                else:
                    _msg = _sc_r.json().get("message", _sc_r.text[:200]) if _sc_r.text else ""
                    print(f"  [WARN] Shortcut {_sc_name}: HTTP {_sc_r.status_code} {_msg[:150]}")

        if _sc_ok >= len(_shortcut_map):
            print(f"\n  All {_sc_ok} shortcuts ready")
        else:
            print(f"\n  {_sc_ok}/{len(_shortcut_map)} shortcuts created")
            print(f"  Re-run this cell if shortcuts failed due to OneLake propagation delay.")

        # ── Step 5: Run Scoring Notebooks ───────────────────────────
        print()
        print("=" * 60)
        print("  STEP 5: RUNNING SCORING NOTEBOOKS")
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

        # ── Summary ─────────────────────────────────────────────────
        print()
        print("=" * 60)
        print("  RTI STREAMING PIPELINE COMPLETE")
        print("=" * 60)
        print(f"  Simulator:  {'OK' if _sim_ok else 'FAILED'}")
        print(f"  Shortcuts:  {_sc_ok}/{len(_shortcut_map)}")
        print(f"  Scoring:    {_scoring_ok}/{len(_scoring_nbs)}")
        print()
        print("  Data flow:")
        print("    Simulator → Eventstream → rti_all_events (KQL)")
        print("    KQL update policies → claims_events, adt_events, rx_events")
        print("    OneLake shortcuts → lh_gold_curated.rti_*")
        print("    Scoring notebooks → fraud_scores, care_gap_alerts, highcost_alerts")
        print("=" * 60)

    elif not _sim_ok:
        print("\n  Simulator failed — skipping shortcuts and scoring.")
        print("  Fix the issue and re-run this cell.")
    else:
        print("\n  KQL Database not found — cannot create shortcuts or run scoring.")
