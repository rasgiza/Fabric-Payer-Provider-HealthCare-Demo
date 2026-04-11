# Fabric notebook source

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# # RTI Use Case 1: Claims Fraud Detection
# 
# Real-time scoring of claims events to detect potential fraud patterns:
# - **Velocity bursts** -- Provider submits many claims in a short window
# - **Geographic anomaly** -- Patient location far from provider facility
# - **Amount outliers** -- Claim amount exceeds 3σ of provider's historical mean
# - **Upcoding** -- Consistent use of highest E&M codes
# - **Diagnosis pattern** -- Unusual diagnosis combinations for specialty
# 
# **Input:** `rti_claims_events` (Delta) or `claims_events` (KQL)
# **Output:** `rti_fraud_scores` (Delta) + `fraud_scores` (KQL)
# 
# **Default lakehouse:** `lh_gold_curated`

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# NB_RTI_Fraud_Detection
# ============================================================================
# Scores claims events for fraud risk using rule-based + statistical methods.
# Reads from rti_claims_events (Delta), enriches with provider history,
# writes scored results to rti_fraud_scores.
#
# Default lakehouse: lh_gold_curated
# ============================================================================

print("NB_RTI_Fraud_Detection: Starting...")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

%pip install azure-kusto-data azure-kusto-ingest azure-core>=1.31.0 --quiet

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.sql.types import DoubleType, StringType, ArrayType
import math

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ---------- Load events and reference data ----------
print("Loading claims events and reference data...")

df_claims = spark.table("lh_gold_curated.rti_claims_events")
df_providers = spark.sql("""
    SELECT provider_id, display_name AS provider_name, specialty
    FROM lh_gold_curated.dim_provider WHERE is_current = true
""")
df_facilities = spark.sql("SELECT facility_id, latitude as fac_lat, longitude as fac_lon FROM lh_gold_curated.dim_facility")

# Historical claim stats for baseline comparison
# fact_claim uses surrogate provider_key; join with dim_provider to get provider_id
df_historical = spark.sql("""
    SELECT p.provider_id,
           AVG(c.billed_amount) as hist_avg_amount,
           STDDEV(c.billed_amount) as hist_std_amount,
           COUNT(*) as hist_claim_count
    FROM lh_gold_curated.fact_claim c
    JOIN lh_gold_curated.dim_provider p ON c.provider_key = p.provider_key
    GROUP BY p.provider_id
""")

print(f"  Claims events: {df_claims.count()}")
print(f"  Providers: {df_providers.count()}")
print(f"  Historical baselines: {df_historical.count()}")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# Fraud Scoring Rules
# ============================================================================

# Enrich claims with provider and facility data
df_enriched = (
    df_claims
    .join(df_providers, "provider_id", "left")
    .join(df_facilities, "facility_id", "left")
    .join(df_historical, "provider_id", "left")
)

# ---------- Rule 1: Velocity Burst ----------
# Count claims per provider within 1-hour windows
window_velocity = Window.partitionBy("provider_id").orderBy("event_timestamp").rangeBetween(-3600, 0)

df_scored = df_enriched.withColumn(
    "claims_in_window",
    F.count("claim_id").over(
        Window.partitionBy("provider_id")
        .orderBy(F.col("event_timestamp").cast("long"))
        .rangeBetween(-3600, 0)
    )
)

# Velocity score: 0 if ≤5 claims/hr, scales up to 30 points
df_scored = df_scored.withColumn(
    "velocity_score",
    F.when(F.col("claims_in_window") > 5,
           F.least(F.lit(30), (F.col("claims_in_window") - 5) * 6))
    .otherwise(0)
)

# ---------- Rule 2: Amount Outlier ----------
# Z-score of claim amount vs provider's historical mean
df_scored = df_scored.withColumn(
    "amount_zscore",
    F.when(
        (F.col("hist_std_amount").isNotNull()) & (F.col("hist_std_amount") > 0),
        (F.col("claim_amount") - F.col("hist_avg_amount")) / F.col("hist_std_amount")
    ).otherwise(0)
)

# Amount score: 0 if z ≤ 2, up to 25 points
df_scored = df_scored.withColumn(
    "amount_score",
    F.when(F.col("amount_zscore") > 2,
           F.least(F.lit(25), (F.col("amount_zscore") - 2) * 10))
    .otherwise(0)
)

# ---------- Rule 3: Geographic Anomaly ----------
# Haversine approximation between claim lat/lon and facility lat/lon
df_scored = df_scored.withColumn(
    "geo_distance_deg",
    F.sqrt(
        F.pow(F.col("latitude") - F.col("fac_lat"), 2) +
        F.pow(F.col("longitude") - F.col("fac_lon"), 2)
    )
)

