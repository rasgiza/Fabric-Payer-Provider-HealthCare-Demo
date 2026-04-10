# Fabric notebook source

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# # RTI Event Simulator -- Streaming Healthcare Events
# 
# Generates realistic real-time events for **3 RTI use cases**:
# 1. **Claims Fraud Detection** -- Claims submissions with amounts, diagnoses, geo
# 2. **Care Gap Closure** -- ADT admit/discharge events triggering gap checks
# 3. **High-Cost Member Trajectory** -- Claims + ED visits for rolling cost analysis
# 
# **Modes:**
# - `batch` -- Generate one batch, save as Delta tables + push to KQL (used by launcher)
# - `stream` -- Continuously push events to KQL in a loop (for live demos)
# 
# **Ingestion:** Direct Kusto (`azure-kusto-ingest`, pre-installed in Fabric)
# - Zero config: token from `notebookutils.credentials.getToken("kusto")`
# - No Eventstream, connection strings, or manual portal steps
# 
# > **Note:** This demo uses direct Kusto ingestion because it can be deployed entirely
# > programmatically with no manual portal steps. In a production environment, events would
# > flow from **Eventstream Custom Endpoints**, **IoT Hub** (medical devices / wearables),
# > or **Azure Event Hub** into the same KQL tables. The scoring notebooks and KQL dashboards
# > work identically regardless of the ingestion source.
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
# Pushes to KQL via direct Kusto ingestion (zero config).
# Default lakehouse: lh_gold_curated
# ============================================================================

print("NB_RTI_Event_Simulator: Starting...")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

%pip install azure-kusto-data azure-kusto-ingest azure-core>=1.31.0 --quiet

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ---------- Parameters (override from pipeline or %run) ----------
MODE = "batch"           # "batch" = single batch to Delta + KQL | "stream" = continuous to KQL
BATCH_SIZE = 500         # events per batch
STREAM_INTERVAL_SEC = 5  # seconds between stream batches
STREAM_BATCHES = 10      # number of batches in stream mode (0 = infinite)

# Kusto config -- auto-discovered from NB_RTI_Setup_Eventhouse output
KUSTO_QUERY_URI = ""     # Auto-detected from Eventhouse API if blank
KUSTO_INGEST_URI = ""    # Auto-detected from Eventhouse API if blank
KQL_DB_NAME = "Healthcare_RTI_DB"

# METADATA **{"language":"python"}**

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

# ---------- Auto-discover Kusto ingestion URI ----------
print("Discovering Kusto ingestion URI...")

BASE_URL = "https://api.fabric.microsoft.com/v1"

def get_fabric_token():
    return notebookutils.credentials.getToken("https://analysis.windows.net/powerbi/api")

def get_kusto_token():
    return notebookutils.credentials.getToken("kusto")

WORKSPACE_ID = notebookutils.runtime.context.get("currentWorkspaceId", "")

if not KUSTO_INGEST_URI:
    # Discover Eventhouse and get both query + ingestion URIs
    headers = {"Authorization": f"Bearer {get_fabric_token()}", "Content-Type": "application/json"}
    items_url = f"{BASE_URL}/workspaces/{WORKSPACE_ID}/items?type=Eventhouse"
    resp = requests.get(items_url, headers=headers)
    if resp.status_code == 200:
        for item in resp.json().get("value", []):
            if "Healthcare" in item.get("displayName", ""):
                eh_id = item["id"]
                props_resp = requests.get(
                    f"{BASE_URL}/workspaces/{WORKSPACE_ID}/eventhouses/{eh_id}",
                    headers=headers
                )
                if props_resp.status_code == 200:
                    props = props_resp.json().get("properties", props_resp.json())
                    KUSTO_QUERY_URI = props.get("queryServiceUri", "")
                    KUSTO_INGEST_URI = props.get("ingestionServiceUri", "")
                    if not KUSTO_INGEST_URI and KUSTO_QUERY_URI:
                        KUSTO_INGEST_URI = KUSTO_QUERY_URI.replace("https://", "https://ingest-")
                    print(f"  Eventhouse: {item['displayName']}")
                    break

