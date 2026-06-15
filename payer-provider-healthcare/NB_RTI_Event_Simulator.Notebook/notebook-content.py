# Fabric notebook source

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# # RTI Event Simulator — Streaming Healthcare Events
# 
# Generates realistic **streaming** events for **3 RTI use cases**:
# 1. **Claims Fraud Detection** — Claims submissions with amounts, diagnoses, geo
# 2. **Care Gap Closure** — ADT admit/discharge events triggering gap checks
# 3. **High-Cost Member Trajectory** — Claims + ED visits for rolling cost analysis
# 
# **How it works — Eventstream ingestion:**
# 
# ```
# This Notebook  ──► Eventstream Custom Endpoint (EventHub protocol)
#                         ├──► Eventhouse (rti_all_events → update policies → scoring)
#                         ├──► Lakehouse (lh_bronze_raw)  (raw archival)
#                         └──► Activator / Reflex   (fraud/care-gap alerts)
# ```
# 
# **Eventstream** is the primary ingestion path. Events are pushed to the
# Custom Endpoint using EventHub protocol. The Eventstream topology routes
# data to all destinations (Eventhouse, Lakehouse, Activator) automatically.
# 
# **Default lakehouse:** `lh_gold_curated`

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# NB_RTI_Event_Simulator
# ============================================================================
# Generates streaming healthcare events for 3 Fabric RTI use cases:
#   - Claims Fraud Detection (claims_events)
#   - Care Gap Closure (adt_events)
#   - High-Cost Member Trajectory (claims + ED events)
#
# Reads dimension/fact tables from lh_gold_curated, produces event batches.
# Primary path: Eventstream Custom Endpoint (EventHub protocol)
#   → Eventhouse + Lakehouse + Activator (all routed by Eventstream topology)
# Default lakehouse: lh_gold_curated
# ============================================================================

print("NB_RTI_Event_Simulator: Starting...")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ---------- Attach default lakehouse (self-healing) ----------
# When run via notebookutils.notebook.run(), the child notebook may not
# inherit the caller's lakehouse context. Discover and attach lh_gold_curated
# so spark.table("lh_gold_curated.xxx") resolves correctly.
import requests as _req
_ws_id = notebookutils.runtime.context.get("currentWorkspaceId", "")
_tok = notebookutils.credentials.getToken("pbi")
_hdr = {"Authorization": f"Bearer {_tok}"}
_lh_resp = _req.get(f"https://api.fabric.microsoft.com/v1/workspaces/{_ws_id}/lakehouses", headers=_hdr)
if _lh_resp.status_code == 200:
    for _lh in _lh_resp.json().get("value", []):
        if _lh["displayName"] == "lh_gold_curated":
            _lh_id = _lh["id"]
            _attached = False
            try:
                notebookutils.lakehouse.setDefaultLakehouse(_ws_id, _lh_id)
                print(f"  Attached lh_gold_curated ({_lh_id[:8]}...)")
                _attached = True
            except (AttributeError, Exception):
                pass
            if not _attached:
                import re as _re_mod
                _abfss = f"abfss://{_ws_id}@onelake.dfs.fabric.microsoft.com/{_lh_id}/Tables"
                _orig_sql = spark.sql
                def _patched_sql(query, _base=_abfss, _orig=_orig_sql):
                    query = _re_mod.sub(
                        r'\blh_gold_curated\.(\w+)\b',
                        lambda m: f'delta.`{_base}/{m.group(1)}`',
                        query
                    )
                    return _orig(query)
                spark.sql = _patched_sql
                # Also patch saveAsTable for DataFrame writes
                from pyspark.sql import DataFrameWriter as _DFW
                _orig_sat = _DFW.saveAsTable
                def _patched_sat(self, name, _base=_abfss, _orig=_orig_sat, **kwargs):
                    if name.startswith('lh_gold_curated.'):
                        tbl = name.split('.', 1)[1]
                        self.save(f'{_base}/{tbl}')
                        return
                    return _orig(self, name, **kwargs)
                _DFW.saveAsTable = _patched_sat
                # Also patch spark.table() for reading
                _orig_table = spark.table
                def _patched_table(name, _base=_abfss, _orig=_orig_table):
                    if name.startswith('lh_gold_curated.'):
                        tbl = name.split('.', 1)[1]
                        return spark.read.format('delta').load(f'{_base}/{tbl}')
                    return _orig(name)
                spark.table = _patched_table
                print(f"  Registered lh_gold_curated via ABFSS path rewriter ({_lh_id[:8]}...)")
                _attached = True
            if not _attached:
                print(f"  WARNING: Could not attach lh_gold_curated ({_lh_id[:8]}...)")
                print(f"  Lakehouse methods: {[m for m in dir(notebookutils.lakehouse) if not m.startswith('_')]}")
            break
    else:
        print("  WARNING: lh_gold_curated not found in workspace")
