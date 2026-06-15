# Fabric notebook source

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# # RTI Post-Deploy Setup
# 
# **Prerequisites:** The Eventhouse and KQL Database must already be deployed as Git artifacts
# (via `fabric-launcher` or `fabric-cicd`). This notebook performs post-deploy wiring:
# 
# 1. **Discover** Eventhouse + KQL Database by display name (zero hardcoded IDs)
# 2. **Execute** schema -- creates 6 tables + streaming ingestion policies + JSON mappings
# 3. **Discover** Kusto ingestion URI for downstream notebooks
# 
# > **Why direct Kusto ingestion?** This demo deploys everything programmatically
# > (zero portal clicks). Eventstream Custom Endpoints and their wiring to KQL destinations
# > cannot be fully configured via public API today, which would require manual portal steps.
# > Direct Kusto ingestion (`azure-kusto-ingest`) achieves the same streaming result with
# > zero user configuration.
# >
# > **In production**, you would typically ingest via:
# > - **Eventstream Custom Endpoint** -- for application-generated events
# > - **IoT Hub / IoT Central** -- for medical device telemetry (vitals, wearables)
# > - **Azure Event Hub** -- for high-throughput enterprise event buses
# > - **Change Data Capture** -- for database-sourced real-time feeds
# >
# > All of these route through Eventstream into the same KQL tables created here.
# 
# **Default lakehouse:** `lh_gold_curated`

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# NB_RTI_Setup_Eventhouse -- Post-Deploy Wiring
# ============================================================================
# The Eventhouse + KQL Database are deployed as Git artifacts by the launcher.
# This notebook discovers them, executes the schema, and outputs the Kusto
# ingestion URI for direct ingestion (no Eventstream needed).
#
# Zero hardcoded IDs -- everything resolved by displayName lookup.
# Default lakehouse: lh_gold_curated
# ============================================================================

print("NB_RTI_Setup_Eventhouse: Starting post-deploy setup...")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ---------- Parameters ----------
WORKSPACE_ID = ""                               # Auto-detected if blank
EVENTHOUSE_NAME = "Healthcare_RTI_Eventhouse"    # Must match Git artifact displayName
KQL_DB_NAME = "Healthcare_RTI_DB"                # Must match Git artifact displayName

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

import requests
import json
import time

def get_fabric_token():
    """Get Fabric API token from notebook context."""
    return notebookutils.credentials.getToken("https://analysis.windows.net/powerbi/api")

def get_kusto_token():
    """Get Kusto/ADX token for direct ingestion."""
    return notebookutils.credentials.getToken("kusto")

def get_headers():
    return {
        "Authorization": f"Bearer {get_fabric_token()}",
        "Content-Type": "application/json"
    }

BASE_URL = "https://api.fabric.microsoft.com/v1"

if not WORKSPACE_ID:
    WORKSPACE_ID = notebookutils.runtime.context.get("currentWorkspaceId", "")
    if not WORKSPACE_ID:
        raise ValueError("WORKSPACE_ID must be set -- could not auto-detect")

print(f"Workspace ID: {WORKSPACE_ID}")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# Step 1: Discover Eventhouse + KQL Database by displayName
# ============================================================================
print("Step 1: Discovering deployed RTI artifacts...")

def find_item(item_type, display_name):
    """Find a workspace item by type and displayName. Returns item dict or None."""
    url = f"{BASE_URL}/workspaces/{WORKSPACE_ID}/items?type={item_type}"
    resp = requests.get(url, headers=get_headers())
    resp.raise_for_status()
    for item in resp.json().get("value", []):
        if item["displayName"] == display_name:
            return item
    return None

# Discover Eventhouse
eventhouse = find_item("Eventhouse", EVENTHOUSE_NAME)
if not eventhouse:
    raise RuntimeError(
        f"Eventhouse '{EVENTHOUSE_NAME}' not found in workspace.\n"
        f"Ensure Healthcare_Launcher.ipynb deployed the Eventhouse artifact first.\n"
        f"Check the workspace for the item or re-run the launcher."
    )
eventhouse_id = eventhouse["id"]
print(f"  Eventhouse: {EVENTHOUSE_NAME} ({eventhouse_id})")

# Discover KQL Database
kql_db = find_item("KQLDatabase", KQL_DB_NAME)
if not kql_db:
    kql_db = find_item("KQLDatabase", EVENTHOUSE_NAME)
    if kql_db:
        KQL_DB_NAME = EVENTHOUSE_NAME
        print(f"  KQL Database found with Eventhouse name: {KQL_DB_NAME}")