if KUSTO_QUERY_URI and KUSTO_INGEST_URI:
    print(f"  Query URI:     {KUSTO_QUERY_URI}")
    print(f"  Ingestion URI: {KUSTO_INGEST_URI}")
else:
    print("  WARN: Could not discover Kusto URIs -- KQL ingestion will be skipped")
    print("  Delta tables will still be written to lh_gold_curated")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ---------- Kusto Managed Streaming Ingestion ----------
# Per Microsoft best practice: ManagedStreamingIngestClient tries streaming
# first (seconds latency), falls back to queued ingestion automatically
# if the payload exceeds 10 MB or on transient failures (3 retries).
# Ref: https://learn.microsoft.com/en-us/kusto/api/get-started/app-managed-streaming-ingest

from azure.kusto.ingest import ManagedStreamingIngestClient, IngestionProperties
from azure.kusto.data import KustoConnectionStringBuilder, KustoClient, DataFormat
import io

_kusto_client = None  # Reuse client across calls
_ensured_tables = set()  # Track which tables have been ensured

# Table schemas and mappings for self-healing creation
_TABLE_SCHEMAS = {
    "claims_events": {
        "create": ".create-merge table claims_events (event_id:string,event_timestamp:datetime,event_type:string,claim_id:string,patient_id:string,provider_id:string,facility_id:string,payer_id:string,diagnosis_code:string,procedure_code:string,claim_type:string,claim_amount:real,latitude:real,longitude:real,injected_fraud_flags:string)",
        "mapping": """.create-or-alter table claims_events ingestion json mapping 'claims_events_mapping' '[{"column":"event_id","path":"$.event_id","datatype":"string"},{"column":"event_timestamp","path":"$.event_timestamp","datatype":"datetime"},{"column":"event_type","path":"$.event_type","datatype":"string"},{"column":"claim_id","path":"$.claim_id","datatype":"string"},{"column":"patient_id","path":"$.patient_id","datatype":"string"},{"column":"provider_id","path":"$.provider_id","datatype":"string"},{"column":"facility_id","path":"$.facility_id","datatype":"string"},{"column":"payer_id","path":"$.payer_id","datatype":"string"},{"column":"diagnosis_code","path":"$.diagnosis_code","datatype":"string"},{"column":"procedure_code","path":"$.procedure_code","datatype":"string"},{"column":"claim_type","path":"$.claim_type","datatype":"string"},{"column":"claim_amount","path":"$.claim_amount","datatype":"real"},{"column":"latitude","path":"$.latitude","datatype":"real"},{"column":"longitude","path":"$.longitude","datatype":"real"},{"column":"injected_fraud_flags","path":"$.injected_fraud_flags","datatype":"string"}]'""",
    },
    "adt_events": {
        "create": ".create-merge table adt_events (event_id:string,event_timestamp:datetime,event_type:string,patient_id:string,facility_id:string,facility_name:string,admission_type:string,primary_diagnosis:string,latitude:real,longitude:real,has_open_care_gaps:bool,open_gap_measures:string)",
        "mapping": """.create-or-alter table adt_events ingestion json mapping 'adt_events_mapping' '[{"column":"event_id","path":"$.event_id","datatype":"string"},{"column":"event_timestamp","path":"$.event_timestamp","datatype":"datetime"},{"column":"event_type","path":"$.event_type","datatype":"string"},{"column":"patient_id","path":"$.patient_id","datatype":"string"},{"column":"facility_id","path":"$.facility_id","datatype":"string"},{"column":"facility_name","path":"$.facility_name","datatype":"string"},{"column":"admission_type","path":"$.admission_type","datatype":"string"},{"column":"primary_diagnosis","path":"$.primary_diagnosis","datatype":"string"},{"column":"latitude","path":"$.latitude","datatype":"real"},{"column":"longitude","path":"$.longitude","datatype":"real"},{"column":"has_open_care_gaps","path":"$.has_open_care_gaps","datatype":"bool"},{"column":"open_gap_measures","path":"$.open_gap_measures","datatype":"string"}]'""",
    },
    "rx_events": {
        "create": ".create-merge table rx_events (event_id:string,event_timestamp:datetime,event_type:string,patient_id:string,provider_id:string,medication_code:string,medication_name:string,drug_class:string,quantity:int,days_supply:int,latitude:real,longitude:real)",
        "mapping": """.create-or-alter table rx_events ingestion json mapping 'rx_events_mapping' '[{"column":"event_id","path":"$.event_id","datatype":"string"},{"column":"event_timestamp","path":"$.event_timestamp","datatype":"datetime"},{"column":"event_type","path":"$.event_type","datatype":"string"},{"column":"patient_id","path":"$.patient_id","datatype":"string"},{"column":"provider_id","path":"$.provider_id","datatype":"string"},{"column":"medication_code","path":"$.medication_code","datatype":"string"},{"column":"medication_name","path":"$.medication_name","datatype":"string"},{"column":"drug_class","path":"$.drug_class","datatype":"string"},{"column":"quantity","path":"$.quantity","datatype":"int"},{"column":"days_supply","path":"$.days_supply","datatype":"int"},{"column":"latitude","path":"$.latitude","datatype":"real"},{"column":"longitude","path":"$.longitude","datatype":"real"}]'""",
    },
}