else:
    print(f"  WARNING: Could not list lakehouses (HTTP {_lh_resp.status_code})")
del _req, _ws_id, _tok, _hdr, _lh_resp

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

%pip install azure-eventhub azure-core>=1.31.0 --quiet

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ---------- Parameters (override from pipeline or %run) ----------
BATCH_SIZE = 500         # events per streaming batch
STREAM_INTERVAL_SEC = 5  # seconds between batches
STREAM_BATCHES = STREAM_BATCHES if "STREAM_BATCHES" in dir() and STREAM_BATCHES else 10

# ┌─────────────────────────────────────────────────────────────────┐
# │  PASTE YOUR EVENTSTREAM CONNECTION STRING BELOW                │
# │                                                                │
# │  1. Open Healthcare_RTI_Eventstream in the Fabric portal       │
# │  2. Click 'HealthcareCustomEndpoint' source node               │
# │  3. Copy the Connection String → paste below                   │
# │                                                                │
# │  Or run PL_Healthcare_RTI pipeline with ES_CONNECTION_STRING   │
# │  parameter — it passes the value to this notebook.             │
# └─────────────────────────────────────────────────────────────────┘
ES_CONNECTION_STRING = ES_CONNECTION_STRING if "ES_CONNECTION_STRING" in dir() and ES_CONNECTION_STRING else ""

# METADATA **{"language":"python","tags":["parameters"]}**

# CELL **{"language":"python"}**

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import uuid
import json
import requests

np.random.seed(None)  # Truly random for each run

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ---------- Connect to Eventstream (primary) + KQL Eventhouse (verification) ----------
#
# Primary:   Eventstream Custom Endpoint → Eventhouse + Lakehouse + Activator
# KQL query: Used only to verify data landed in Eventhouse after streaming

WORKSPACE_ID = notebookutils.runtime.context.get("currentWorkspaceId", "")

# ── Primary path: Eventstream Custom Endpoint ──
_es_producer = None
if ES_CONNECTION_STRING:
    try:
        from azure.eventhub import EventHubProducerClient, EventData
        _es_producer = EventHubProducerClient.from_connection_string(ES_CONNECTION_STRING)
        print(f"  Eventstream: Connected (primary ingestion path)")
        print(f"    → Eventhouse (rti_all_events → update policies → scoring)")
        print(f"    → Lakehouse (raw archival)")
        print(f"    → Activator (real-time alerts)")
    except Exception as _es_err:
        print(f"  Eventstream ERROR: Could not connect -- {_es_err}")
else:
    print("  ERROR: No ES_CONNECTION_STRING provided.")
    print("  Copy from Healthcare_RTI_Eventstream → HealthcareCustomEndpoint → Connection String")

# ── KQL query path (verification only — not used for ingestion) ──
_KUSTO_QUERY_URI = ""
_KQL_DB_NAME = "Healthcare_RTI_DB"
_fabric_tok = notebookutils.credentials.getToken("pbi")
_hdr = {"Authorization": f"Bearer {_fabric_tok}", "Content-Type": "application/json"}