if not kql_db:
    raise RuntimeError(
        f"KQL Database '{KQL_DB_NAME}' not found in workspace.\n"
        f"The KQL Database should be deployed as a Git artifact alongside the Eventhouse."
    )
kql_db_id = kql_db["id"]
print(f"  KQL Database: {KQL_DB_NAME} ({kql_db_id})")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# Step 2: Discover Kusto ingestion URI
# ============================================================================
print("Step 2: Discovering Kusto cluster URI...")

# Eventhouse properties contain the query and ingestion URIs
props_url = f"{BASE_URL}/workspaces/{WORKSPACE_ID}/eventhouses/{eventhouse_id}"
resp = requests.get(props_url, headers=get_headers())

KUSTO_QUERY_URI = ""
KUSTO_INGEST_URI = ""

if resp.status_code == 200:
    props = resp.json().get("properties", resp.json())
    KUSTO_QUERY_URI = props.get("queryServiceUri", "")
    KUSTO_INGEST_URI = props.get("ingestionServiceUri", "")
    if not KUSTO_INGEST_URI and KUSTO_QUERY_URI:
        # Derive ingestion URI from query URI
        KUSTO_INGEST_URI = KUSTO_QUERY_URI.replace("https://", "https://ingest-")

if not KUSTO_QUERY_URI:
    # Fallback: discover via KQL management command
    cmd_url = f"{BASE_URL}/workspaces/{WORKSPACE_ID}/kqlDatabases/{kql_db_id}/runCommand"
    cmd_resp = requests.post(cmd_url, headers=get_headers(),
                             json={"script": ".show cluster"})
    if cmd_resp.status_code == 200:
        try:
            rows = cmd_resp.json().get("results", [{}])[0].get("rows", [])
            if rows:
                # First column is typically the cluster URI
                KUSTO_QUERY_URI = rows[0][0] if isinstance(rows[0], list) else str(rows[0])
                KUSTO_INGEST_URI = KUSTO_QUERY_URI.replace("https://", "https://ingest-")
        except Exception as e:
            print(f"  WARN: Could not parse cluster info: {e}")

if KUSTO_QUERY_URI:
    print(f"  Query URI:     {KUSTO_QUERY_URI}")
    print(f"  Ingestion URI: {KUSTO_INGEST_URI}")
else:
    print("  WARN: Could not discover Kusto URIs -- Kusto ingestion will be skipped")
    print("  KQL tables will still be created for manual use")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# Step 3: Execute KQL schema -- create tables + streaming policies + mappings
# ============================================================================
print("Step 3: Executing KQL schema commands...")

