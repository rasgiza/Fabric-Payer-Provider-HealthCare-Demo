# Fabric notebook source

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# # RTI Use Case 3: High-Cost Member Trajectory
# 
# Identifies members on an **escalating cost trajectory** before they become
# catastrophic spenders. Uses rolling windows over claims and ED visits to flag:
# - **Rising spend** -- 30-day and 90-day rolling claim totals exceeding thresholds
# - **ED superutilizers** -- >=3 ED visits in 30 days
# - **Readmission risk** -- Multiple admits within 30 days
# - **Cost trend** -- Accelerating vs. stable vs. declining spend
# 
# **Industry pain point:** 5% of members drive 50% of healthcare costs. Early
# identification of members trending toward high-cost status enables care management
# intervention *before* an ICU admission or catastrophic event.
# 
# **Input:** `rti_claims_events` + `rti_adt_events` (Delta)
# **Output:** `rti_highcost_alerts` (Delta)
# 
# **Default lakehouse:** `lh_gold_curated`

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# NB_RTI_HighCost_Trajectory
# ============================================================================
# Rolling window analysis over claims and encounters to detect members
# on an escalating cost trajectory.
#
# Default lakehouse: lh_gold_curated
# ============================================================================

print("NB_RTI_HighCost_Trajectory: Starting...")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

%pip install azure-kusto-data azure-kusto-ingest azure-core>=1.31.0 --quiet

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

from pyspark.sql import functions as F
from pyspark.sql.window import Window

# ---------- Thresholds ----------
SPEND_30D_THRESHOLD = 15000    # Flag if 30-day rolling spend exceeds this
SPEND_90D_THRESHOLD = 40000    # Flag if 90-day rolling spend exceeds this
ED_VISITS_30D_THRESHOLD = 3    # Flag if >=3 ED visits in 30 days
READMIT_WINDOW_DAYS = 30       # Readmission = re-admit within this many days

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ---------- Load events ----------
print("Loading claims and ADT events...")

df_claims = spark.table("lh_gold_curated.rti_claims_events")
df_adt = spark.table("lh_gold_curated.rti_adt_events")
df_patients = spark.sql("""
    SELECT patient_id, first_name, last_name, date_of_birth, zip_code
    FROM lh_gold_curated.dim_patient WHERE is_current = true
""")
df_facilities = spark.sql("SELECT facility_id, facility_name, latitude, longitude FROM lh_gold_curated.dim_facility")

print(f"  Claims events: {df_claims.count()}")
print(f"  ADT events: {df_adt.count()}")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# Step 1: Rolling Spend by Patient
# ============================================================================
print("Computing rolling spend windows...")

# Parse timestamps and compute per-patient rolling totals
df_claims_ts = df_claims.withColumn(
    "event_ts", F.to_timestamp("event_timestamp")
).withColumn(
    "event_epoch", F.col("event_ts").cast("long")
)

# 30-day window = 30 * 86400 seconds
WINDOW_30D = 30 * 86400
WINDOW_90D = 90 * 86400

window_30d = (
    Window.partitionBy("patient_id")
    .orderBy("event_epoch")
    .rangeBetween(-WINDOW_30D, 0)
)
window_90d = (
    Window.partitionBy("patient_id")
    .orderBy("event_epoch")
    .rangeBetween(-WINDOW_90D, 0)
)

df_rolling = df_claims_ts.withColumn(
    "rolling_spend_30d", F.round(F.sum("claim_amount").over(window_30d), 2)
).withColumn(
    "rolling_spend_90d", F.round(F.sum("claim_amount").over(window_90d), 2)
).withColumn(
    "claims_count_30d", F.count("claim_id").over(window_30d)
)

print("  Rolling spend windows computed.")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# Step 2: ED Visit Counting
# ============================================================================
print("Counting ED visits per patient...")

# Filter ADT to emergency admissions
df_ed = df_adt.filter(
    F.col("admission_type") == "EMERGENCY"
).withColumn(
    "event_ts", F.to_timestamp("event_timestamp")
).withColumn(
    "event_epoch", F.col("event_ts").cast("long")
)

# Count ED visits per patient in 30-day window
ed_window_30d = (
    Window.partitionBy("patient_id")
    .orderBy("event_epoch")
    .rangeBetween(-WINDOW_30D, 0)
)