_eh_resp = requests.get(
    f"https://api.fabric.microsoft.com/v1/workspaces/{WORKSPACE_ID}/items?type=Eventhouse",
    headers=_hdr
)
if _eh_resp.status_code == 200:
    for _item in _eh_resp.json().get("value", []):
        if "Healthcare" in _item.get("displayName", ""):
            _props_resp = requests.get(
                f"https://api.fabric.microsoft.com/v1/workspaces/{WORKSPACE_ID}/eventhouses/{_item['id']}",
                headers=_hdr
            )
            if _props_resp.status_code == 200:
                _props = _props_resp.json().get("properties", _props_resp.json())
                _KUSTO_QUERY_URI = _props.get("queryServiceUri", "")
            break

if _KUSTO_QUERY_URI:
    print(f"  KQL verify: {_KUSTO_QUERY_URI} (query-only, not for ingestion)")

if not _es_producer:
    print("="*60)
    print("  ERROR: Eventstream is not available.")
    print("  Set ES_CONNECTION_STRING and re-run this notebook.")
    print("="*60)

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ---------- KQL Query (verification only) ----------
# Used after streaming to confirm data landed in Eventhouse via Eventstream.

def _get_kusto_token():
    """Get a fresh Kusto token (tokens expire, so refresh per batch)."""
    return notebookutils.credentials.getToken("kusto")

def _kql_query(query, token=None):
    """Execute a KQL query via REST API. Returns rows list or []."""
    if not _KUSTO_QUERY_URI:
        return []
    tok = token or _get_kusto_token()
    headers = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    resp = requests.post(
        f"{_KUSTO_QUERY_URI}/v1/rest/query",
        headers=headers,
        json={"db": _KQL_DB_NAME, "csl": query},
    )
    if resp.status_code != 200:
        return []
    data = resp.json()
    if data.get("Tables") and data["Tables"][0].get("Rows"):
        return data["Tables"][0]["Rows"]
    return []

# ---------- Eventstream (primary ingestion path) ----------

def push_to_eventstream(df_pandas, table_name):
    """Push events to Eventstream Custom Endpoint → Eventhouse + Lakehouse + Activator."""
    if _es_producer is None:
        return False
    try:
        records = df_pandas.to_dict(orient="records")
        batch = _es_producer.create_batch()
        for record in records:
            record["_table"] = table_name
            for k, v in record.items():
                if hasattr(v, 'isoformat'):
                    record[k] = v.isoformat()
            event = EventData(json.dumps(record))
            try:
                batch.add(event)
            except ValueError:
                _es_producer.send_batch(batch)
                batch = _es_producer.create_batch()
                batch.add(event)
        _es_producer.send_batch(batch)
        print(f"  Eventstream: {len(df_pandas)} events -> {table_name}")
        return True
    except Exception as e:
        print(f"  Eventstream ERROR: {table_name} push failed: {e}")
        return False

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ---------- Load dimension/fact data from Gold lakehouse ----------
print("Loading dimension tables from lh_gold_curated...")

df_patients = spark.sql("SELECT patient_id, first_name, last_name, gender, date_of_birth, zip_code FROM lh_gold_curated.dim_patient WHERE is_current = true").toPandas()
df_providers = spark.sql("SELECT provider_id, display_name AS provider_name, specialty, facility_id FROM lh_gold_curated.dim_provider WHERE is_current = true").toPandas()
df_facilities = spark.sql("SELECT facility_id, facility_name, facility_type, latitude, longitude FROM lh_gold_curated.dim_facility").toPandas()
df_diagnoses = spark.sql("SELECT DISTINCT icd_code AS diagnosis_code, icd_description AS diagnosis_description FROM lh_gold_curated.dim_diagnosis").toPandas()
df_medications = spark.sql("SELECT DISTINCT rxnorm_code AS medication_code, medication_name, drug_class FROM lh_gold_curated.dim_medication").toPandas()
df_payers = spark.sql("SELECT payer_id, payer_name, payer_type AS plan_type FROM lh_gold_curated.dim_payer").toPandas()