KQL_COMMANDS = [
    # --- LANDING TABLE (all events from Eventstream land here) ---
    # The Eventstream writes ALL event types into this single table.
    # KQL update policies (defined below) automatically route rows
    # into the typed per-event tables based on the _table field.
    #
    # IMPORTANT: event_timestamp is STRING (not datetime) because Eventstream
    # ingests the ISO-format timestamp as a string. The Extract functions
    # convert it to datetime for the typed tables. quantity/days_supply are
    # LONG because that's what Eventstream infers from JSON integers.
    # If we use different types here (e.g. datetime, int), .create-merge will
    # FAIL when the table already exists (from Eventstream auto-creation),
    # and ALL new columns (claim_id, facility_id, etc.) will NOT be added.
    """.create-merge table rti_all_events (
        event_id: string, event_timestamp: string, event_type: string,
        _table: string,
        claim_id: string, patient_id: string, provider_id: string,
        facility_id: string, facility_name: string, payer_id: string,
        diagnosis_code: string, procedure_code: string,
        claim_type: string, claim_amount: real,
        admission_type: string, primary_diagnosis: string,
        medication_code: string, medication_name: string, drug_class: string,
        quantity: long, days_supply: long,
        latitude: real, longitude: real,
        injected_fraud_flags: string,
        has_open_care_gaps: bool, open_gap_measures: string
    )""",
    # DEFENSIVE: If .create-merge failed due to any residual type conflict,
    # this .alter-merge adds ONLY the string/real/bool columns that Eventstream
    # definitely didn't create (claims/ADT-specific columns). These types
    # cannot conflict because these columns won't exist yet.
    """.alter-merge table rti_all_events (
        claim_id: string, facility_id: string, facility_name: string,
        payer_id: string, diagnosis_code: string, procedure_code: string,
        claim_type: string, claim_amount: real,
        admission_type: string, primary_diagnosis: string,
        has_open_care_gaps: bool, open_gap_measures: string,
        injected_fraud_flags: string, _table: string
    )""",
    # --- INPUT TABLES ---
    """.create-merge table claims_events (
        event_id: string, event_timestamp: datetime, event_type: string,
        claim_id: string, patient_id: string, provider_id: string,
        facility_id: string, payer_id: string, diagnosis_code: string,
        procedure_code: string, claim_type: string, claim_amount: real,
        latitude: real, longitude: real, injected_fraud_flags: string
    )""",
    """.create-merge table adt_events (
        event_id: string, event_timestamp: datetime, event_type: string,
        patient_id: string, facility_id: string, facility_name: string,
        admission_type: string, primary_diagnosis: string,
        latitude: real, longitude: real,
        has_open_care_gaps: bool, open_gap_measures: string
    )""",
    """.create-merge table rx_events (
        event_id: string, event_timestamp: datetime, event_type: string,
        patient_id: string, provider_id: string, medication_code: string,
        medication_name: string, drug_class: string,
        quantity: int, days_supply: int, latitude: real, longitude: real
    )""",
    # --- OUTPUT / SCORED TABLES ---
    """.create-merge table fraud_scores (
        score_id: string, score_timestamp: datetime, claim_id: string,
        patient_id: string, provider_id: string, facility_id: string,
        claim_amount: real, fraud_score: real, fraud_flags: string,
        risk_tier: string, latitude: real, longitude: real
    )""",
    """.create-merge table care_gap_alerts (
        alert_id: string, alert_timestamp: datetime, patient_id: string,
        facility_id: string, facility_name: string, measure_id: string,
        measure_name: string, gap_days_overdue: int, alert_priority: string,
        alert_text: string, latitude: real, longitude: real
    )""",
    """.create-merge table highcost_alerts (
        alert_id: string, alert_timestamp: datetime, patient_id: string,
        facility_id: string, facility_name: string,
        rolling_spend_30d: real, rolling_spend_90d: real, ed_visits_30d: int,
        readmission_flag: bool, risk_tier: string, cost_trend: string,
        latitude: real, longitude: real
    )""",
    # --- STREAMING INGESTION POLICIES (landing + 6 typed tables) ---
    ".alter table rti_all_events policy streamingingestion enable",
    ".alter table claims_events policy streamingingestion enable",
    ".alter table adt_events policy streamingingestion enable",
    ".alter table rx_events policy streamingingestion enable",
    ".alter table fraud_scores policy streamingingestion enable",
    ".alter table care_gap_alerts policy streamingingestion enable",
    ".alter table highcost_alerts policy streamingingestion enable",
    # --- UPDATE POLICIES (auto-route from rti_all_events → typed tables) ---
    # These server-side policies fire on every ingestion batch into rti_all_events,
    # extracting rows by _table field and appending them to the target tables.
    # Note: todatetime() is needed because event_timestamp arrives as string from Eventstream.
    # toint()/coalesce() handle columns that may be null in the landing table.
    # coalesce() on claim-specific fields handles the case where the Eventstream
    # created rti_all_events before these columns were added.
    """.create-or-alter function ExtractClaimsEvents() {
        rti_all_events
        | where _table == "claims_events"
        | project event_id,
                  event_timestamp = todatetime(event_timestamp),
                  event_type,
                  claim_id = coalesce(claim_id, ""),
                  patient_id,
                  provider_id = coalesce(provider_id, ""),
                  facility_id = coalesce(facility_id, ""),
                  payer_id = coalesce(payer_id, ""),
                  diagnosis_code = coalesce(diagnosis_code, ""),
                  procedure_code = coalesce(procedure_code, ""),
                  claim_type = coalesce(claim_type, ""),
                  claim_amount = coalesce(claim_amount, 0.0),
                  latitude,
                  longitude,
                  injected_fraud_flags = coalesce(injected_fraud_flags, "")
    }""",
    """.create-or-alter function ExtractAdtEvents() {
        rti_all_events
        | where _table == "adt_events"
        | project event_id,
                  event_timestamp = todatetime(event_timestamp),
                  event_type, patient_id,
                  facility_id = coalesce(facility_id, ""),
                  facility_name = coalesce(facility_name, ""),
                  admission_type = coalesce(admission_type, ""),
                  primary_diagnosis = coalesce(primary_diagnosis, ""),
                  latitude, longitude,
                  has_open_care_gaps = coalesce(has_open_care_gaps, false),
                  open_gap_measures = coalesce(open_gap_measures, "")
    }""",
    """.create-or-alter function ExtractRxEvents() {
        rti_all_events
        | where _table == "rx_events"
        | project event_id,
                  event_timestamp = todatetime(event_timestamp),
                  event_type, patient_id,
                  provider_id = coalesce(provider_id, ""),
                  medication_code = coalesce(medication_code, ""),
                  medication_name = coalesce(medication_name, ""),
                  drug_class = coalesce(drug_class, ""),
                  quantity = toint(coalesce(quantity, 0)),
                  days_supply = toint(coalesce(days_supply, 0)),
                  latitude, longitude
    }""",
    ".alter table claims_events policy update @'[{\"IsEnabled\": true, \"Source\": \"rti_all_events\", \"Query\": \"ExtractClaimsEvents()\", \"IsTransactional\": false, \"PropagateIngestionProperties\": true}]'",
    ".alter table adt_events policy update @'[{\"IsEnabled\": true, \"Source\": \"rti_all_events\", \"Query\": \"ExtractAdtEvents()\", \"IsTransactional\": false, \"PropagateIngestionProperties\": true}]'",
    ".alter table rx_events policy update @'[{\"IsEnabled\": true, \"Source\": \"rti_all_events\", \"Query\": \"ExtractRxEvents()\", \"IsTransactional\": false, \"PropagateIngestionProperties\": true}]'",
    # --- ONELAKE MIRRORING POLICIES (5-minute flush for demos) ---
    # OneLake Availability must be enabled on the KQL DB first (portal toggle).
    # These policies set the delta-table flush to 5 minutes instead of the
    # default 3 hours, so scoring notebooks see data quickly after streaming.
    ".alter-merge table claims_events policy mirroring dataformat=parquet with (IsEnabled=true, TargetLatencyInMinutes=5)",
    ".alter-merge table adt_events policy mirroring dataformat=parquet with (IsEnabled=true, TargetLatencyInMinutes=5)",
    ".alter-merge table rx_events policy mirroring dataformat=parquet with (IsEnabled=true, TargetLatencyInMinutes=5)",
    # --- JSON INGESTION MAPPINGS ---
    """.create-or-alter table rti_all_events ingestion json mapping 'rti_all_events_mapping'
    '[{"column":"event_id","path":"$.event_id","datatype":"string"},{"column":"event_timestamp","path":"$.event_timestamp","datatype":"string"},{"column":"event_type","path":"$.event_type","datatype":"string"},{"column":"_table","path":"$._table","datatype":"string"},{"column":"claim_id","path":"$.claim_id","datatype":"string"},{"column":"patient_id","path":"$.patient_id","datatype":"string"},{"column":"provider_id","path":"$.provider_id","datatype":"string"},{"column":"facility_id","path":"$.facility_id","datatype":"string"},{"column":"facility_name","path":"$.facility_name","datatype":"string"},{"column":"payer_id","path":"$.payer_id","datatype":"string"},{"column":"diagnosis_code","path":"$.diagnosis_code","datatype":"string"},{"column":"procedure_code","path":"$.procedure_code","datatype":"string"},{"column":"claim_type","path":"$.claim_type","datatype":"string"},{"column":"claim_amount","path":"$.claim_amount","datatype":"real"},{"column":"admission_type","path":"$.admission_type","datatype":"string"},{"column":"primary_diagnosis","path":"$.primary_diagnosis","datatype":"string"},{"column":"medication_code","path":"$.medication_code","datatype":"string"},{"column":"medication_name","path":"$.medication_name","datatype":"string"},{"column":"drug_class","path":"$.drug_class","datatype":"string"},{"column":"quantity","path":"$.quantity","datatype":"long"},{"column":"days_supply","path":"$.days_supply","datatype":"long"},{"column":"latitude","path":"$.latitude","datatype":"real"},{"column":"longitude","path":"$.longitude","datatype":"real"},{"column":"injected_fraud_flags","path":"$.injected_fraud_flags","datatype":"string"},{"column":"has_open_care_gaps","path":"$.has_open_care_gaps","datatype":"bool"},{"column":"open_gap_measures","path":"$.open_gap_measures","datatype":"string"}]'""",
    """.create-or-alter table claims_events ingestion json mapping 'claims_events_mapping'
    '[{"column":"event_id","path":"$.event_id","datatype":"string"},{"column":"event_timestamp","path":"$.event_timestamp","datatype":"datetime"},{"column":"event_type","path":"$.event_type","datatype":"string"},{"column":"claim_id","path":"$.claim_id","datatype":"string"},{"column":"patient_id","path":"$.patient_id","datatype":"string"},{"column":"provider_id","path":"$.provider_id","datatype":"string"},{"column":"facility_id","path":"$.facility_id","datatype":"string"},{"column":"payer_id","path":"$.payer_id","datatype":"string"},{"column":"diagnosis_code","path":"$.diagnosis_code","datatype":"string"},{"column":"procedure_code","path":"$.procedure_code","datatype":"string"},{"column":"claim_type","path":"$.claim_type","datatype":"string"},{"column":"claim_amount","path":"$.claim_amount","datatype":"real"},{"column":"latitude","path":"$.latitude","datatype":"real"},{"column":"longitude","path":"$.longitude","datatype":"real"},{"column":"injected_fraud_flags","path":"$.injected_fraud_flags","datatype":"string"}]'""",
    """.create-or-alter table adt_events ingestion json mapping 'adt_events_mapping'
    '[{"column":"event_id","path":"$.event_id","datatype":"string"},{"column":"event_timestamp","path":"$.event_timestamp","datatype":"datetime"},{"column":"event_type","path":"$.event_type","datatype":"string"},{"column":"patient_id","path":"$.patient_id","datatype":"string"},{"column":"facility_id","path":"$.facility_id","datatype":"string"},{"column":"facility_name","path":"$.facility_name","datatype":"string"},{"column":"admission_type","path":"$.admission_type","datatype":"string"},{"column":"primary_diagnosis","path":"$.primary_diagnosis","datatype":"string"},{"column":"latitude","path":"$.latitude","datatype":"real"},{"column":"longitude","path":"$.longitude","datatype":"real"},{"column":"has_open_care_gaps","path":"$.has_open_care_gaps","datatype":"bool"},{"column":"open_gap_measures","path":"$.open_gap_measures","datatype":"string"}]'""",
    """.create-or-alter table rx_events ingestion json mapping 'rx_events_mapping'
    '[{"column":"event_id","path":"$.event_id","datatype":"string"},{"column":"event_timestamp","path":"$.event_timestamp","datatype":"datetime"},{"column":"event_type","path":"$.event_type","datatype":"string"},{"column":"patient_id","path":"$.patient_id","datatype":"string"},{"column":"provider_id","path":"$.provider_id","datatype":"string"},{"column":"medication_code","path":"$.medication_code","datatype":"string"},{"column":"medication_name","path":"$.medication_name","datatype":"string"},{"column":"drug_class","path":"$.drug_class","datatype":"string"},{"column":"quantity","path":"$.quantity","datatype":"int"},{"column":"days_supply","path":"$.days_supply","datatype":"int"},{"column":"latitude","path":"$.latitude","datatype":"real"},{"column":"longitude","path":"$.longitude","datatype":"real"}]'""",
    """.create-or-alter table fraud_scores ingestion json mapping 'fraud_scores_mapping'
    '[{"column":"score_id","path":"$.score_id","datatype":"string"},{"column":"score_timestamp","path":"$.score_timestamp","datatype":"datetime"},{"column":"claim_id","path":"$.claim_id","datatype":"string"},{"column":"patient_id","path":"$.patient_id","datatype":"string"},{"column":"provider_id","path":"$.provider_id","datatype":"string"},{"column":"facility_id","path":"$.facility_id","datatype":"string"},{"column":"claim_amount","path":"$.claim_amount","datatype":"real"},{"column":"fraud_score","path":"$.fraud_score","datatype":"real"},{"column":"fraud_flags","path":"$.fraud_flags","datatype":"string"},{"column":"risk_tier","path":"$.risk_tier","datatype":"string"},{"column":"latitude","path":"$.latitude","datatype":"real"},{"column":"longitude","path":"$.longitude","datatype":"real"}]'""",
    """.create-or-alter table care_gap_alerts ingestion json mapping 'care_gap_alerts_mapping'
    '[{"column":"alert_id","path":"$.alert_id","datatype":"string"},{"column":"alert_timestamp","path":"$.alert_timestamp","datatype":"datetime"},{"column":"patient_id","path":"$.patient_id","datatype":"string"},{"column":"facility_id","path":"$.facility_id","datatype":"string"},{"column":"facility_name","path":"$.facility_name","datatype":"string"},{"column":"measure_id","path":"$.measure_id","datatype":"string"},{"column":"measure_name","path":"$.measure_name","datatype":"string"},{"column":"gap_days_overdue","path":"$.gap_days_overdue","datatype":"int"},{"column":"alert_priority","path":"$.alert_priority","datatype":"string"},{"column":"alert_text","path":"$.alert_text","datatype":"string"},{"column":"latitude","path":"$.latitude","datatype":"real"},{"column":"longitude","path":"$.longitude","datatype":"real"}]'""",
    """.create-or-alter table highcost_alerts ingestion json mapping 'highcost_alerts_mapping'
    '[{"column":"alert_id","path":"$.alert_id","datatype":"string"},{"column":"alert_timestamp","path":"$.alert_timestamp","datatype":"datetime"},{"column":"patient_id","path":"$.patient_id","datatype":"string"},{"column":"facility_id","path":"$.facility_id","datatype":"string"},{"column":"facility_name","path":"$.facility_name","datatype":"string"},{"column":"rolling_spend_30d","path":"$.rolling_spend_30d","datatype":"real"},{"column":"rolling_spend_90d","path":"$.rolling_spend_90d","datatype":"real"},{"column":"ed_visits_30d","path":"$.ed_visits_30d","datatype":"int"},{"column":"readmission_flag","path":"$.readmission_flag","datatype":"bool"},{"column":"risk_tier","path":"$.risk_tier","datatype":"string"},{"column":"cost_trend","path":"$.cost_trend","datatype":"string"},{"column":"latitude","path":"$.latitude","datatype":"real"},{"column":"longitude","path":"$.longitude","datatype":"real"}]'""",
]

