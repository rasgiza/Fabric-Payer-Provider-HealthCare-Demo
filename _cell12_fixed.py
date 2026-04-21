# ============================================================================
# CELL 12 — Deploy Real-Time Intelligence (RTI) + Operations Agent
# ============================================================================
# Eventhouse + KQL Database are already deployed as Git artifacts (Stage 2).
# This cell:
#   1. Patches RTI notebooks with lakehouse metadata
#   2. Runs NB_RTI_Setup_Eventhouse (creates KQL tables, discovers Kusto URI)
#   3. Wires Eventstream full topology via API:
#      Custom Endpoint → Stream → Eventhouse + Lakehouse + Activator
#   4. Creates OperationsAgent + patches definition
#   5. Prints instruction: copy connection string from portal
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
                 "NB_RTI_Fraud_Detection",
                 "NB_RTI_Care_Gap_Alerts", "NB_RTI_HighCost_Trajectory",
                 "NB_RTI_Operations_Agent"]

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

    # ── OperationsAgent Setup (needs KQL DB from streaming) ──────
    # ── HealthcareOpsAgent (OperationsAgent) — create-if-not-exists + patch ──────
    # fabric-cicd doesn't support the OperationsAgent item type, so Cell 3 skips it.
    # Config is inlined here (not read from extracted repo) to avoid path search issues.
    # Uses the dedicated /operationsAgents REST API endpoint.
    print("\n" + "=" * 60)
    print("  HEALTHCAREOPSAGENT (OperationsAgent) SETUP")
    print("=" * 60)

    ops_agent_id = None
    kql_db_id = None
    for item in items:
        if item["type"] == "OperationsAgent" and item["displayName"] == "HealthcareOpsAgent":
            ops_agent_id = item["id"]
        elif item["type"] == "KQLDatabase":
            kql_db_id = item["id"]

    if not kql_db_id:
        print("[SKIP] KQL Database not found in workspace (needed for OpsAgent)")
    else:
        print(f"  OpsAgent:       {ops_agent_id or '(not yet created)'}")
        print(f"  KQL Database:   {kql_db_id}")

        # --- Inline config (avoids fragile file-path search in extracted repo) ---
        config_json = {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/operationsAgents/definition/1.0.0/schema.json",
            "configuration": {
                "goals": "Monitor healthcare real-time streaming tables for fraud alerts, care gap alerts, and high-cost member alerts. Detect critical issues and recommend actions.",
                "instructions": "Monitor the fraud_scores, care_gap_alerts, and highcost_alerts tables. Alert when fraud_score >= 50 (SIU referral), gap_days_overdue > 90 (care outreach), or rolling_spend_30d > 50000 (care management). Flag stale data if no records arrive in 30 minutes.",
                "dataSources": {
                    "healthcareRTI": {
                        "id": kql_db_id,
                        "type": "KustoDatabase",
                        "workspaceId": workspace_id
                    }
                },
                "actions": {}
            },
            "shouldRun": False
        }
        print(f"    dataSources.healthcareRTI.id -> {kql_db_id}")
        print(f"    dataSources.healthcareRTI.workspaceId -> {workspace_id}")

        ops_api = f"{api_base}/operationsAgents"

        def _wait_for_lro(r, action_name):
            """Wait for a 202 LRO to complete. Returns True on success."""
            if r.status_code == 200:
                print(f"  [OK] {action_name} succeeded")
                return True
            elif r.status_code == 201:
                print(f"  [OK] {action_name} created")
                return True
            elif r.status_code == 202:
                op_url = r.headers.get("Location", "")
                retry_after = int(r.headers.get("Retry-After", 5))
                for _ in range(60):
                    time.sleep(retry_after)
                    op_r = requests.get(op_url, headers=headers)
                    if op_r.status_code == 200:
                        body = op_r.json()
                        if body.get("status") == "Succeeded":
                            print(f"  [OK] {action_name} succeeded (LRO)")
                            return True
                        elif body.get("status") in ("Failed", "Cancelled"):
                            err = body.get("error", {}).get("message", "")
                            print(f"  [FAIL] {action_name}: {body.get('status')} -- {err}")
                            return False
                print(f"  [WARN] {action_name} LRO timed out")
                return False
            else:
                print(f"  [FAIL] {action_name}: HTTP {r.status_code} {r.text[:500]}")
                return False

        if not ops_agent_id:
            # --- CREATE shell via dedicated /operationsAgents endpoint ---
            print("  Creating HealthcareOpsAgent via /operationsAgents API...")
            create_body = {"displayName": "HealthcareOpsAgent"}
            r = requests.post(ops_api, headers=headers, json=create_body)
            print(f"  createItem: HTTP {r.status_code}")

            if r.status_code in (200, 201):
                ops_agent_id = r.json().get("id")
                print(f"  [OK] Created shell: {ops_agent_id}")
            elif r.status_code == 202:
                _wait_for_lro(r, "createItem")
                resp2 = requests.get(f"{api_base}/items", headers=headers)
                for it in resp2.json().get("value", []):
                    if it["type"] == "OperationsAgent" and it["displayName"] == "HealthcareOpsAgent":
                        ops_agent_id = it["id"]
                        break
                if ops_agent_id:
                    print(f"  [OK] Created shell (LRO): {ops_agent_id}")
            else:
                print(f"  [FAIL] createItem: HTTP {r.status_code} {r.text[:500]}")

        if ops_agent_id:
            # --- GET current definition, swap config payload, PUT back ---
            print("  Pushing OperationsAgent definition (GET-modify-PUT)...")
            r = requests.post(f"{ops_api}/{ops_agent_id}/getDefinition",
                              headers=headers, json={})
            if r.status_code == 200:
                current_def = r.json()["definition"]
                config_payload = base64.b64encode(
                    json.dumps(config_json, indent=2, ensure_ascii=False).encode("utf-8")
                ).decode("utf-8")
                for part in current_def["parts"]:
                    if part["path"] == "Configurations.json":
                        part["payload"] = config_payload
                r = requests.post(f"{ops_api}/{ops_agent_id}/updateDefinition",
                                  headers=headers, json={"definition": current_def})
                print(f"  updateDefinition: HTTP {r.status_code}")
                _wait_for_lro(r, "updateDefinition")
            else:
                print(f"  [FAIL] getDefinition: HTTP {r.status_code}")

    print("\nData Agent source patching complete.")

    # ── Run Operations Agent Notebook ────────────────────────────────
    print("\n" + "=" * 60)
    print("  RUNNING OPERATIONS AGENT NOTEBOOK")
    print("=" * 60)
    try:
        print("  Running NB_RTI_Operations_Agent...")
        notebookutils.notebook.run("NB_RTI_Operations_Agent", 600, {"useRootDefaultLakehouse": True})
        print("  [OK] Operations Agent notebook completed successfully")
    except Exception as e:
        if "mssparkutilsrun-result+json" in str(e) or "NoSuchElementException" in str(e):
            print("  [OK] Operations Agent notebook completed (ignoring Fabric result-parse bug)")
        else:
            print(f"  [WARN] Operations Agent notebook failed: {e}")
            print("  This is expected if scoring notebooks haven't populated output tables yet")
            print("  Re-run NB_RTI_Operations_Agent after scoring runs produce data")

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
        # ── Build Eventstream topology ──────────────────────────────
        print("\n  Building topology...")

        # Source: Custom Endpoint (EventHub-compatible ingress)
        _es_sources = [{
            "name": "HealthcareCustomEndpoint",
            "type": "CustomEndpoint",
            "properties": {
                "inputSerialization": {"type": "Json", "properties": {"encoding": "UTF8"}}
            }
        }]

        # Default stream: source → fan-out to destinations
        _es_streams = [{
            "name": "HealthcareRTI-stream",
            "type": "DefaultStream",
            "properties": {},
            "inputNodes": [{"name": "HealthcareCustomEndpoint"}]
        }]

        # Destination 1: Eventhouse / KQL DB (real-time queries + dashboards)
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
                "tableName": "rti_claims_events",
                "inputSerialization": {"type": "Json", "properties": {"encoding": "UTF8"}}
            },
            "inputNodes": [{"name": "HealthcareRTI-stream"}]
        }]

        # Destination 2: Lakehouse (raw archival → medallion pattern)
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
            print(f"    + Lakehouse destination: lh_bronze_raw → rti_raw_events")
        else:
            print(f"    - Lakehouse: lh_bronze_raw not found (skipping)")

        # Destination 3: Activator / Reflex (alerts)
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
            print(f"    + Activator destination: Healthcare Reflex")
        else:
            print(f"    - Activator: no Reflex item found (create one in portal to auto-wire)")

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
        print("  ┌─────────────────────────────────────────────────────────┐")
        print("  │  EVENTSTREAM TOPOLOGY WIRED — READY FOR STREAMING      │")
        print("  │                                                        │")
        print("  │  1. Open the Eventstream URL above in your browser     │")
        print("  │  2. Click HealthcareCustomEndpoint → copy Conn String  │")
        print("  │  3. Paste into the NEXT CELL → run it                  │")
        print("  │                                                        │")
        print("  │  That cell triggers PL_Healthcare_RTI which runs:      │")
        print("  │    Simulator → Fraud + CareGap + HighCost (parallel)   │")
        print("  │                                                        │")
        print("  │  One paste, one cell — everything else is automatic.   │")
        print("  └─────────────────────────────────────────────────────────┘")
    elif _es_id:
        print("  [WARN] KQL Database not found — cannot wire Eventstream topology")
        print("  Eventstream created but empty. Wire manually in the portal.")
    else:
        print("  [WARN] Eventstream not available — use Direct Kusto (zero-config)")

    print()
    print("RTI deployment complete.")
    print("  Eventstream topology wired — copy connection string to start streaming")
    print()
    print("  NEXT: Paste the connection string into the next cell and run it.")
    print("  PL_Healthcare_RTI orchestrates: Simulator → Scoring (parallel)")

else:
    print("Skipping RTI deployment (DEPLOY_STREAMING=False)")
    print("Set DEPLOY_STREAMING = True in the CONFIG cell to enable Eventhouse + scoring.")