try:
    df_care_gaps = spark.sql("SELECT patient_id, measure_id, measure_name, is_gap_open, gap_days_overdue FROM lh_gold_curated.care_gaps WHERE is_gap_open = true").toPandas()
    print(f"  Loaded {len(df_care_gaps)} open care gaps")
except Exception:
    df_care_gaps = pd.DataFrame(columns=["patient_id", "measure_id", "measure_name", "is_gap_open", "gap_days_overdue"])
    print("  No care_gaps table found -- care gap alerts will be empty")

print(f"  Patients: {len(df_patients)}, Providers: {len(df_providers)}, Facilities: {len(df_facilities)}")
print(f"  Diagnoses: {len(df_diagnoses)}, Medications: {len(df_medications)}, Payers: {len(df_payers)}")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ---------- Reference data for realistic event generation ----------

CLAIM_TYPES = ["professional", "institutional", "pharmacy"]
ADT_EVENT_TYPES = ["ADMIT", "DISCHARGE", "TRANSFER", "OBSERVATION"]
ADMISSION_TYPES = ["EMERGENCY", "URGENT", "ELECTIVE", "NEWBORN"]

PROCEDURE_CODES = {
    "Cardiology": ["99213", "99214", "93000", "93306", "93458"],
    "Orthopedics": ["99213", "99214", "27447", "27130", "29881"],
    "Oncology": ["99214", "99215", "96413", "77386", "88305"],
    "Primary Care": ["99213", "99214", "99215", "99396", "90471"],
    "Neurology": ["99213", "99214", "95819", "70553", "95910"],
    "Emergency Medicine": ["99281", "99282", "99283", "99284", "99285"],
    "Pediatrics": ["99213", "99214", "99392", "99393", "90471"],
    "Internal Medicine": ["99213", "99214", "99215", "99396", "80053"],
}

FRAUD_PATTERNS = {
    "velocity": 0.03,
    "geo_anomaly": 0.02,
    "amount_outlier": 0.04,
    "upcoding": 0.03,
}

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# Event Generator Functions
# ============================================================================

def generate_claims_events(n: int) -> pd.DataFrame:
    """Generate n claims submission events with controlled fraud pattern injection."""
    events = []
    now = datetime.utcnow()

    fraud_velocity_providers = set(
        df_providers.sample(max(1, int(len(df_providers) * FRAUD_PATTERNS["velocity"])))["provider_id"]
    )

    for i in range(n):
        patient = df_patients.sample(1).iloc[0]
        provider = df_providers.sample(1).iloc[0]
        payer = df_payers.sample(1).iloc[0]

        fac = df_facilities[df_facilities["facility_id"] == provider["facility_id"]]
        lat = float(fac["latitude"].iloc[0]) if len(fac) > 0 and pd.notna(fac["latitude"].iloc[0]) else 42.96
        lon = float(fac["longitude"].iloc[0]) if len(fac) > 0 and pd.notna(fac["longitude"].iloc[0]) else -85.67

        diag = df_diagnoses.sample(1).iloc[0] if len(df_diagnoses) > 0 else {"diagnosis_code": "Z00.00", "diagnosis_description": "General exam"}

        specialty = provider.get("specialty", "Primary Care")
        proc_codes = PROCEDURE_CODES.get(specialty, PROCEDURE_CODES["Primary Care"])
        proc_code = random.choice(proc_codes)

        claim_type = random.choice(CLAIM_TYPES)
        if claim_type == "institutional":
            base_amount = round(random.gauss(8500, 3000), 2)
        elif claim_type == "pharmacy":
            base_amount = round(random.gauss(250, 150), 2)
        else:
            base_amount = round(random.gauss(350, 200), 2)
        base_amount = max(25.0, base_amount)

        fraud_flags = []

        if provider["provider_id"] in fraud_velocity_providers and random.random() < 0.5:
            event_ts = now - timedelta(minutes=random.randint(0, 60))
            fraud_flags.append("velocity_burst")
        else:
            event_ts = now - timedelta(minutes=random.randint(0, 1440))

        if random.random() < FRAUD_PATTERNS["amount_outlier"]:
            base_amount *= random.uniform(3.0, 8.0)
            fraud_flags.append("amount_outlier")

        if random.random() < FRAUD_PATTERNS["upcoding"]:
            proc_code = "99215"
            fraud_flags.append("upcoding")

        if random.random() < FRAUD_PATTERNS["geo_anomaly"]:
            lat += random.uniform(3, 8) * random.choice([-1, 1])
            lon += random.uniform(3, 8) * random.choice([-1, 1])
            fraud_flags.append("geo_anomaly")

        events.append({
            "event_id": str(uuid.uuid4()),
            "event_timestamp": event_ts.isoformat(),
            "event_type": "CLAIM_SUBMITTED",
            "claim_id": f"CLM-{uuid.uuid4().hex[:10].upper()}",
            "patient_id": patient["patient_id"],
            "provider_id": provider["provider_id"],
            "facility_id": provider.get("facility_id", ""),
            "payer_id": payer["payer_id"],
            "diagnosis_code": diag["diagnosis_code"] if isinstance(diag, dict) else diag.get("diagnosis_code", "Z00.00"),
            "procedure_code": proc_code,
            "claim_type": claim_type,
            "claim_amount": round(base_amount, 2),
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "injected_fraud_flags": "|".join(fraud_flags) if fraud_flags else "",
        })

    return pd.DataFrame(events)