# --- Install Kusto SDK if not already present ---
import subprocess, sys
try:
    from azure.kusto.data import KustoClient, KustoConnectionStringBuilder
    from azure.kusto.data.exceptions import KustoServiceError
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "azure-kusto-data"])
    # Purge stale azure.* module refs so fresh import works
    import importlib
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith("azure"):
            del sys.modules[mod_name]
    from azure.kusto.data import KustoClient, KustoConnectionStringBuilder
    from azure.kusto.data.exceptions import KustoServiceError

_kql_token = get_kusto_token()
_kcs = KustoConnectionStringBuilder.with_aad_user_token_authentication(KUSTO_QUERY_URI, _kql_token)
_kusto_client = KustoClient(_kcs)

def run_kql_mgmt(command):
    """Execute a KQL management command via Kusto SDK."""
    return _kusto_client.execute_mgmt(KQL_DB_NAME, command.strip())

def run_kql_query(query):
    """Execute a KQL query via Kusto SDK."""
    return _kusto_client.execute(KQL_DB_NAME, query.strip())

success_count = 0
fail_count = 0
for cmd in KQL_COMMANDS:
    cmd_clean = cmd.strip()
    if not cmd_clean:
        continue
    if "create-merge table" in cmd_clean or "alter-merge table" in cmd_clean:
        label = cmd_clean.split("table ")[-1].split(" ")[0].split("(")[0].strip()
    elif "alter table" in cmd_clean and "policy" in cmd_clean:
        label = "streaming policy: " + cmd_clean.split("table ")[-1].split(" ")[0]
    elif "ingestion json mapping" in cmd_clean:
        label = "mapping: " + cmd_clean.split("table ")[-1].split(" ")[0]
    else:
        label = cmd_clean[:60]
    try:
        run_kql_mgmt(cmd_clean)
        print(f"  OK: {label}")
        success_count += 1
    except KustoServiceError as e:
        print(f"  WARN: {label} -- {str(e)[:200]}")
        fail_count += 1
    except Exception as e:
        print(f"  WARN: {label} -- {str(e)[:200]}")
        fail_count += 1