df_ed_counts = df_ed.withColumn(
    "ed_visits_30d", F.count("event_id").over(ed_window_30d)
).select(
    "patient_id",
    F.col("event_ts").alias("ed_event_ts"),
    "ed_visits_30d",
    "facility_id"
).dropDuplicates(["patient_id"])  # Keep latest ED count per patient

print(f"  ED events processed: {df_ed.count()}")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# Step 3: Readmission Detection
# ============================================================================
print("Detecting readmissions...")

df_admits = df_adt.filter(
    F.col("event_type") == "ADMIT"
).withColumn(
    "admit_ts", F.to_timestamp("event_timestamp")
).select(
    "patient_id",
    "admit_ts",
    "facility_id"
).orderBy("patient_id", "admit_ts")

# Compute days since previous admission
admit_window = Window.partitionBy("patient_id").orderBy("admit_ts")

df_readmit = df_admits.withColumn(
    "prev_admit_ts", F.lag("admit_ts").over(admit_window)
).withColumn(
    "days_since_last_admit",
    F.datediff(F.col("admit_ts"), F.col("prev_admit_ts"))
).withColumn(
    "is_readmission",
    F.when(
        F.col("days_since_last_admit").isNotNull() &
        (F.col("days_since_last_admit") <= READMIT_WINDOW_DAYS),
        True
    ).otherwise(False)
)

# Count readmissions per patient
df_readmit_counts = df_readmit.groupBy("patient_id").agg(
    F.sum(F.when(F.col("is_readmission"), 1).otherwise(0)).alias("readmission_count_30d")
)

print(f"  Admits analyzed: {df_admits.count()}")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# Step 4: Combine Signals and Score
# ============================================================================
print("Combining cost trajectory signals...")

# Get the latest rolling spend per patient
df_latest_spend = (
    df_rolling
    .withColumn("rn", F.row_number().over(
        Window.partitionBy("patient_id").orderBy(F.col("event_epoch").desc())
    ))
    .filter(F.col("rn") == 1)
    .select(
        "patient_id",
        "rolling_spend_30d",
        "rolling_spend_90d",
        "claims_count_30d",
        "latitude",
        "longitude",
    )
)

# Join all signals
df_combined = (
    df_latest_spend
    .join(df_ed_counts.select("patient_id", "ed_visits_30d"), "patient_id", "left")
    .join(df_readmit_counts, "patient_id", "left")
    .join(df_patients, "patient_id", "left")
)

# Fill nulls
df_combined = df_combined.fillna({
    "ed_visits_30d": 0,
    "readmission_count_30d": 0,
    "rolling_spend_30d": 0,
    "rolling_spend_90d": 0,
})

# Cost trend: compare 30-day rate to 90-day rate
df_combined = df_combined.withColumn(
    "monthly_rate_30d", F.col("rolling_spend_30d")
).withColumn(
    "monthly_rate_90d", F.col("rolling_spend_90d") / 3
).withColumn(
    "cost_trend",
    F.when(F.col("monthly_rate_30d") > F.col("monthly_rate_90d") * 1.5, "ACCELERATING")
    .when(F.col("monthly_rate_30d") > F.col("monthly_rate_90d") * 1.1, "RISING")
    .when(F.col("monthly_rate_30d") < F.col("monthly_rate_90d") * 0.8, "DECLINING")
    .otherwise("STABLE")
)

# Risk tier
df_combined = df_combined.withColumn(
    "risk_tier",
    F.when(
        (F.col("rolling_spend_30d") >= SPEND_30D_THRESHOLD) &
        (F.col("ed_visits_30d") >= ED_VISITS_30D_THRESHOLD),
        "CRITICAL"
    )
    .when(
        (F.col("rolling_spend_30d") >= SPEND_30D_THRESHOLD) |
        (F.col("rolling_spend_90d") >= SPEND_90D_THRESHOLD),
        "HIGH"
    )
    .when(
        (F.col("ed_visits_30d") >= ED_VISITS_30D_THRESHOLD) |
        (F.col("readmission_count_30d") > 0) |
        (F.col("cost_trend") == "ACCELERATING"),
        "MEDIUM"
    )
    .otherwise("LOW")
)

# Readmission flag
df_combined = df_combined.withColumn(
    "readmission_flag",
    F.col("readmission_count_30d") > 0
)