def generate_adt_events(n: int) -> pd.DataFrame:
    """Generate n ADT events for Care Gap Closure use case."""
    events = []
    now = datetime.utcnow()

    for i in range(n):
        patient = df_patients.sample(1).iloc[0]
        facility = df_facilities.sample(1).iloc[0]

        event_type = random.choices(ADT_EVENT_TYPES, weights=[0.35, 0.35, 0.15, 0.15], k=1)[0]
        admission_type = random.choices(ADMISSION_TYPES, weights=[0.30, 0.25, 0.35, 0.10], k=1)[0]

        diag = df_diagnoses.sample(1).iloc[0] if len(df_diagnoses) > 0 else {"diagnosis_code": "Z00.00", "diagnosis_description": "General exam"}

        lat = float(facility["latitude"]) if pd.notna(facility.get("latitude")) else 42.96
        lon = float(facility["longitude"]) if pd.notna(facility.get("longitude")) else -85.67

        patient_gaps = df_care_gaps[df_care_gaps["patient_id"] == patient["patient_id"]]
        has_open_gaps = len(patient_gaps) > 0
        open_gap_measures = "|".join(patient_gaps["measure_id"].tolist()) if has_open_gaps else ""

        events.append({
            "event_id": str(uuid.uuid4()),
            "event_timestamp": (now - timedelta(minutes=random.randint(0, 1440))).isoformat(),
            "event_type": event_type,
            "patient_id": patient["patient_id"],
            "facility_id": facility["facility_id"],
            "facility_name": facility.get("facility_name", ""),
            "admission_type": admission_type,
            "primary_diagnosis": diag["diagnosis_code"] if isinstance(diag, dict) else diag.get("diagnosis_code", "Z00.00"),
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "has_open_care_gaps": has_open_gaps,
            "open_gap_measures": open_gap_measures,
        })

    return pd.DataFrame(events)