print(f"\nSchema execution complete: {success_count} succeeded, {fail_count} failed")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# Step 3b: Backfill typed tables from existing rti_all_events data
# ============================================================================
# KQL update policies only process NEW ingestion. If rti_all_events already
# has data (e.g. simulator ran before policies were created), we must backfill
# the typed tables once. This is idempotent: checks if target is empty first.
# ============================================================================
print("Step 3b: Checking if backfill is needed...")

BACKFILL_COMMANDS = [
    # Check counts and backfill if needed
    ("claims_events", ".set-or-append claims_events <| ExtractClaimsEvents()"),
    ("adt_events", ".set-or-append adt_events <| ExtractAdtEvents()"),
    ("rx_events", ".set-or-append rx_events <| ExtractRxEvents()"),
]

# First check if rti_all_events has any data
_landing_count = 0
try:
    _result = run_kql_query("rti_all_events | count")
    for row in _result.primary_results[0]:
        _landing_count = int(row[0])
except Exception:
    pass

if _landing_count > 0:
    print(f"  rti_all_events has {_landing_count} rows — checking typed tables...")
    for _tbl_name, _backfill_cmd in BACKFILL_COMMANDS:
        # Check if target already has data
        _tbl_count = 0
        try:
            _cnt_result = run_kql_query(f"{_tbl_name} | count")
            for row in _cnt_result.primary_results[0]:
                _tbl_count = int(row[0])
        except Exception:
            pass
        if _tbl_count == 0:
            print(f"  Backfilling {_tbl_name} from rti_all_events...")
            try:
                run_kql_mgmt(_backfill_cmd)
                print(f"    OK: {_tbl_name} backfilled")
            except Exception as e:
                print(f"    WARN: {_tbl_name} -- {str(e)[:200]}")
        else:
            print(f"  {_tbl_name}: already has {_tbl_count} rows — skipping backfill")