def _get_or_create_kusto_client():
    """Create (or refresh) the ManagedStreamingIngestClient."""
    global _kusto_client
    if _kusto_client is None:
        token = get_kusto_token()
        engine_kcsb = KustoConnectionStringBuilder.with_aad_user_token_authentication(
            KUSTO_QUERY_URI, token
        )
        dm_kcsb = KustoConnectionStringBuilder.with_aad_user_token_authentication(
            KUSTO_INGEST_URI, token
        )
        _kusto_client = ManagedStreamingIngestClient(engine_kcsb, dm_kcsb)
    return _kusto_client

def _ensure_table_and_mapping(table_name):
    """Ensure the KQL table, streaming policy, and mapping exist (idempotent)."""
    if table_name in _ensured_tables or table_name not in _TABLE_SCHEMAS:
        return
    try:
        token = get_kusto_token()
        kcsb = KustoConnectionStringBuilder.with_aad_user_token_authentication(KUSTO_QUERY_URI, token)
        mgmt = KustoClient(kcsb)
        schema = _TABLE_SCHEMAS[table_name]
        for cmd in [schema["create"], f".alter table {table_name} policy streamingingestion enable", schema["mapping"]]:
            try:
                mgmt.execute_mgmt(KQL_DB_NAME, cmd.strip())
            except Exception:
                pass
        _ensured_tables.add(table_name)
    except Exception as e:
        print(f"  KQL WARN: ensure table {table_name} failed (non-fatal): {e}")