# Geo score: 0 if <1 degree (~69 miles), up to 25 points
df_scored = df_scored.withColumn(
    "geo_score",
    F.when(F.col("geo_distance_deg") > 1,
           F.least(F.lit(25), F.col("geo_distance_deg") * 5))
    .otherwise(0)
)

# ---------- Rule 4: Upcoding ----------
# Flag if procedure_code is always highest E&M (99215)
df_scored = df_scored.withColumn(
    "upcoding_score",
    F.when(F.col("procedure_code") == "99215", F.lit(20)).otherwise(0)
)

print("Scoring rules applied.")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# Composite Score and Risk Tiers
# ============================================================================

df_scored = df_scored.withColumn(
    "fraud_score",
    F.round(
        F.col("velocity_score") + F.col("amount_score") +
        F.col("geo_score") + F.col("upcoding_score"),
        2
    )
)

# Assemble fraud flags
df_scored = df_scored.withColumn(
    "fraud_flags",
    F.concat_ws("|",
        F.when(F.col("velocity_score") > 0, F.lit("velocity_burst")),
        F.when(F.col("amount_score") > 0, F.lit("amount_outlier")),
        F.when(F.col("geo_score") > 0, F.lit("geo_anomaly")),
        F.when(F.col("upcoding_score") > 0, F.lit("upcoding")),
    )
)

# Risk tiers
df_scored = df_scored.withColumn(
    "risk_tier",
    F.when(F.col("fraud_score") >= 50, "CRITICAL")
    .when(F.col("fraud_score") >= 30, "HIGH")
    .when(F.col("fraud_score") >= 15, "MEDIUM")
    .otherwise("LOW")
)

# Select final output columns
df_output = df_scored.select(
    F.expr("uuid()").alias("score_id"),
    F.current_timestamp().alias("score_timestamp"),
    "claim_id",
    "patient_id",
    "provider_id",
    "facility_id",
    "claim_amount",
    "diagnosis_code",
    "procedure_code",
    "claim_type",
    "fraud_score",
    "fraud_flags",
    "risk_tier",
    "velocity_score",
    "amount_score",
    "geo_score",
    "upcoding_score",
    "claims_in_window",
    "amount_zscore",
    "geo_distance_deg",
    "latitude",
    "longitude",
)

# Write to Delta
df_output.write.format("delta").mode("overwrite").saveAsTable("lh_gold_curated.rti_fraud_scores")

print(f"Fraud scores written: {df_output.count()} claims scored")


# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# Push Fraud Scores to KQL (direct Kusto ingestion)
# ============================================================================
print("Pushing fraud scores to KQL...")

import requests, json

BASE_URL = "https://api.fabric.microsoft.com/v1"
WORKSPACE_ID = notebookutils.runtime.context.get("currentWorkspaceId", "")
KQL_DB_NAME = "Healthcare_RTI_DB"

def get_fabric_token():
    return notebookutils.credentials.getToken("https://analysis.windows.net/powerbi/api")

def get_kusto_token():
    return notebookutils.credentials.getToken("kusto")

# Auto-discover Kusto query + ingestion URIs
KUSTO_QUERY_URI = ""
KUSTO_INGEST_URI = ""
headers = {"Authorization": f"Bearer {get_fabric_token()}", "Content-Type": "application/json"}
resp = requests.get(f"{BASE_URL}/workspaces/{WORKSPACE_ID}/items?type=Eventhouse", headers=headers)
if resp.status_code == 200:
    for item in resp.json().get("value", []):
        if "Healthcare" in item.get("displayName", ""):
            props_resp = requests.get(
                f"{BASE_URL}/workspaces/{WORKSPACE_ID}/eventhouses/{item['id']}",
                headers=headers
            )
            if props_resp.status_code == 200:
                props = props_resp.json().get("properties", props_resp.json())
                KUSTO_QUERY_URI = props.get("queryServiceUri", "")
                KUSTO_INGEST_URI = props.get("ingestionServiceUri", "")
                if not KUSTO_INGEST_URI and KUSTO_QUERY_URI:
                    KUSTO_INGEST_URI = KUSTO_QUERY_URI.replace("https://", "https://ingest-")
            break