else:
    print("  rti_all_events is empty — no backfill needed (data will flow via update policies)")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# Step 4: Verify setup
# ============================================================================
print("\nStep 4: Verifying RTI setup...")

try:
    _verify_result = run_kql_mgmt(".show tables | project TableName | order by TableName asc")
    print("  KQL Database tables:")
    for row in _verify_result.primary_results[0]:
        print(f"    - {row[0]}")
except Exception as e:
    print(f"  Could not verify tables: {str(e)[:200]}")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# Step 5: Store Kusto URIs for downstream notebooks
# ============================================================================
# The Event Simulator and scoring notebooks use these to push data to KQL.
# notebookutils.notebook.run() shares the mssparkutils context automatically,
# but we also store them as notebook exit values for explicit passing.

print("Step 5: Storing Kusto configuration...")

kusto_config = {
    "kusto_query_uri": KUSTO_QUERY_URI,
    "kusto_ingest_uri": KUSTO_INGEST_URI,
    "kql_db_name": KQL_DB_NAME,
    "eventhouse_id": eventhouse_id,
    "kql_db_id": kql_db_id,
}

# Store as notebook output for downstream consumption
notebookutils.notebook.exit(json.dumps(kusto_config))

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ---------- Summary ----------
print("\n" + "=" * 70)
print("  NB_RTI_Setup_Eventhouse: COMPLETE")
print("=" * 70)
print()
print(f"  Workspace:     {WORKSPACE_ID}")
print(f"  Eventhouse:    {EVENTHOUSE_NAME} ({eventhouse_id})")
print(f"  KQL DB:        {KQL_DB_NAME} ({kql_db_id})")
print(f"  Query URI:     {KUSTO_QUERY_URI}")
print(f"  Ingestion URI: {KUSTO_INGEST_URI}")
print()
print("  KQL Tables (7):")
print("    LANDING: rti_all_events (Eventstream → update policies split to typed tables)")
print("    INPUT:  claims_events, adt_events, rx_events")
print("    OUTPUT: fraud_scores, care_gap_alerts, highcost_alerts")
print()
print("  Ingestion: Direct Kusto (azure-kusto-ingest, pre-installed)")
print("    - Zero config: token from notebookutils.credentials.getToken('kusto')")
print("    - No Eventstream or connection strings needed")
print()
print("  Next Steps:")
print("    1. Run NB_RTI_Event_Simulator (batch mode) to seed events")
print("    2. Run NB_RTI_Fraud_Detection to score claims")
print("    3. Run NB_RTI_Care_Gap_Alerts for point-of-care alerts")
print("    4. Run NB_RTI_HighCost_Trajectory for cost trend analysis")
print("    5. For live streaming: set MODE='stream' in Event Simulator")
print("       (uses direct Kusto ingestion -- no manual config needed)")
print("=" * 70)

# METADATA **{"language":"python"}**