# Final output
df_output = df_combined.select(
    F.expr("uuid()").alias("alert_id"),
    F.current_timestamp().alias("alert_timestamp"),
    "patient_id",
    F.col("first_name").alias("patient_first_name"),
    F.col("last_name").alias("patient_last_name"),
    "rolling_spend_30d",
    "rolling_spend_90d",
    "claims_count_30d",
    "ed_visits_30d",
    "readmission_count_30d",
    "readmission_flag",
    "risk_tier",
    "cost_trend",
    "latitude",
    "longitude",
)

df_output.write.format("delta").mode("overwrite").saveAsTable("lh_gold_curated.rti_highcost_alerts")
alert_count = df_output.count()
print(f"High-cost trajectory alerts written: {alert_count}")


# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# Push High-Cost Alerts to KQL (direct Kusto ingestion)
# ============================================================================
print("Pushing high-cost alerts to KQL...")

import requests as _requests
import json as _json

_BASE_URL = "https://api.fabric.microsoft.com/v1"
_WORKSPACE_ID = notebookutils.runtime.context.get("currentWorkspaceId", "")
_KQL_DB_NAME = "Healthcare_RTI_DB"

def _get_fabric_token():
    return notebookutils.credentials.getToken("https://analysis.windows.net/powerbi/api")

def _get_kusto_token():
    return notebookutils.credentials.getToken("kusto")

_KUSTO_QUERY_URI = ""
_KUSTO_INGEST_URI = ""
_headers = {"Authorization": f"Bearer {_get_fabric_token()}", "Content-Type": "application/json"}
_resp = _requests.get(f"{_BASE_URL}/workspaces/{_WORKSPACE_ID}/items?type=Eventhouse", headers=_headers)
if _resp.status_code == 200:
    for _item in _resp.json().get("value", []):
        if "Healthcare" in _item.get("displayName", ""):
            _props_resp = _requests.get(
                f"{_BASE_URL}/workspaces/{_WORKSPACE_ID}/eventhouses/{_item['id']}",
                headers=_headers
            )
            if _props_resp.status_code == 200:
                _props = _props_resp.json().get("properties", _props_resp.json())
                _KUSTO_QUERY_URI = _props.get("queryServiceUri", "")
                _KUSTO_INGEST_URI = _props.get("ingestionServiceUri", "")
                if not _KUSTO_INGEST_URI and _KUSTO_QUERY_URI:
                    _KUSTO_INGEST_URI = _KUSTO_QUERY_URI.replace("https://", "https://ingest-")
            break