if KUSTO_QUERY_URI and KUSTO_INGEST_URI:
    try:
        from azure.kusto.ingest import ManagedStreamingIngestClient, IngestionProperties
        from azure.kusto.data import KustoConnectionStringBuilder, KustoClient, DataFormat
        import io

        # Select columns matching KQL fraud_scores schema
        df_kql = df_output.select(
            "score_id", "score_timestamp", "claim_id", "patient_id",
            "provider_id", "facility_id", "claim_amount", "fraud_score",
            "fraud_flags", "risk_tier", "latitude", "longitude"
        ).toPandas()

        token = get_kusto_token()
        engine_kcsb = KustoConnectionStringBuilder.with_aad_user_token_authentication(KUSTO_QUERY_URI, token)
        dm_kcsb = KustoConnectionStringBuilder.with_aad_user_token_authentication(KUSTO_INGEST_URI, token)

        # Ensure table, streaming policy, and mapping exist before ingesting
        _mgmt_client = KustoClient(engine_kcsb)
        _mgmt_cmds = [
            """.create-merge table fraud_scores (score_id:string,score_timestamp:datetime,claim_id:string,patient_id:string,provider_id:string,facility_id:string,claim_amount:real,fraud_score:real,fraud_flags:string,risk_tier:string,latitude:real,longitude:real)""",
            """.alter table fraud_scores policy streamingingestion enable""",
            """.create-or-alter table fraud_scores ingestion json mapping 'fraud_scores_mapping' '[{"column":"score_id","path":"$.score_id","datatype":"string"},{"column":"score_timestamp","path":"$.score_timestamp","datatype":"datetime"},{"column":"claim_id","path":"$.claim_id","datatype":"string"},{"column":"patient_id","path":"$.patient_id","datatype":"string"},{"column":"provider_id","path":"$.provider_id","datatype":"string"},{"column":"facility_id","path":"$.facility_id","datatype":"string"},{"column":"claim_amount","path":"$.claim_amount","datatype":"real"},{"column":"fraud_score","path":"$.fraud_score","datatype":"real"},{"column":"fraud_flags","path":"$.fraud_flags","datatype":"string"},{"column":"risk_tier","path":"$.risk_tier","datatype":"string"},{"column":"latitude","path":"$.latitude","datatype":"real"},{"column":"longitude","path":"$.longitude","datatype":"real"}]'""",
        ]
        for _cmd in _mgmt_cmds:
            try:
                _mgmt_client.execute_mgmt(KQL_DB_NAME, _cmd.strip())
            except Exception as _me:
                print(f"  KQL WARN: mgmt command failed (non-fatal): {_me}")

        # Wait for table/mapping propagation across Kusto cluster nodes
        import time as _time_kql
        _time_kql.sleep(10)

        client = ManagedStreamingIngestClient(engine_kcsb, dm_kcsb)
        ingestion_props = IngestionProperties(
            database=KQL_DB_NAME, table="fraud_scores",
            data_format=DataFormat.JSON, ingestion_mapping_reference="fraud_scores_mapping"
        )
        json_data = df_kql.to_json(orient="records", lines=True, date_format="iso")
        client.ingest_from_stream(io.StringIO(json_data), ingestion_properties=ingestion_props)
        print(f"  KQL: {len(df_kql)} fraud scores streamed -> fraud_scores")
    except Exception as e:
        print(f"  KQL WARN: fraud_scores ingestion failed: {e}")
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
        COUNT(*) as claim_count,
        ROUND(AVG(fraud_score), 1) as avg_score,
        ROUND(MAX(fraud_score), 1) as max_score,
        ROUND(SUM(claim_amount), 2) as total_amount
    FROM lh_gold_curated.rti_fraud_scores
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
print("FRAUD DETECTION RESULTS")
print("=" * 60)
df_summary.show(truncate=False)

# Top flagged providers
df_top_providers = spark.sql("""
    SELECT
        f.provider_id,
        p.display_name AS provider_name,
        p.specialty,
        COUNT(*) as flagged_claims,
        ROUND(AVG(f.fraud_score), 1) as avg_fraud_score,
        ROUND(SUM(f.claim_amount), 2) as total_flagged_amount
    FROM lh_gold_curated.rti_fraud_scores f
    LEFT JOIN lh_gold_curated.dim_provider p ON f.provider_id = p.provider_id AND p.is_current = true
    WHERE f.risk_tier IN ('CRITICAL', 'HIGH')
    GROUP BY f.provider_id, p.display_name, p.specialty
    ORDER BY avg_fraud_score DESC
    LIMIT 10
""")

print("Top 10 Flagged Providers:")
df_top_providers.show(truncate=False)

print("NB_RTI_Fraud_Detection: COMPLETE")
print("=" * 60)

# METADATA **{"language":"python"}**