def generate_rx_events(n: int) -> pd.DataFrame:
    """Generate n prescription fill events."""
    events = []
    now = datetime.utcnow()

    for i in range(n):
        patient = df_patients.sample(1).iloc[0]
        provider = df_providers.sample(1).iloc[0]
        med = df_medications.sample(1).iloc[0] if len(df_medications) > 0 else {"medication_code": "RX0001", "medication_name": "Generic Med", "drug_class": "Other"}

        fac = df_facilities[df_facilities["facility_id"] == provider["facility_id"]]
        lat = float(fac["latitude"].iloc[0]) if len(fac) > 0 and pd.notna(fac["latitude"].iloc[0]) else 42.96
        lon = float(fac["longitude"].iloc[0]) if len(fac) > 0 and pd.notna(fac["longitude"].iloc[0]) else -85.67

        events.append({
            "event_id": str(uuid.uuid4()),
            "event_timestamp": (now - timedelta(minutes=random.randint(0, 1440))).isoformat(),
            "event_type": "RX_FILL",
            "patient_id": patient["patient_id"],
            "provider_id": provider["provider_id"],
            "medication_code": med["medication_code"] if isinstance(med, dict) else med.get("medication_code", "RX0001"),
            "medication_name": med["medication_name"] if isinstance(med, dict) else med.get("medication_name", "Generic"),
            "drug_class": med.get("drug_class", "Other") if isinstance(med, dict) else "Other",
            "quantity": random.choice([30, 60, 90]),
            "days_supply": random.choice([30, 60, 90]),
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
        })

    return pd.DataFrame(events)

print("Event generators ready.")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# Stream Events — Eventstream primary path
# ============================================================================
# Eventstream: EventHub → Eventhouse + Lakehouse + Activator
# All routing is handled by the Eventstream topology (no direct KQL ingestion)
# ============================================================================

if not _es_producer:
    print("STOPPING: Eventstream is not available.")
    print("Set ES_CONNECTION_STRING and re-run this notebook.")
else:
    import time as _stream_time

    batch_num = 0
    max_batches = STREAM_BATCHES if STREAM_BATCHES > 0 else float("inf")
    print(f"Streaming {BATCH_SIZE} events/batch every {STREAM_INTERVAL_SEC}s...")
    print(f"  Eventstream → Eventhouse + Lakehouse + Activator")
    if STREAM_BATCHES > 0:
        print(f"  Batches: {STREAM_BATCHES} (then stop)")
    else:
        print(f"  Batches: infinite (Ctrl+C to stop)")

    try:
        while batch_num < max_batches:
            batch_num += 1

            claims_pdf = generate_claims_events(BATCH_SIZE)
            adt_pdf = generate_adt_events(BATCH_SIZE // 2)
            rx_pdf = generate_rx_events(BATCH_SIZE // 3)

            # Push to Eventstream (routes to all destinations)
            push_to_eventstream(claims_pdf, "claims_events")
            push_to_eventstream(adt_pdf, "adt_events")
            push_to_eventstream(rx_pdf, "rx_events")

            total = len(claims_pdf) + len(adt_pdf) + len(rx_pdf)
            print(f"  Batch {batch_num}: {total} events → Eventstream")

            if batch_num < max_batches:
                _stream_time.sleep(STREAM_INTERVAL_SEC)

    except KeyboardInterrupt:
        print(f"\nStreaming stopped by user after {batch_num} batches.")

    # Verify data landed in KQL (via Eventstream → Eventhouse routing)
    if _KUSTO_QUERY_URI:
        import time as _verify_time
        print("\nWaiting 10s for Eventstream → Eventhouse routing...")
        _verify_time.sleep(10)
        print("Verifying KQL table counts:")
        for _tbl in ["rti_all_events", "claims_events", "adt_events", "rx_events"]:
            _rows = _kql_query(f"{_tbl} | count")
            _cnt = _rows[0][0] if _rows else 0
            print(f"  {_tbl}: {_cnt} rows")

    print(f"\nStreaming complete — {batch_num} batches pushed via Eventstream.")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ---------- Summary ----------
print("\n" + "=" * 60)
print("NB_RTI_Event_Simulator: COMPLETE")
print("=" * 60)
print()
print("Ingestion path:")
if _es_producer:
    print("  ✓ Eventstream → Eventhouse + Lakehouse + Activator")
    _es_producer.close()
else:
    print("  ✗ Eventstream (no connection string)")
print()
print("Fraud pattern injection rates:")
for k, v in FRAUD_PATTERNS.items():
    print(f"  - {k}: {v*100:.0f}%")
print()
print("Re-run this notebook anytime to generate more streaming events.")
print("=" * 60)

# METADATA **{"language":"python"}**