if _KUSTO_QUERY_URI and _KUSTO_INGEST_URI:
    try:
        from azure.kusto.ingest import ManagedStreamingIngestClient, IngestionProperties
        from azure.kusto.data import KustoConnectionStringBuilder, KustoClient, DataFormat
        import io

        _df_kql = df_output.select(
            "alert_id", "alert_timestamp", "patient_id",
            "rolling_spend_30d", "rolling_spend_90d", "ed_visits_30d",
            "readmission_flag", "risk_tier", "cost_trend",
            "latitude", "longitude"
        ).toPandas()

        _token = _get_kusto_token()
        _engine_kcsb = KustoConnectionStringBuilder.with_aad_user_token_authentication(_KUSTO_QUERY_URI, _token)
        _dm_kcsb = KustoConnectionStringBuilder.with_aad_user_token_authentication(_KUSTO_INGEST_URI, _token)

        # Ensure table, streaming policy, and mapping exist before ingesting
        _mgmt_client = KustoClient(_engine_kcsb)
        _mgmt_cmds = [
            """.create-merge table highcost_alerts (alert_id:string,alert_timestamp:datetime,patient_id:string,rolling_spend_30d:real,rolling_spend_90d:real,ed_visits_30d:int,readmission_flag:bool,risk_tier:string,cost_trend:string,latitude:real,longitude:real)""",
            """.alter table highcost_alerts policy streamingingestion enable""",
            """.create-or-alter table highcost_alerts ingestion json mapping 'highcost_alerts_mapping' '[{"column":"alert_id","path":"$.alert_id","datatype":"string"},{"column":"alert_timestamp","path":"$.alert_timestamp","datatype":"datetime"},{"column":"patient_id","path":"$.patient_id","datatype":"string"},{"column":"rolling_spend_30d","path":"$.rolling_spend_30d","datatype":"real"},{"column":"rolling_spend_90d","path":"$.rolling_spend_90d","datatype":"real"},{"column":"ed_visits_30d","path":"$.ed_visits_30d","datatype":"int"},{"column":"readmission_flag","path":"$.readmission_flag","datatype":"bool"},{"column":"risk_tier","path":"$.risk_tier","datatype":"string"},{"column":"cost_trend","path":"$.cost_trend","datatype":"string"},{"column":"latitude","path":"$.latitude","datatype":"real"},{"column":"longitude","path":"$.longitude","datatype":"real"}]'""",
        ]
        for _cmd in _mgmt_cmds:
            try:
                _mgmt_client.execute_mgmt(_KQL_DB_NAME, _cmd.strip())
            except Exception as _me:
                print(f"  KQL WARN: mgmt command failed (non-fatal): {_me}")

        # Wait for table/mapping propagation across Kusto cluster nodes
        import time as _time_kql
        _time_kql.sleep(10)

        _client = ManagedStreamingIngestClient(_engine_kcsb, _dm_kcsb)
        _ingestion_props = IngestionProperties(
            database=_KQL_DB_NAME, table="highcost_alerts",
            data_format=DataFormat.JSON, ingestion_mapping_reference="highcost_alerts_mapping"
        )
        _json_data = _df_kql.to_json(orient="records", lines=True, date_format="iso")
        _client.ingest_from_stream(io.StringIO(_json_data), ingestion_properties=_ingestion_props)
        print(f"  KQL: {len(_df_kql)} high-cost alerts streamed -> highcost_alerts")
    except Exception as e:
        print(f"  KQL WARN: highcost_alerts ingestion failed: {e}")
else:
    print("  KQL: Eventhouse not found -- skipping KQL ingestion (Delta table still written)")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# Summary Statistics
# ============================================================================

df_summary = spark.sql("""
    SELECT
        risk_tier,
        COUNT(*) as patients,
        ROUND(AVG(rolling_spend_30d), 0) as avg_spend_30d,
        ROUND(AVG(rolling_spend_90d), 0) as avg_spend_90d,
        ROUND(AVG(ed_visits_30d), 1) as avg_ed_visits,
        SUM(CASE WHEN readmission_flag THEN 1 ELSE 0 END) as readmissions
    FROM lh_gold_curated.rti_highcost_alerts
    GROUP BY risk_tier
    ORDER BY
        CASE risk_tier
            WHEN 'CRITICAL' THEN 1
            WHEN 'HIGH' THEN 2
            WHEN 'MEDIUM' THEN 3
            ELSE 4
        END
""")

print("\n" + "=" * 60)
print("HIGH-COST MEMBER TRAJECTORY RESULTS")
print("=" * 60)
df_summary.show(truncate=False)

# Cost trend distribution
df_trend = spark.sql("""
    SELECT
        cost_trend,
        COUNT(*) as members,
        ROUND(AVG(rolling_spend_30d), 0) as avg_30d_spend,
        ROUND(AVG(ed_visits_30d), 1) as avg_ed_visits
    FROM lh_gold_curated.rti_highcost_alerts
    GROUP BY cost_trend
    ORDER BY
        CASE cost_trend
            WHEN 'ACCELERATING' THEN 1
            WHEN 'RISING' THEN 2
            WHEN 'STABLE' THEN 3
            ELSE 4
        END
""")

print("Cost Trend Distribution:")
df_trend.show(truncate=False)

# Top high-cost members for care management outreach
df_top = spark.sql("""
    SELECT
        patient_id,
        patient_first_name,
        patient_last_name,
        risk_tier,
        cost_trend,
        rolling_spend_30d,
        rolling_spend_90d,
        ed_visits_30d,
        readmission_flag
    FROM lh_gold_curated.rti_highcost_alerts
    WHERE risk_tier IN ('CRITICAL', 'HIGH')
    ORDER BY rolling_spend_30d DESC
    LIMIT 15
""")

print("Top 15 High-Cost Members (Care Management Priority):")
df_top.show(truncate=False)

print("\nNB_RTI_HighCost_Trajectory: COMPLETE")
print("=" * 60)

# METADATA **{"language":"python"}**