def push_to_kql(df_pandas, table_name, mapping_name):
    """Push a pandas DataFrame to a KQL table via managed streaming ingestion."""
    if not KUSTO_QUERY_URI or not KUSTO_INGEST_URI:
        return False
    try:
        _ensure_table_and_mapping(table_name)
        client = _get_or_create_kusto_client()

        ingestion_props = IngestionProperties(
            database=KQL_DB_NAME,
            table=table_name,
            data_format=DataFormat.JSON,
            ingestion_mapping_reference=mapping_name,
        )

        # Convert DataFrame to JSON lines
        json_data = df_pandas.to_json(orient="records", lines=True, date_format="iso")
        stream = io.StringIO(json_data)

        client.ingest_from_stream(stream, ingestion_properties=ingestion_props)
        print(f"  KQL: {len(df_pandas)} rows streamed -> {table_name}")
        return True
    except Exception as e:
        print(f"  KQL WARN: {table_name} ingestion failed: {e}")
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
# Batch Mode -- Generate one batch, save as Delta tables + push to KQL
# ============================================================================
if MODE == "batch":
    print(f"Generating batch: {BATCH_SIZE} claims, {BATCH_SIZE // 2} ADT, {BATCH_SIZE // 3} Rx events...")

    claims_pdf = generate_claims_events(BATCH_SIZE)
    adt_pdf = generate_adt_events(BATCH_SIZE // 2)
    rx_pdf = generate_rx_events(BATCH_SIZE // 3)

    # Write to Delta tables in lakehouse
    claims_sdf = spark.createDataFrame(claims_pdf)
    adt_sdf = spark.createDataFrame(adt_pdf)
    rx_sdf = spark.createDataFrame(rx_pdf)

    claims_sdf.write.format("delta").mode("overwrite").saveAsTable("lh_gold_curated.rti_claims_events")
    adt_sdf.write.format("delta").mode("overwrite").saveAsTable("lh_gold_curated.rti_adt_events")
    rx_sdf.write.format("delta").mode("overwrite").saveAsTable("lh_gold_curated.rti_rx_events")

    print(f"  Delta: rti_claims_events ({len(claims_pdf)}), rti_adt_events ({len(adt_pdf)}), rti_rx_events ({len(rx_pdf)})")

    # Push to KQL for real-time dashboard/alerting
    push_to_kql(claims_pdf, "claims_events", "claims_events_mapping")
    push_to_kql(adt_pdf, "adt_events", "adt_events_mapping")
    push_to_kql(rx_pdf, "rx_events", "rx_events_mapping")

    print("Batch mode complete -- Delta tables + KQL ingestion done.")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# Stream Mode -- Continuously push events via direct Kusto ingestion
# ============================================================================
if MODE == "stream":
    if not KUSTO_INGEST_URI:
        raise ValueError(
            "Could not discover Kusto ingestion URI.\n"
            "Ensure NB_RTI_Setup_Eventhouse ran successfully and the Eventhouse exists."
        )

    import time

    batch_num = 0
    max_batches = STREAM_BATCHES if STREAM_BATCHES > 0 else float("inf")
    print(f"Streaming events every {STREAM_INTERVAL_SEC}s via direct Kusto ingestion...")
    if STREAM_BATCHES > 0:
        print(f"  Will stop after {STREAM_BATCHES} batches")

    try:
        while batch_num < max_batches:
            batch_num += 1

            claims_pdf = generate_claims_events(BATCH_SIZE)
            adt_pdf = generate_adt_events(BATCH_SIZE // 2)
            rx_pdf = generate_rx_events(BATCH_SIZE // 3)

            # Push to KQL
            push_to_kql(claims_pdf, "claims_events", "claims_events_mapping")
            push_to_kql(adt_pdf, "adt_events", "adt_events_mapping")
            push_to_kql(rx_pdf, "rx_events", "rx_events_mapping")

            # Also append to Delta for historical tracking
            spark.createDataFrame(claims_pdf).write.format("delta").mode("append").saveAsTable("lh_gold_curated.rti_claims_events")
            spark.createDataFrame(adt_pdf).write.format("delta").mode("append").saveAsTable("lh_gold_curated.rti_adt_events")
            spark.createDataFrame(rx_pdf).write.format("delta").mode("append").saveAsTable("lh_gold_curated.rti_rx_events")

            total = len(claims_pdf) + len(adt_pdf) + len(rx_pdf)
            print(f"  Batch {batch_num}: {total} events -> KQL + Delta")

            if batch_num < max_batches:
                time.sleep(STREAM_INTERVAL_SEC)

    except KeyboardInterrupt:
        print(f"Streaming stopped after {batch_num} batches.")

    print(f"Stream mode complete -- {batch_num} batches pushed to KQL + Delta.")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ---------- Summary ----------
print("\n" + "=" * 60)
print("NB_RTI_Event_Simulator: COMPLETE")
print("=" * 60)
if MODE == "batch":
    print("Tables written to lh_gold_curated + KQL:")
    print("  - rti_claims_events / claims_events  (claims + injected fraud patterns)")
    print("  - rti_adt_events / adt_events         (ADT + open care gap flags)")
    print("  - rti_rx_events / rx_events           (prescription fills)")
    print()
    print("Fraud pattern injection rates:")
    for k, v in FRAUD_PATTERNS.items():
        print(f"  - {k}: {v*100:.0f}%")
elif MODE == "stream":
    print("Events streamed to KQL via direct Kusto ingestion")
    print("Delta tables also updated for batch analysis")
print()
print("Ingestion method: Managed Streaming (azure-kusto-ingest)")
print("  Tries streaming first (seconds latency), falls back to queued")
print("  No Eventstream or connection strings needed")
print("=" * 60)

# METADATA **{"language":"python"}**
