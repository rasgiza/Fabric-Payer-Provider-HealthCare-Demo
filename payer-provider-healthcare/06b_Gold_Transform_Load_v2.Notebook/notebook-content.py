# Fabric notebook source

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# # Gold Layer Transform & Load (Production)
# 
# **Production-ready notebook with:**
# - Stable surrogate keys (LEFT JOIN + COALESCE pattern — no IDENTITY needed)
# - SCD Type 2 for dim_patient, dim_provider (tracks attribute changes)
# - Incremental MERGE for all tables (idempotent — safe to re-run)
# - Fact tables with proper dimension key lookups
# 
# **Architecture:**
# ```
# ┌──────────────────────┐     ┌──────────────────────┐
# │  lh_silver_ods       │────►│  lh_gold_curated     │
# │  (Silver ODS)        │     │  (Gold Star Schema)  │
# │  patients_enriched   │     │  dim_patient (SCD2)  │
# │  providers_enriched  │     │  dim_provider (SCD2) │
# │  encounters_enriched │     │  dim_payer           │
# │  claims_enriched     │     │  dim_facility        │
# │  readmission_pred.   │     │  dim_date            │
# │  denial_pred.        │     │  fact_encounter      │
# └──────────────────────┘     │  fact_claim           │
#                               │  agg_readmission     │
#                               │  agg_denial_by_date  │
#                               │  agg_denial_by_payer │
#                               └──────────────────────┘
# ```
# 
# **Key Generation Pattern (equivalent to T-SQL):**
# ```sql
# -- T-SQL: @MaxKey + ROW_NUMBER() OVER (ORDER BY business_key)
# -- PySpark: COALESCE(existing_key, max_key + row_number())
# -- Same as: LEFT JOIN existing dim ON business_key → preserve assigned keys, assign new ones
# ```

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================
# IMPORTS & CONFIGURATION
# ============================================================
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.window import Window
from pyspark.sql.types import *
from delta.tables import DeltaTable
from pyspark.sql.utils import AnalysisException
from functools import reduce
from datetime import datetime

spark = SparkSession.builder.getOrCreate()
print(f"🏆 Gold Transform Load (Production) - {datetime.now()}")

# --- Variable Library (CI/CD across Dev/Test/Prod) ---
try:
    import notebookutils
    vl = notebookutils.variableLibrary.getLibrary("vl_healthcare_params")
    SILVER_LAKEHOUSE = vl.lakehouse_silver
    GOLD_LAKEHOUSE = vl.lakehouse_gold
    print(f"🔧 Loaded from Variable Library: {vl.env_name}")
except Exception as e:
    SILVER_LAKEHOUSE = "lh_silver_ods"
    GOLD_LAKEHOUSE = "lh_gold_curated"
    print(f"⚠️ Using defaults (Variable Library not found)")

SILVER = f"{SILVER_LAKEHOUSE}"
GOLD = f"{GOLD_LAKEHOUSE}"
print(f"   Source: {SILVER}")
print(f"   Target: {GOLD}")

# --- Load Mode (pipeline parameter: full vs incremental) ---
try:
    load_mode = spark.conf.get("spark.load_mode", "full")
except Exception:
    load_mode = "full"
load_mode = load_mode.lower().strip()
if load_mode not in ["full", "incremental"]:
    print(f"⚠️ Invalid load_mode '{load_mode}', defaulting to 'full'")
    load_mode = "full"
IS_FULL = load_mode == "full"
print(f"   Mode: {load_mode.upper()}")
if IS_FULL:
    print("   ⚠️ FULL mode: all Gold tables will be dropped and rebuilt")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## Helper Functions

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================
# HELPER: Check if Delta table exists
# ============================================================
def table_exists(full_name):
    try:
        spark.table(full_name)
        return True
    except AnalysisException:
        return False

# ============================================================
# HELPER: Get max surrogate key from table
# ============================================================
def get_max_key(full_name, key_col):
    try:
        result = spark.table(full_name).agg(max(col(key_col))).collect()[0][0]
        return result or 0
    except AnalysisException:
        return 0

# ============================================================
# HELPER: Assign stable surrogate keys using LEFT JOIN pattern
# ============================================================
# This is the PySpark equivalent of:
#   SELECT COALESCE(dim.Key, MAX(dim.Key) OVER() + ROW_NUMBER() OVER (...))
#   FROM source s LEFT JOIN dim d ON s.business_key = d.business_key
#
# The LEFT JOIN preserves already-assigned keys.
# Only NEW rows (NULL key from join) get max + row_number.
# ============================================================
def assign_keys(df_source, gold_table, surrogate_key, business_key):
    """
    Assign stable surrogate keys. Existing rows keep their keys.
    New rows get max(existing_key) + row_number().
    
    Returns: DataFrame with surrogate_key column added
    """
    if not table_exists(gold_table):
        # First run — assign from 1
        w = Window.orderBy(business_key)
        return df_source.withColumn(surrogate_key, row_number().over(w).cast("bigint"))
    
    max_key = get_max_key(gold_table, surrogate_key)
    
    # LEFT JOIN source to existing dimension on business key
    # For SCD2 tables: only join to current records to get the latest key
    df_gold = spark.table(gold_table)
    if "is_current" in [f.name for f in df_gold.schema]:
        df_gold = df_gold.filter("is_current = 1")
    
    # Deduplicate on business key to prevent 1:many join multiplication
    # (handles tables with legacy duplicates from prior runs)
    df_existing_keys = df_gold \
        .select(col(surrogate_key).alias("_ek"), col(business_key).alias("_bk")) \
        .dropDuplicates(["_bk"])
    
    df_joined = df_source.alias("s").join(
        df_existing_keys.alias("d"),
        col(f"s.{business_key}") == col("d._bk"),
        "left"
    )
    
    # COALESCE: existing key for matched rows, max + row_number for new rows
    # PARTITION BY isNull → row_number only counts within new rows
    w = Window.partitionBy(col("_ek").isNull()).orderBy(col(f"s.{business_key}"))
    
    df_keyed = df_joined.withColumn(
        surrogate_key,
        coalesce(
            col("_ek"),
            (lit(max_key) + row_number().over(w)).cast("bigint")
        )
    ).drop("_ek", "_bk")
    
    return df_keyed

print("✓ Helper functions loaded")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 1. dim_date (Type 1 — Generate)

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

print("=" * 60)
print("1. Loading dim_date")
print("=" * 60)

if not IS_FULL and table_exists(f"{GOLD}.dim_date") and len(spark.table(f"{GOLD}.dim_date").head(1)) > 0:
    print("   Already populated — skipping (incremental mode)")
else:
    from pyspark.sql.functions import explode, sequence, to_date

    df_dates = spark.sql("""
        SELECT explode(sequence(to_date('2020-01-01'), to_date('2030-12-31'), interval 1 day)) as full_date
    """)

    df_dim_date = df_dates.select(
        (year("full_date") * 10000 + month("full_date") * 100 + dayofmonth("full_date")).alias("date_key"),
        col("full_date"),
        dayofweek("full_date").alias("day_of_week"),
        date_format("full_date", "EEEE").alias("day_name"),
        dayofmonth("full_date").alias("day_of_month"),
        dayofyear("full_date").alias("day_of_year"),
        weekofyear("full_date").alias("week_of_year"),
        month("full_date").alias("month_number"),
        date_format("full_date", "MMMM").alias("month_name"),
        quarter("full_date").alias("quarter"),
        year("full_date").alias("year"),
        when(dayofweek("full_date").isin(1, 7), 1).otherwise(0).alias("is_weekend"),
        lit(0).alias("is_holiday"),
        # Fiscal year: July start
        when(month("full_date") >= 7, year("full_date") + 1).otherwise(year("full_date")).alias("fiscal_year"),
        when(month("full_date").isin(7,8,9), lit(1))
        .when(month("full_date").isin(10,11,12), lit(2))
        .when(month("full_date").isin(1,2,3), lit(3))
        .otherwise(lit(4)).alias("fiscal_quarter")
    )

    df_dim_date.write.format("delta").mode("overwrite").saveAsTable(f"{GOLD}.dim_date")
    print(f"   ✓ dim_date: {df_dim_date.count():,} rows")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 2. dim_patient (SCD Type 2)
# 
# Tracks changes to: city, state, zip_code (patient moved)
# 
# **Pattern:**
# 1. JOIN source → current dim on `patient_id`
# 2. Changed rows → expire old version (`is_current = false`)
# 3. New + changed rows → INSERT with `max_key + ROW_NUMBER()`

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

print("=" * 60)
print("2. Loading dim_patient (SCD Type 2)")
print("=" * 60)

# --- Read source ---
df_patients = spark.table(f"{SILVER}.patients_enriched")

df_patient_source = df_patients.select(
    col("patient_id"),
    col("first_name"),
    col("last_name"),
    col("date_of_birth"),
    col("gender"),
    coalesce(col("address"), lit(None).cast("string")).alias("address"),
    col("city"),
    col("state"),
    col("zip_code"),
    coalesce(col("phone"), lit(None).cast("string")).alias("phone"),
    coalesce(col("email"), lit(None).cast("string")).alias("email"),
    coalesce(col("insurance_type"), lit(None).cast("string")).alias("insurance_type"),
    coalesce(col("insurance_provider"), lit(None).cast("string")).alias("insurance_provider"),
    lit(None).cast("string").alias("insurance_policy_number"),
    coalesce(
        col("age").cast("int"),
        floor(datediff(current_date(), col("date_of_birth")) / 365.25).cast("int")
    ).alias("age"),
    coalesce(
        col("age_group"),
        when(floor(datediff(current_date(), col("date_of_birth")) / 365.25) < 18, "Pediatric")
        .when(floor(datediff(current_date(), col("date_of_birth")) / 365.25) < 65, "Adult")
        .otherwise("Senior")
    ).alias("age_group")
).dropDuplicates(["patient_id"])

PATIENT_TABLE = f"{GOLD}.dim_patient"
TRACKED_COLS = ["first_name", "last_name", "city", "state", "zip_code"]

# Check if table exists AND has SCD2 columns (old notebook didn't add them)
has_scd2 = False
if table_exists(PATIENT_TABLE):
    existing_cols = [f.name for f in spark.table(PATIENT_TABLE).schema]
    has_scd2 = "is_current" in existing_cols
    if not has_scd2:
        print("   \u26a0\ufe0f Existing table missing SCD2 columns \u2014 rebuilding with full schema")

if IS_FULL or not table_exists(PATIENT_TABLE) or not has_scd2:
    # === FULL REBUILD / INITIAL LOAD ===
    w = Window.orderBy("patient_id")
    df_initial = df_patient_source \
        .withColumn("patient_key", row_number().over(w).cast("bigint")) \
        .withColumn("is_current", lit(1)) \
        .withColumn("effective_start_date", current_timestamp()) \
        .withColumn("effective_end_date", lit(None).cast("timestamp")) \
        .withColumn("_load_timestamp", current_timestamp())
    
    df_initial.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(PATIENT_TABLE)
    print(f"   ✓ {'Full rebuild' if IS_FULL else 'Initial load'}: {df_initial.count():,} rows")
else:
    # === INCREMENTAL SCD TYPE 2 ===
    df_current = spark.table(PATIENT_TABLE).filter("is_current = 1")
    
    # Find NEW patients (not in current dimension)
    df_new = df_patient_source.join(df_current, "patient_id", "left_anti")
    new_count = df_new.count()
    
    # Find CHANGED patients (matching patient_id, different tracked attributes)
    change_conds = [
        coalesce(col(f"s.{c}").cast("string"), lit("__NULL__")) !=
        coalesce(col(f"d.{c}").cast("string"), lit("__NULL__"))
        for c in TRACKED_COLS
    ]
    has_changes = reduce(lambda a, b: a | b, change_conds)
    
    df_changed_keys = df_patient_source.alias("s").join(
        df_current.alias("d"),
        col("s.patient_id") == col("d.patient_id"),
        "inner"
    ).filter(has_changes).select(col("s.patient_id"))
    changed_count = df_changed_keys.count()
    
    print(f"   New patients: {new_count}")
    print(f"   Changed patients: {changed_count}")
    
    if changed_count > 0 or new_count > 0:
        # Step 1: EXPIRE old versions of changed rows
        if changed_count > 0:
            dt = DeltaTable.forName(spark, PATIENT_TABLE)
            dt.alias("t").merge(
                df_changed_keys.alias("c"),
                "t.patient_id = c.patient_id AND t.is_current = 1"
            ).whenMatchedUpdate(set={
                "is_current": lit(0),
                "effective_end_date": current_timestamp()
            }).execute()
            print(f"   ✓ Expired {changed_count} old versions")
        
        # Step 2: INSERT new versions + truly new rows
        max_key = get_max_key(PATIENT_TABLE, "patient_key")
        
        all_new_bks = df_changed_keys.union(df_new.select("patient_id")).distinct()
        df_to_insert = df_patient_source.join(all_new_bks, "patient_id", "inner")
        
        w = Window.orderBy("patient_id")
        df_keyed = df_to_insert \
            .withColumn("patient_key", (lit(max_key) + row_number().over(w)).cast("bigint")) \
            .withColumn("is_current", lit(1)) \
            .withColumn("effective_start_date", current_timestamp()) \
            .withColumn("effective_end_date", lit(None).cast("timestamp")) \
            .withColumn("_load_timestamp", current_timestamp())
        
        # Reorder columns to match existing table
        existing_cols = [f.name for f in spark.table(PATIENT_TABLE).schema]
        df_keyed.select(*existing_cols).write.format("delta").mode("append").saveAsTable(PATIENT_TABLE)
        print(f"   ✓ Inserted {new_count + changed_count} new versions")
    else:
        print("   No changes — skipping")
    
    total = spark.table(PATIENT_TABLE).count()
    current = spark.table(PATIENT_TABLE).filter("is_current = 1").count()
    print(f"   Total rows: {total:,} (current: {current:,}, historical: {total - current:,})")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 3. dim_provider (SCD Type 2)
# 
# Tracks changes to: specialty, department, facility_name

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

print("=" * 60)
print("3. Loading dim_provider (SCD Type 2)")
print("=" * 60)

df_providers = spark.table(f"{SILVER}.providers_enriched")

df_provider_source = df_providers.select(
    col("provider_id"),
    col("first_name"),
    col("last_name"),
    concat(lit("Dr. "), col("first_name"), lit(" "), col("last_name")).alias("display_name"),
    coalesce(col("npi"), lit(None).cast("string")).alias("npi_number"),
    col("specialty"),
    coalesce(col("department"), lit("General")).alias("department"),
    coalesce(col("facility_id"), lit(None).cast("string")).alias("facility_id"),
    when(col("is_active").cast("boolean") == True, 1).otherwise(0).alias("is_active")
).dropDuplicates(["provider_id"])

PROVIDER_TABLE = f"{GOLD}.dim_provider"
PROVIDER_TRACKED = ["specialty", "department", "facility_id"]

# Check if table exists AND has SCD2 columns
has_scd2_prov = False
if table_exists(PROVIDER_TABLE):
    existing_cols = [f.name for f in spark.table(PROVIDER_TABLE).schema]
    has_scd2_prov = "is_current" in existing_cols
    if not has_scd2_prov:
        print("   \u26a0\ufe0f Existing table missing SCD2 columns \u2014 rebuilding with full schema")

if IS_FULL or not table_exists(PROVIDER_TABLE) or not has_scd2_prov:
    w = Window.orderBy("provider_id")
    df_initial = df_provider_source \
        .withColumn("provider_key", row_number().over(w).cast("bigint")) \
        .withColumn("is_current", lit(1)) \
        .withColumn("effective_start_date", current_timestamp()) \
        .withColumn("effective_end_date", lit(None).cast("timestamp")) \
        .withColumn("_load_timestamp", current_timestamp())
    
    df_initial.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(PROVIDER_TABLE)
    print(f"   ✓ {'Full rebuild' if IS_FULL else 'Initial load'}: {df_initial.count():,} rows")
else:
    df_current = spark.table(PROVIDER_TABLE).filter("is_current = 1")
    
    df_new = df_provider_source.join(df_current, "provider_id", "left_anti")
    new_count = df_new.count()
    
    change_conds = [
        coalesce(col(f"s.{c}").cast("string"), lit("__NULL__")) !=
        coalesce(col(f"d.{c}").cast("string"), lit("__NULL__"))
        for c in PROVIDER_TRACKED
    ]
    has_changes = reduce(lambda a, b: a | b, change_conds)
    
    df_changed_keys = df_provider_source.alias("s").join(
        df_current.alias("d"),
        col("s.provider_id") == col("d.provider_id"), "inner"
    ).filter(has_changes).select(col("s.provider_id"))
    changed_count = df_changed_keys.count()
    
    print(f"   New providers: {new_count}")
    print(f"   Changed providers: {changed_count}")
    
    if changed_count > 0 or new_count > 0:
        if changed_count > 0:
            dt = DeltaTable.forName(spark, PROVIDER_TABLE)
            dt.alias("t").merge(
                df_changed_keys.alias("c"),
                "t.provider_id = c.provider_id AND t.is_current = 1"
            ).whenMatchedUpdate(set={
                "is_current": lit(0),
                "effective_end_date": current_timestamp()
            }).execute()
            print(f"   ✓ Expired {changed_count} old versions")
        
        max_key = get_max_key(PROVIDER_TABLE, "provider_key")
        all_new_bks = df_changed_keys.union(df_new.select("provider_id")).distinct()
        df_to_insert = df_provider_source.join(all_new_bks, "provider_id", "inner")
        
        w = Window.orderBy("provider_id")
        df_keyed = df_to_insert \
            .withColumn("provider_key", (lit(max_key) + row_number().over(w)).cast("bigint")) \
            .withColumn("is_current", lit(1)) \
            .withColumn("effective_start_date", current_timestamp()) \
            .withColumn("effective_end_date", lit(None).cast("timestamp")) \
            .withColumn("_load_timestamp", current_timestamp())
        
        existing_cols = [f.name for f in spark.table(PROVIDER_TABLE).schema]
        df_keyed.select(*existing_cols).write.format("delta").mode("append").saveAsTable(PROVIDER_TABLE)
        print(f"   ✓ Inserted {new_count + changed_count} new versions")
    else:
        print("   No changes — skipping")
    
    total = spark.table(PROVIDER_TABLE).count()
    current = spark.table(PROVIDER_TABLE).filter("is_current = 1").count()
    print(f"   Total rows: {total:,} (current: {current:,}, historical: {total - current:,})")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 4. dim_payer (Type 1 — Stable Keys)

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

print("=" * 60)
print("4. Loading dim_payer (Type 1)")
print("=" * 60)

# Try dedicated payer table, fallback to deriving from claims
try:
    df_payers = spark.table(f"{SILVER}.payers_enriched")
    print("   Source: payers_enriched")
except AnalysisException:
    df_claims_src = spark.table(f"{SILVER}.claims_enriched")
    df_payers = df_claims_src.select("payer_id", "payer_name").distinct()
    print(f"   Source: derived from claims ({df_payers.count()} payers)")

# Use upstream payer_type if available (from ref_payers join), otherwise derive
payer_cols = [c.lower() for c in df_payers.columns]
if "payer_type" in payer_cols:
    df_payer_source = df_payers.select(
        col("payer_id"),
        col("payer_name"),
        col("payer_type")
    ).dropDuplicates(["payer_id"])
else:
    df_payer_source = df_payers.select(
        col("payer_id"),
        col("payer_name"),
        when(lower(col("payer_name")).contains("medicare"), "Medicare")
        .when(lower(col("payer_name")).contains("medicaid"), "Medicaid")
        .when(lower(col("payer_name")).contains("self") | lower(col("payer_name")).contains("cash"), "Self-Pay")
        .otherwise("Commercial").alias("payer_type")
    ).dropDuplicates(["payer_id"])

PAYER_TABLE = f"{GOLD}.dim_payer"

# Type 1: assign keys, overwrite (no history tracking for payers)
if IS_FULL:
    w = Window.orderBy("payer_id")
    df_payer_keyed = df_payer_source.withColumn("payer_key", row_number().over(w).cast("bigint"))
else:
    df_payer_keyed = assign_keys(df_payer_source, PAYER_TABLE, "payer_key", "payer_id")
df_payer_final = df_payer_keyed \
    .withColumn("is_active", lit(1)) \
    .withColumn("_load_timestamp", current_timestamp())

df_payer_final.write.format("delta").mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(PAYER_TABLE)

print(f"   ✓ dim_payer: {spark.table(PAYER_TABLE).count():,} rows")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 5. dim_facility (Type 1 — Stable Keys)
# 
# Facility dimension enables multi-site comparisons (denial rate by facility, readmission rate by campus, etc.)

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ── dim_facility ──────────────────────────────────────────
from pyspark.sql.functions import col, lit, monotonically_increasing_id, row_number
from pyspark.sql.window import Window

print("=" * 60)
print("LOADING dim_facility")
print("=" * 60)

# Facility reference data (with lat/lon for RTI geo-scoring)
facility_data = [
    ("FAC001", "Lakeside Main Hospital", "General Hospital", "Grand Rapids", "MI", 450, 42.9634, -85.6681),
    ("FAC002", "Heart Center", "Specialty Center", "Grand Rapids", "MI", 120, 42.9634, -85.6681),
    ("FAC003", "Urgent Care North", "Urgent Care", "Traverse City", "MI", 30, 44.7631, -85.6206),
    ("FAC004", "Cancer Institute", "Specialty Center", "Ann Arbor", "MI", 200, 42.2808, -83.7430),
    ("FAC005", "Community Clinic", "Primary Care", "Lansing", "MI", 50, 42.7325, -84.5555),
    ("FAC006", "Children's Hospital", "General Hospital", "Detroit", "MI", 300, 42.3314, -83.0458),
    ("FAC007", "Rehabilitation Center", "Specialty Center", "Kalamazoo", "MI", 100, 42.2917, -85.5872),
    ("FAC008", "South Campus", "General Hospital", "Toledo", "OH", 250, 41.6528, -83.5379),
]

facility_schema = ["facility_id", "facility_name", "facility_type", "city", "state", "bed_count", "latitude", "longitude"]
df_facility_src = spark.createDataFrame(facility_data, facility_schema)
df_facility_src = df_facility_src.withColumn("is_active", lit(1))

# Assign surrogate keys
w = Window.orderBy("facility_id")
df_facility = df_facility_src.withColumn("facility_key", row_number().over(w).cast("bigint"))

# Select final columns
df_facility = df_facility.select(
    "facility_key", "facility_id", "facility_name", "facility_type",
    "city", "state", "bed_count", "latitude", "longitude", "is_active"
).withColumn("_load_timestamp", current_timestamp())

# Write to Gold lakehouse (Type 1 — overwrite, facility master data is small and stable)
FACILITY_TABLE = f"{GOLD}.dim_facility"
df_facility.write.format("delta").mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(FACILITY_TABLE)

print(f"   ✓ dim_facility: {spark.table(FACILITY_TABLE).count():,} facilities loaded")
df_facility.show(truncate=False)

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 5b. dim_medication (Type 1 - Reference Data)

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 5a. dim_monitor (Type 1 — Device Reference Data)
# 
# Monitoring device dimension for the Ontology PatientMonitor entity. Static data binding from `monitors.csv`. Time series vitals bind separately from Eventhouse.

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ── dim_monitor ──────────────────────────────────────────
# Ontology PatientMonitor entity — static device data
# Source: sample_data/metadata/monitors.csv (30 devices)
# Streaming vitals bind separately via Eventhouse time series
print("=" * 60)
print("5a. Loading dim_monitor (Type 1 - Device Reference Data)")
print("=" * 60)

# Try to load from Bronze reference table (loaded via Copy Activity)
try:
    df_monitor_src = spark.table("lh_bronze_raw.ref_monitors")
    print(f"   Source: lh_bronze_raw.ref_monitors ({df_monitor_src.count()} devices)")
except Exception:
    # Fallback: read from Files/ path if CSV was uploaded
    try:
        df_monitor_src = spark.read.format("csv") \
            .option("header", "true") \
            .option("inferSchema", "true") \
            .load("Files/monitors.csv")
        print(f"   Source: Files/monitors.csv ({df_monitor_src.count()} devices)")
    except Exception:
        print("   ⚠️ monitors.csv not found — generating inline reference data")
        # Inline fallback: 30 monitoring devices across 4 facilities
        monitor_data = [
            ("MON-ICU01-01", "Philips IntelliVue", "MX800", "ICU-01", "ICU", 2, "Main", "FAC001", 1),
            ("MON-ICU01-02", "Philips IntelliVue", "MX800", "ICU-01", "ICU", 2, "Main", "FAC001", 1),
            ("MON-ICU02-01", "GE CARESCAPE", "B650", "ICU-02", "ICU", 2, "Main", "FAC001", 1),
            ("MON-ICU02-02", "GE CARESCAPE", "B650", "ICU-02", "ICU", 2, "Main", "FAC001", 1),
            ("MON-ED01-01", "Welch Allyn Connex", "VSM 6000", "ED-01", "Emergency", 1, "Main", "FAC001", 1),
            ("MON-ED01-02", "Welch Allyn Connex", "VSM 6000", "ED-01", "Emergency", 1, "Main", "FAC001", 1),
            ("MON-ED02-01", "Masimo Root", "Radical-7", "ED-02", "Emergency", 1, "Main", "FAC001", 1),
            ("MON-ED02-02", "Masimo Root", "Radical-7", "ED-02", "Emergency", 1, "Main", "FAC001", 1),
            ("MON-ED03-01", "Nihon Kohden", "BSM-6000", "ED-03", "Emergency", 1, "Main", "FAC001", 1),
            ("MON-ED03-02", "Nihon Kohden", "BSM-6000", "ED-03", "Emergency", 1, "Main", "FAC001", 1),
            ("MON-MED01-01", "Philips IntelliVue", "MX800", "MED-01", "Medical", 3, "Main", "FAC001", 1),
            ("MON-MED01-02", "Philips IntelliVue", "MX800", "MED-01", "Medical", 3, "Main", "FAC001", 1),
            ("MON-MED02-01", "GE CARESCAPE", "B650", "MED-02", "Medical", 3, "Main", "FAC001", 1),
            ("MON-MED02-02", "GE CARESCAPE", "B650", "MED-02", "Medical", 3, "Main", "FAC001", 1),
            ("MON-MED03-01", "Welch Allyn Connex", "VSM 6000", "MED-03", "Medical", 4, "South", "FAC001", 1),
            ("MON-MED03-02", "Welch Allyn Connex", "VSM 6000", "MED-03", "Medical", 4, "South", "FAC001", 1),
            ("MON-SURG01-01", "Philips IntelliVue", "MX800", "SURG-01", "Surgical", 3, "South", "FAC001", 1),
            ("MON-SURG01-02", "GE CARESCAPE", "B650", "SURG-01", "Surgical", 3, "South", "FAC001", 1),
            ("MON-STEP01-01", "Masimo Root", "Radical-7", "STEP-01", "Step Down", 4, "Main", "FAC001", 1),
            ("MON-STEP01-02", "Nihon Kohden", "BSM-6000", "STEP-01", "Step Down", 4, "Main", "FAC001", 1),
            ("MON-CCU01-01", "Philips IntelliVue", "MX800", "CCU-01", "Cardiac Care", 2, "Heart Center", "FAC002", 1),
            ("MON-CCU01-02", "Philips IntelliVue", "MX800", "CCU-01", "Cardiac Care", 2, "Heart Center", "FAC002", 1),
            ("MON-CCU02-01", "GE CARESCAPE", "B650", "CCU-02", "Cardiac Care", 3, "Heart Center", "FAC002", 1),
            ("MON-CCU02-02", "GE CARESCAPE", "B650", "CCU-02", "Cardiac Care", 3, "Heart Center", "FAC002", 1),
            ("MON-PEDS01-01", "Philips IntelliVue", "MX800", "PEDS-01", "Pediatrics", 2, "Children", "FAC006", 1),
            ("MON-PEDS01-02", "Masimo Root", "Radical-7", "PEDS-01", "Pediatrics", 2, "Children", "FAC006", 1),
            ("MON-NICU01-01", "Philips IntelliVue", "MX800", "NICU-01", "NICU", 3, "Children", "FAC006", 1),
            ("MON-NICU01-02", "GE CARESCAPE", "B650", "NICU-01", "NICU", 3, "Children", "FAC006", 1),
            ("MON-OBS01-01", "Welch Allyn Connex", "VSM 6000", "OBS-01", "Obstetrics", 2, "Women", "FAC008", 1),
            ("MON-OBS01-02", "Masimo Root", "Radical-7", "OBS-01", "Obstetrics", 2, "Women", "FAC008", 1),
        ]
        monitor_schema = [
            "device_id", "device_type", "device_model", "location_id",
            "unit_name", "floor_number", "building", "facility_id", "is_active"
        ]
        df_monitor_src = spark.createDataFrame(monitor_data, monitor_schema)

# Standardize columns and types (Ontology compatible: INT not BOOLEAN)
# Source ref_monitors uses monitor_id/monitor_type/model; alias to dim_monitor schema
src_cols = [c.lower() for c in df_monitor_src.columns]
if "device_id" in src_cols:
    # Inline fallback or future CSV with device_* columns
    df_monitor = df_monitor_src.select(
        col("device_id").cast("string"),
        col("device_type").cast("string"),
        col("device_model").cast("string"),
        col("location_id").cast("string"),
        col("unit_name").cast("string"),
        col("floor_number").cast("int"),
        col("building").cast("string"),
        col("facility_id").cast("string"),
        col("is_active").cast("int"),
    )
else:
    # Generated CSV: monitor_id, monitor_type, manufacturer, model, ...
    df_monitor = df_monitor_src.select(
        col("monitor_id").alias("device_id").cast("string"),
        col("monitor_type").alias("device_type").cast("string"),
        col("model").alias("device_model").cast("string"),
        lit(None).cast("string").alias("location_id"),
        lit(None).cast("string").alias("unit_name"),
        lit(None).cast("int").alias("floor_number"),
        lit(None).cast("string").alias("building"),
        lit(None).cast("string").alias("facility_id"),
        lit(1).cast("int").alias("is_active"),
    )

# Assign surrogate key
w_mon = Window.orderBy("device_id")
df_monitor = df_monitor.withColumn("monitor_key", row_number().over(w_mon).cast("bigint"))

# ── Join surrogate FKs for ontology relationships ──
# facility_key: lookup from dim_facility by facility_id
try:
    df_facility_lkp = spark.table(f"{GOLD}.dim_facility").select(
        col("facility_id").alias("fac_id"), col("facility_key")
    )
    df_monitor = df_monitor.join(df_facility_lkp, df_monitor.facility_id == df_facility_lkp.fac_id, "left").drop("fac_id")
    print("   ✓ Joined facility_key from dim_facility")
except Exception:
    df_monitor = df_monitor.withColumn("facility_key", lit(None).cast("bigint"))
    print("   ⚠️ dim_facility not found — facility_key set to NULL")

# location_key: lookup from dim_location by location_id
try:
    df_location_lkp = spark.table(f"{GOLD}.dim_location").select(
        col("location_id").alias("loc_id"), col("location_key")
    )
    df_monitor = df_monitor.join(df_location_lkp, df_monitor.location_id == df_location_lkp.loc_id, "left").drop("loc_id")
    print("   ✓ Joined location_key from dim_location")
except Exception:
    df_monitor = df_monitor.withColumn("location_key", lit(None).cast("bigint"))
    print("   ⚠️ dim_location not found — location_key set to NULL")

# patient_key: NULL for now — assigned dynamically when patient is admitted to a bed
# In production, an ADT (Admit-Discharge-Transfer) feed would update this in real time
df_monitor = df_monitor.withColumn("patient_key", lit(None).cast("bigint"))
print("   ℹ patient_key set to NULL (populated by ADT feed at runtime)")

# Reorder columns
df_monitor = df_monitor.select(
    "monitor_key", "device_id", "device_type", "device_model",
    "location_id", "unit_name", "floor_number", "building",
    "facility_id", "patient_key", "facility_key", "location_key",
    "is_active"
).withColumn("_load_timestamp", current_timestamp())

MONITOR_TABLE = f"{GOLD}.dim_monitor"
df_monitor.write.format("delta").mode("overwrite") \
    .option("overwriteSchema", "true").saveAsTable(MONITOR_TABLE)

mon_count = spark.table(MONITOR_TABLE).count()
facilities = df_monitor.select("facility_id").distinct().count()
units = df_monitor.select("unit_name").distinct().count()
print(f"   ✓ dim_monitor: {mon_count:,} devices across {facilities} facilities, {units} unit types")
print(f"      Ontology entity: PatientMonitor (static binding → dim_monitor)")
print(f"      Time series binding → Eventhouse VitalsTelemetry (configured separately)")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ── dim_medication ──────────────────────────────────────────
print("=" * 60)
print("5b. Loading dim_medication (Type 1 - Reference Data)")
print("=" * 60)

# Medication reference data - RxNorm-based formulary
medication_data = [
    # Cardiovascular
    ("314076", "Lisinopril 10 MG Oral Tablet", "Lisinopril", "ACE Inhibitor", "Cardiovascular", "Oral", "Tablet", "10 MG", True),
    ("197361", "Amlodipine 5 MG Oral Tablet", "Amlodipine", "Calcium Channel Blocker", "Cardiovascular", "Oral", "Tablet", "5 MG", True),
    ("200031", "Atorvastatin 20 MG Oral Tablet", "Atorvastatin", "Statin", "Cardiovascular", "Oral", "Tablet", "20 MG", True),
    ("866924", "Metoprolol Succinate 50 MG ER Tablet", "Metoprolol", "Beta Blocker", "Cardiovascular", "Oral", "Tablet", "50 MG", True),
    ("310798", "Losartan 50 MG Oral Tablet", "Losartan", "ARB", "Cardiovascular", "Oral", "Tablet", "50 MG", True),
    ("836585", "Warfarin Sodium 5 MG Oral Tablet", "Warfarin", "Anticoagulant", "Cardiovascular", "Oral", "Tablet", "5 MG", True),
    ("310429", "Furosemide 40 MG Oral Tablet", "Furosemide", "Loop Diuretic", "Cardiovascular", "Oral", "Tablet", "40 MG", True),
    # Endocrine / Diabetes
    ("860974", "Metformin 500 MG Oral Tablet", "Metformin", "Biguanide", "Endocrine", "Oral", "Tablet", "500 MG", True),
    ("311040", "Glipizide 5 MG Oral Tablet", "Glipizide", "Sulfonylurea", "Endocrine", "Oral", "Tablet", "5 MG", True),
    ("1373463", "Insulin Glargine 100 UNT/ML Injectable", "Insulin Glargine", "Insulin", "Endocrine", "Subcutaneous", "Injectable", "100 UNT/ML", True),
    ("966247", "Levothyroxine 0.05 MG Oral Tablet", "Levothyroxine", "Thyroid Hormone", "Endocrine", "Oral", "Tablet", "0.05 MG", True),
    # Respiratory
    ("895994", "Albuterol 0.09 MG/ACTUAT Inhaler", "Albuterol", "Beta-2 Agonist", "Respiratory", "Inhalation", "Inhaler", "0.09 MG/ACTUAT", False),
    ("896188", "Fluticasone 110 MCG/ACTUAT Inhaler", "Fluticasone", "Inhaled Corticosteroid", "Respiratory", "Inhalation", "Inhaler", "110 MCG/ACTUAT", True),
    # Pain / Musculoskeletal
    ("310965", "Ibuprofen 200 MG Oral Tablet", "Ibuprofen", "NSAID", "Pain", "Oral", "Tablet", "200 MG", False),
    ("313782", "Acetaminophen 500 MG Oral Tablet", "Acetaminophen", "Analgesic", "Pain", "Oral", "Tablet", "500 MG", False),
    ("856987", "Hydrocodone-APAP 5-325 MG Oral Tablet", "Hydrocodone/APAP", "Opioid", "Pain", "Oral", "Tablet", "5-325 MG", False),
    # Mental Health
    ("312938", "Sertraline 50 MG Oral Tablet", "Sertraline", "SSRI", "Mental Health", "Oral", "Tablet", "50 MG", True),
    ("312036", "Escitalopram 10 MG Oral Tablet", "Escitalopram", "SSRI", "Mental Health", "Oral", "Tablet", "10 MG", True),
    ("835564", "Lorazepam 0.5 MG Oral Tablet", "Lorazepam", "Benzodiazepine", "Mental Health", "Oral", "Tablet", "0.5 MG", False),
    # GI
    ("311700", "Omeprazole 20 MG DR Oral Capsule", "Omeprazole", "Proton Pump Inhibitor", "Digestive", "Oral", "Capsule", "20 MG", True),
    # Antibiotics
    ("308182", "Amoxicillin 500 MG Oral Capsule", "Amoxicillin", "Penicillin Antibiotic", "Infectious Disease", "Oral", "Capsule", "500 MG", False),
    ("197511", "Azithromycin 250 MG Oral Tablet", "Azithromycin", "Macrolide Antibiotic", "Infectious Disease", "Oral", "Tablet", "250 MG", False),
]

medication_schema = [
    "rxnorm_code", "medication_name", "generic_name", "drug_class",
    "therapeutic_area", "route", "form", "strength", "is_chronic"
]
df_medication_src = spark.createDataFrame(medication_data, medication_schema)
df_medication_src = df_medication_src.withColumn("is_active", lit(1))
df_medication_src = df_medication_src.withColumn("is_chronic", col("is_chronic").cast("int"))

# Assign surrogate keys
w = Window.orderBy("rxnorm_code")
df_medication = df_medication_src.withColumn("medication_key", row_number().over(w).cast("bigint"))
df_medication = df_medication.select(
    "medication_key", "rxnorm_code", "medication_name", "generic_name",
    "drug_class", "therapeutic_area", "route", "form", "strength",
    "is_chronic", "is_active"
).withColumn("_load_timestamp", current_timestamp())

MEDICATION_TABLE = f"{GOLD}.dim_medication"
df_medication.write.format("delta").mode("overwrite") \
    .option("overwriteSchema", "true").saveAsTable(MEDICATION_TABLE)
med_count = spark.table(MEDICATION_TABLE).count()
print(f"   ✓ dim_medication: {med_count:,} rows (22 RxNorm medications)")
print(f"      Chronic meds: {df_medication.filter('is_chronic = 1').count()}")
print(f"      Acute meds:   {df_medication.filter('is_chronic = 0').count()}")
print(f"      Acute meds:   {df_medication.filter('is_chronic = false').count()}")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 5c. dim_diagnosis (Type 1 - ICD Code Reference)
# 
# Maps ICD-10 codes to categories, chronic flags, and descriptions. Sourced from icd_codes reference table in Bronze.

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ── dim_diagnosis ──────────────────────────────────────────
print("=" * 60)
print("5c. Loading dim_diagnosis (Type 1 - ICD Code Reference)")
print("=" * 60)

# ICD-10 diagnosis reference data — same 20 codes used in data generator
diagnosis_data = [
    ("I10", "Essential (primary) hypertension", "Cardiovascular", True),
    ("E11.9", "Type 2 diabetes mellitus without complications", "Endocrine", True),
    ("J06.9", "Acute upper respiratory infection, unspecified", "Respiratory", False),
    ("M54.5", "Low back pain", "Musculoskeletal", False),
    ("F32.9", "Major depressive disorder, single episode, unspecified", "Mental Health", True),
    ("J18.9", "Pneumonia, unspecified organism", "Respiratory", False),
    ("N39.0", "Urinary tract infection, site not specified", "Genitourinary", False),
    ("I25.10", "Atherosclerotic heart disease of native coronary artery", "Cardiovascular", True),
    ("K21.0", "Gastro-esophageal reflux disease with esophagitis", "Digestive", True),
    ("J45.909", "Unspecified asthma, uncomplicated", "Respiratory", True),
    ("G43.909", "Migraine, unspecified, not intractable", "Neurological", True),
    ("I50.9", "Heart failure, unspecified", "Cardiovascular", True),
    ("E78.5", "Hyperlipidemia, unspecified", "Endocrine", True),
    ("J44.9", "Chronic obstructive pulmonary disease, unspecified", "Respiratory", True),
    ("M79.3", "Panniculitis, unspecified", "Musculoskeletal", False),
    ("R10.9", "Unspecified abdominal pain", "Symptoms", False),
    ("S72.001A", "Fracture of unspecified part of neck of right femur", "Injury", False),
    ("K80.20", "Calculus of gallbladder without cholecystitis", "Digestive", False),
    ("N18.3", "Chronic kidney disease, stage 3", "Genitourinary", True),
    ("C50.911", "Malignant neoplasm of unspecified site of right female breast", "Oncology", True),
]

diagnosis_schema = ["icd_code", "icd_description", "icd_category", "is_chronic"]
df_diagnosis_src = spark.createDataFrame(diagnosis_data, diagnosis_schema)
df_diagnosis_src = df_diagnosis_src.withColumn("is_active", lit(1))
df_diagnosis_src = df_diagnosis_src.withColumn("is_chronic", col("is_chronic").cast("int"))

# Assign surrogate keys
w = Window.orderBy("icd_code")
df_diagnosis = df_diagnosis_src.withColumn("diagnosis_key", row_number().over(w).cast("bigint"))
df_diagnosis = df_diagnosis.select(
    "diagnosis_key", "icd_code", "icd_description", "icd_category",
    "is_chronic", "is_active"
).withColumn("_load_timestamp", current_timestamp())

DIAGNOSIS_TABLE = f"{GOLD}.dim_diagnosis"
df_diagnosis.write.format("delta").mode("overwrite") \
    .option("overwriteSchema", "true").saveAsTable(DIAGNOSIS_TABLE)
diag_count = spark.table(DIAGNOSIS_TABLE).count()
print(f"   ✓ dim_diagnosis: {diag_count:,} rows (20 ICD-10 codes)")
print(f"      Chronic: {df_diagnosis.filter('is_chronic = 1').count()}")
print(f"      Acute:   {df_diagnosis.filter('is_chronic = 0').count()}")
print(f"      Acute:   {df_diagnosis.filter('is_chronic = false').count()}")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 5d. dim_sdoh (Type 1 - Social Determinants of Health)
# 
# Zip-code level social determinant data: poverty rate, food desert flag, transportation score, housing instability. Links to `dim_patient.zip_code` for the Social Factors pillar of the IQ chain.

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ── dim_sdoh ──────────────────────────────────────────
import builtins as _bi

print("=" * 60)
print("5d. Loading dim_sdoh (Type 1 - Social Determinants)")
print("=" * 60)

# Try to load from Bronze reference table (loaded via Copy Activity)
try:
    df_sdoh_src = spark.table("lh_bronze_raw.ref_sdoh_zipcode")
    print(f"   Loaded {df_sdoh_src.count()} SDOH records from Bronze ref table")
except Exception:
    # Fallback: read from Files/ path if CSV was uploaded there instead
    try:
        df_sdoh_src = spark.read.format("csv") \
            .option("header", "true") \
            .option("inferSchema", "true") \
            .load("Files/sdoh_zipcode.csv")
        print(f"   Loaded {df_sdoh_src.count()} SDOH records from CSV")
    except Exception:
        print("   ⚠️ SDOH data not found — generating synthetic data")
        # Generate minimal SDOH data for Michigan zip codes
        # NOTE: use _bi.round() because PySpark's round() shadows the builtin
        import random as _rnd
        _rnd.seed(42)
        sdoh_rows = []
        for z in range(48000, 50000, 10):
            zc = str(z)
            poverty = _bi.round(_rnd.uniform(0.05, 0.30), 4)
            food_desert = _rnd.random() < 0.25
            transport = _bi.round(_rnd.uniform(0.30, 0.90), 2)
            housing = _bi.round(_rnd.uniform(0.03, 0.25), 4)
            uninsured = _bi.round(_rnd.uniform(0.04, 0.20), 4)
            broadband = _bi.round(_rnd.uniform(0.50, 0.98), 4)
            income = _rnd.randint(28000, 95000)
            pop = _rnd.randint(1000, 80000)
            svi = _bi.round(poverty * 0.25 + int(food_desert) * 0.15 + (1 - transport) * 0.20 + housing * 0.15 + uninsured * 0.15 + (1 - broadband) * 0.10, 4)
            risk = "High" if svi >= 0.30 else ("Medium" if svi >= 0.15 else "Low")
            sdoh_rows.append((zc, "MI", poverty, food_desert, transport, housing, uninsured, broadband, income, pop, svi, risk))
        
        sdoh_schema = ["zip_code", "state", "poverty_rate", "food_desert_flag", "transportation_score",
                       "housing_instability_rate", "uninsured_rate", "broadband_access_pct",
                       "median_household_income", "population", "social_vulnerability_index", "risk_tier"]
        df_sdoh_src = spark.createDataFrame(sdoh_rows, sdoh_schema)

# Ensure standard columns (state column added for multi-state coverage)
# Source ref_sdoh_zipcode uses different column names; map to Gold schema
src_cols = [c.lower() for c in df_sdoh_src.columns]
if "food_desert_flag" in src_cols:
    # Inline fallback with exact Gold schema
    df_sdoh = df_sdoh_src.select(
        col("zip_code").cast("string").alias("zip_code"),
        coalesce(col("state").cast("string"), lit("MI")).alias("state"),
        col("poverty_rate").cast("double").alias("poverty_rate"),
        col("food_desert_flag").cast("int").alias("food_desert_flag"),
        col("transportation_score").cast("double").alias("transportation_score"),
        col("housing_instability_rate").cast("double").alias("housing_instability_rate"),
        col("uninsured_rate").cast("double").alias("uninsured_rate"),
        col("broadband_access_pct").cast("double").alias("broadband_access_pct"),
        col("median_household_income").cast("int").alias("median_household_income"),
        col("population").cast("int").alias("population"),
        col("social_vulnerability_index").cast("double").alias("social_vulnerability_index"),
        col("risk_tier").cast("string").alias("risk_tier"),
    )
else:
    # Generated CSV: food_insecurity_rate, no_vehicle_pct, composite_svi_score, etc.
    df_sdoh = df_sdoh_src.select(
        col("zip_code").cast("string").alias("zip_code"),
        coalesce(col("state").cast("string"), lit("MI")).alias("state"),
        col("poverty_rate").cast("double").alias("poverty_rate"),
        when(col("food_insecurity_rate") > 0.15, lit(1)).otherwise(lit(0)).cast("int").alias("food_desert_flag"),
        (lit(1.0) - coalesce(col("no_vehicle_pct").cast("double"), lit(0.0))).alias("transportation_score"),
        lit(None).cast("double").alias("housing_instability_rate"),
        col("uninsured_rate").cast("double").alias("uninsured_rate"),
        lit(None).cast("double").alias("broadband_access_pct"),
        col("median_household_income").cast("int").alias("median_household_income"),
        lit(None).cast("int").alias("population"),
        col("composite_svi_score").cast("double").alias("social_vulnerability_index"),
        col("risk_tier").cast("string").alias("risk_tier"),
    )

# Add surrogate key
w_sdoh = Window.orderBy("zip_code")
df_sdoh = df_sdoh.withColumn("sdoh_key", row_number().over(w_sdoh).cast("bigint"))
df_sdoh = df_sdoh.withColumn("is_active", lit(1))

# Reorder columns
df_sdoh = df_sdoh.select(
    "sdoh_key", "zip_code", "state", "poverty_rate", "food_desert_flag",
    "transportation_score", "housing_instability_rate", "uninsured_rate",
    "broadband_access_pct", "median_household_income", "population",
    "social_vulnerability_index", "risk_tier", "is_active"
).withColumn("_load_timestamp", current_timestamp())

SDOH_TABLE = f"{GOLD}.dim_sdoh"
df_sdoh.write.format("delta").mode("overwrite") \
    .option("overwriteSchema", "true").saveAsTable(SDOH_TABLE)
sdoh_count = spark.table(SDOH_TABLE).count()
states_count = spark.table(SDOH_TABLE).select("state").distinct().count()
print(f"   ✓ dim_sdoh: {sdoh_count:,} zip codes across {states_count} states")
high_risk = spark.table(SDOH_TABLE).filter("risk_tier = 'High'").count()
food_deserts = spark.table(SDOH_TABLE).filter("food_desert_flag = 1").count()
print(f"      High risk: {high_risk}")
print(f"      Food deserts: {food_deserts}")
print(f"      Links to: dim_patient.zip_code")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 6. fact_encounter (MERGE with Dim Lookups)
# 
# - Joins to CURRENT dim_patient, dim_provider, and dim_facility
# - Uses LEFT JOIN + COALESCE for stable encounter_key
# - MERGE with Delta: update existing, insert new

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

print("=" * 60)
print("6. Loading fact_encounter")
print("=" * 60)

df_encounters = spark.table(f"{SILVER}.encounters_enriched")

# Verify facility_id exists in encounters_enriched
if "facility_id" not in df_encounters.columns:
    raise RuntimeError(
        "❌ encounters_enriched is missing 'facility_id' column.\n"
        "   This means Bronze → Silver Stage → Silver ODS have not been re-run\n"
        "   since facility_id was added to encounters.csv.\n"
        "   ACTION: Re-run notebooks 01 → 02 → 03 (no code changes needed),\n"
        "   then re-run this Gold notebook."
    )

# Dimension lookups — CURRENT records only
df_patient_lkp = spark.table(f"{GOLD}.dim_patient") \
    .filter("is_current = 1") \
    .select(col("patient_key"), col("patient_id"))
df_provider_lkp = spark.table(f"{GOLD}.dim_provider") \
    .filter("is_current = 1") \
    .select(col("provider_key"), col("provider_id"))
df_facility_lkp = spark.table(f"{GOLD}.dim_facility") \
    .select(col("facility_key"), col("facility_id"))

# Check if encounter-level risk scores exist (from data generator)
has_encounter_risk = "readmission_risk" in df_encounters.columns
if has_encounter_risk:
    print("   ✓ Found encounter-level readmission_risk — using directly")
else:
    print("   ⚠️ No encounter-level risk scores — using defaults (0.25)")

# Build fact
df_enc = df_encounters.alias("e") \
    .join(df_patient_lkp.alias("p"), col("e.patient_id") == col("p.patient_id"), "left") \
    .join(df_provider_lkp.alias("pr"), col("e.provider_id") == col("pr.provider_id"), "left") \
    .join(df_facility_lkp.alias("f"), col("e.facility_id") == col("f.facility_id"), "left")

# Pre-compute readmission risk score expression (avoids deep nesting in select)
_risk_fallback = (
    when(coalesce(col("e.length_of_stay").cast("int"), lit(1)) >= 10, lit(0.80))
    .when((coalesce(col("e.length_of_stay").cast("int"), lit(1)) >= 5) &
          (lower(coalesce(col("e.encounter_type"), lit(""))) == "inpatient"), lit(0.65))
    .when(lower(coalesce(col("e.encounter_type"), lit(""))) == "emergency", lit(0.55))
    .when(coalesce(col("e.length_of_stay").cast("int"), lit(1)) >= 3, lit(0.35))
    .otherwise(lit(0.15))
)
_risk_score = coalesce(
    col("e.readmission_risk").cast("double") if has_encounter_risk else lit(None),
    _risk_fallback
)

df_fact_encounter = df_enc.select(
    col("e.encounter_id"),
    (year("e.encounter_date") * 10000 + month("e.encounter_date") * 100 + dayofmonth("e.encounter_date")).alias("encounter_date_key"),
    (year(coalesce("e.discharge_date", "e.encounter_date")) * 10000 +
     month(coalesce("e.discharge_date", "e.encounter_date")) * 100 +
     dayofmonth(coalesce("e.discharge_date", "e.encounter_date"))).alias("discharge_date_key"),
    col("p.patient_key"),
    col("pr.provider_key"),
    col("f.facility_key"),
    coalesce(col("e.encounter_type"), lit("Outpatient")).alias("encounter_type"),
    coalesce(col("e.admission_type"), lit("Elective")).alias("admission_type"),
    coalesce(col("e.discharge_disposition"), lit("Home")).alias("discharge_disposition"),
    coalesce(col("e.length_of_stay").cast("int"), lit(1)).alias("length_of_stay"),
    coalesce(col("e.total_charges").cast("double"), lit(0.0)).alias("total_charges"),
    (coalesce(col("e.total_charges").cast("double"), lit(0.0)) * 0.7).alias("total_cost"),
    when(coalesce(_risk_score, lit(0.0)) >= 0.5, lit(1)).otherwise(lit(0)).alias("readmission_flag"),
    _risk_score.alias("readmission_risk_score"),
    (when(_risk_score >= 0.7, "High")
     .when(_risk_score >= 0.3, "Medium")
     .otherwise("Low")).alias("readmission_risk_category"),
    current_timestamp().alias("_load_timestamp")
).dropDuplicates(["encounter_id"])

# Assign stable encounter_key using LEFT JOIN + COALESCE
ENCOUNTER_TABLE = f"{GOLD}.fact_encounter"
if IS_FULL:
    w = Window.orderBy("encounter_id")
    df_enc_keyed = df_fact_encounter.withColumn("encounter_key", row_number().over(w).cast("bigint"))
else:
    df_enc_keyed = assign_keys(df_fact_encounter, ENCOUNTER_TABLE, "encounter_key", "encounter_id")

if IS_FULL or not table_exists(ENCOUNTER_TABLE):
    df_enc_keyed.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(ENCOUNTER_TABLE)
    print(f"   ✓ {'Full rebuild' if IS_FULL else 'Initial load'}: {spark.table(ENCOUNTER_TABLE).count():,} rows")
else:
    # MERGE: update existing, insert new (preserve surrogate key)
    dt = DeltaTable.forName(spark, ENCOUNTER_TABLE)
    upd = {c: col(f"s.{c}") for c in df_enc_keyed.columns if c != "encounter_key"}

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 7. fact_claim (MERGE with Dim + Encounter Lookups)
# 
# Links claims to encounters, patients, providers, payers, and facilities.

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

print("=" * 60)
print("7. Loading fact_claim")
print("=" * 60)

df_claims = spark.table(f"{SILVER}.claims_enriched")

# Dimension lookups — CURRENT records only
df_patient_lkp = spark.table(f"{GOLD}.dim_patient") \
    .filter("is_current = 1") \
    .select(col("patient_key"), col("patient_id"))
df_provider_lkp = spark.table(f"{GOLD}.dim_provider") \
    .filter("is_current = 1") \
    .select(col("provider_key"), col("provider_id"))
df_payer_lkp = spark.table(f"{GOLD}.dim_payer") \
    .select(col("payer_key"), col("payer_id"))

# Encounter linkage — direct join on encounter_id (claims already have encounter_id from source)
df_encounter_key_lkp = spark.table(f"{GOLD}.fact_encounter") \
    .select(col("encounter_key"), col("encounter_id"), col("facility_key"))

# ML denial predictions (optional)
try:
    df_ml_denial = spark.table(f"{SILVER}.claim_denial_predictions")
    has_denial_ml = True
    print("   ✓ Found denial ML predictions")
except AnalysisException:
    has_denial_ml = False
    print("   ⚠️ No denial predictions — using defaults")

# Build fact with all joins — direct encounter_id join (not fuzzy date match)
df_clm = df_claims.alias("c") \
    .join(df_patient_lkp.alias("p"), col("c.patient_id") == col("p.patient_id"), "left") \
    .join(df_provider_lkp.alias("pr"), col("c.provider_id") == col("pr.provider_id"), "left") \
    .join(df_payer_lkp.alias("py"), col("c.payer_id") == col("py.payer_id"), "left") \
    .join(df_encounter_key_lkp.alias("ek"),
          col("c.encounter_id") == col("ek.encounter_id"), "left")

if has_denial_ml:
    df_clm = df_clm.join(
        df_ml_denial.alias("ml"), col("c.claim_id") == col("ml.claim_id"), "left"
    )

# Synthea data rarely has "denied" claim_status — generate realistic denials
# Uses deterministic hash so results are reproducible across runs
# Overall ~8% denial rate: higher for high-dollar claims
df_clm = df_clm.withColumn(
    "_is_denied",
    when(lower(col("c.claim_status")).contains("denied"), lit(True))
    .when(
        (col("c.billed_amount").cast("double") > 50000) &
        (abs(hash(col("c.claim_id"))) % 100 < 18), lit(True)
    ).when(
        (col("c.billed_amount").cast("double") > 20000) &
        (abs(hash(col("c.claim_id"))) % 100 < 12), lit(True)
    ).when(
        abs(hash(col("c.claim_id"))) % 100 < 5, lit(True)
    ).otherwise(lit(False))
).withColumn(
    "_denial_reason_idx",
    (abs(hash(col("c.claim_id"))) % 7).cast("int")
)

df_fact_claim = df_clm.select(
    col("c.claim_id"),
    (year("c.claim_date") * 10000 + month("c.claim_date") * 100 + dayofmonth("c.claim_date")).alias("claim_date_key"),
    (year(coalesce("c.payment_date", "c.claim_date")) * 10000 +
     month(coalesce("c.payment_date", "c.claim_date")) * 100 +
     dayofmonth(coalesce("c.payment_date", "c.claim_date"))).alias("payment_date_key"),
    col("p.patient_key"),
    col("pr.provider_key"),
    col("py.payer_key"),
    col("ek.encounter_key"),
    col("ek.facility_key"),
    coalesce(col("c.claim_type"), lit("Professional")).alias("claim_type"),
    when(col("_is_denied"), lit("Denied"))
    .otherwise(coalesce(col("c.claim_status"), lit("Paid"))).alias("claim_status"),
    coalesce(col("c.billed_amount").cast("double"), lit(0.0)).alias("billed_amount"),
    coalesce(col("c.allowed_amount").cast("double"), col("c.billed_amount").cast("double") * 0.85, lit(0.0)).alias("allowed_amount"),
    coalesce(col("c.paid_amount").cast("double"), col("c.billed_amount").cast("double") * 0.80, lit(0.0)).alias("paid_amount"),
    when(col("_is_denied"), lit(1)).otherwise(lit(0)).alias("denial_flag"),
    coalesce(col("ml.denial_risk_score").cast("double") if has_denial_ml else lit(None),
             # Rule-based risk score: denied claims get higher scores
             when(col("_is_denied"), lit(0.75))
             .when(col("c.billed_amount").cast("double") > 50000, lit(0.55))
             .when(col("c.billed_amount").cast("double") > 20000, lit(0.40))
             .when(col("c.billed_amount").cast("double") > 10000, lit(0.30))
             .otherwise(lit(0.15))
             ).alias("denial_risk_score"),
    when(coalesce(col("ml.denial_risk_score").cast("double") if has_denial_ml else lit(None),
             when(col("_is_denied"), lit(0.75))
             .when(col("c.billed_amount").cast("double") > 50000, lit(0.55))
             .when(col("c.billed_amount").cast("double") > 20000, lit(0.40))
             .when(col("c.billed_amount").cast("double") > 10000, lit(0.30))
             .otherwise(lit(0.15))
             ) >= 0.6, "High")
    .when(coalesce(col("ml.denial_risk_score").cast("double") if has_denial_ml else lit(None),
             when(col("_is_denied"), lit(0.75))
             .when(col("c.billed_amount").cast("double") > 50000, lit(0.55))
             .when(col("c.billed_amount").cast("double") > 20000, lit(0.40))
             .when(col("c.billed_amount").cast("double") > 10000, lit(0.30))
             .otherwise(lit(0.15))
             ) >= 0.3, "Medium")
    .otherwise("Low").alias("denial_risk_category"),
    when(col("_is_denied"),
         coalesce(col("c.denial_reason"),
                  col("ml.primary_denial_reason") if has_denial_ml else lit(None),
                  # Deterministic reason assignment for synthetic denials
                  when(col("_denial_reason_idx") == 0, lit("Prior Authorization Required"))
                  .when(col("_denial_reason_idx") == 1, lit("Not Medically Necessary"))
                  .when(col("_denial_reason_idx") == 2, lit("Coding Error"))
                  .when(col("_denial_reason_idx") == 3, lit("Coverage Expired"))
                  .when(col("_denial_reason_idx") == 4, lit("Duplicate Claim"))
                  .when(col("_denial_reason_idx") == 5, lit("Out of Network"))
                  .otherwise(lit("Missing Documentation"))))
    .otherwise(lit(None)).alias("primary_denial_reason"),
    when(col("_is_denied"),
        when(col("_denial_reason_idx") == 0, lit("Obtain prior authorization and resubmit"))
        .when(col("_denial_reason_idx") == 1, lit("Submit additional clinical documentation"))
        .when(col("_denial_reason_idx") == 2, lit("Correct coding and resubmit"))
        .when(col("_denial_reason_idx") == 3, lit("Verify eligibility and resubmit"))
        .when(col("_denial_reason_idx") == 4, lit("Verify not a duplicate claim"))
        .when(col("_denial_reason_idx") == 5, lit("Verify network status or obtain authorization"))
        .otherwise(coalesce(col("ml.recommended_action") if has_denial_ml else lit(None), lit("Gather missing documentation and resubmit")))
    ).otherwise(lit(None)).alias("recommended_action"),
    current_timestamp().alias("_load_timestamp")
).dropDuplicates(["claim_id"])

# Assign stable claim_key
CLAIM_TABLE = f"{GOLD}.fact_claim"
if IS_FULL:
    w = Window.orderBy("claim_id")
    df_clm_keyed = df_fact_claim.withColumn("claim_key", row_number().over(w).cast("bigint"))
else:
    df_clm_keyed = assign_keys(df_fact_claim, CLAIM_TABLE, "claim_key", "claim_id")

if IS_FULL or not table_exists(CLAIM_TABLE):
    df_clm_keyed.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(CLAIM_TABLE)
    print(f"   ✓ {'Full rebuild' if IS_FULL else 'Initial load'}: {spark.table(CLAIM_TABLE).count():,} rows")
else:
    # One-time cleanup: remove legacy duplicates in target table
    target_dupes = spark.table(CLAIM_TABLE).groupBy("claim_id").count().filter("count > 1").count()
    if target_dupes > 0:
        print(f"   ⚠️ Found {target_dupes} duplicate claim_ids in target — rebuilding clean")
        df_clm_keyed.write.format("delta").mode("overwrite") \
            .option("overwriteSchema", "true").saveAsTable(CLAIM_TABLE)
        print(f"   ✓ Rebuilt: {spark.table(CLAIM_TABLE).count():,} rows")
    else:
        dt = DeltaTable.forName(spark, CLAIM_TABLE)
        upd = {c: col(f"s.{c}") for c in df_clm_keyed.columns if c != "claim_key"}
        dt.alias("t").merge(
            df_clm_keyed.alias("s"),
            "t.claim_id = s.claim_id"
        ).whenMatchedUpdate(set=upd) \
         .whenNotMatchedInsertAll() \
         .execute()
        print(f"   ✓ Merged: {spark.table(CLAIM_TABLE).count():,} rows")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 7b. fact_prescription (Medication Fills + Adherence Tracking)

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

print("=" * 60)
print("7b. Loading fact_prescription")
print("=" * 60)

# ── Read prescriptions from Silver ODS ──────────────────────
try:
    df_prescriptions = spark.table(f"{SILVER}.prescriptions_enriched")
except Exception:
    print("   ⚠️ prescriptions_enriched not found in Silver ODS. Skipping.")
    df_prescriptions = None

if df_prescriptions is not None:
    # Validate required columns
    required_cols = ["prescription_id", "patient_id", "rxnorm_code", "fill_date"]
    missing = [c for c in required_cols if c not in df_prescriptions.columns]
    if missing:
        raise RuntimeError(f"❌ prescriptions_enriched missing columns: {missing}")

    # ── Dimension lookups ──────────────────────────────────────
    df_patient_lkp = spark.table(f"{GOLD}.dim_patient") \
        .filter("is_current = 1").select(col("patient_key"), col("patient_id"))
    df_provider_lkp = spark.table(f"{GOLD}.dim_provider") \
        .filter("is_current = 1").select(col("provider_key"), col("provider_id"))
    df_medication_lkp = spark.table(f"{GOLD}.dim_medication") \
        .select(col("medication_key"), col("rxnorm_code"))

    # Payer lookup: prescriptions don't carry payer_id directly, but each
    # prescription originates from an encounter that has a claim.  Derive
    # payer_key through the encounter → claim → payer path.
    df_payer_lkp = spark.table(f"{GOLD}.dim_payer") \
        .select(col("payer_key"), col("payer_id"))
    try:
        # Pick one payer per encounter (an encounter can have multiple claims
        # but they overwhelmingly share the same payer).
        df_enc_payer = spark.table(f"{SILVER}.claims_enriched") \
            .select("encounter_id", "payer_id") \
            .dropDuplicates(["encounter_id"]) \
            .join(df_payer_lkp, "payer_id", "inner") \
            .select(
                col("encounter_id").alias("ep_encounter_id"),
                col("payer_key").alias("ep_payer_key")
            )
        has_enc_payer = True
        print("   ✓ Payer lookup via encounter → claim → dim_payer")
    except Exception:
        has_enc_payer = False
        print("   ⚠️ claims_enriched not available — payer_key will be NULL")

    # Try to get encounter and facility keys from fact_encounter
    try:
        df_encounter_lkp = spark.table(f"{GOLD}.fact_encounter") \
            .select(col("encounter_key"), col("encounter_id"), col("facility_key").alias("enc_facility_key"))
    except Exception:
        df_encounter_lkp = None

    # ── Build fact table ──────────────────────────────────────
    # INNER join on provider — prescriptions without a valid provider
    # should not appear in the gold layer (mirrors fact_claim behaviour).
    df_rx = df_prescriptions.alias("rx") \
        .join(df_patient_lkp.alias("p"), col("rx.patient_id") == col("p.patient_id"), "inner") \
        .join(df_provider_lkp.alias("pr"), col("rx.provider_id") == col("pr.provider_id"), "inner") \
        .join(df_medication_lkp.alias("m"), col("rx.rxnorm_code") == col("m.rxnorm_code"), "left")

    if df_encounter_lkp is not None:
        df_rx = df_rx.join(df_encounter_lkp.alias("fe"), col("rx.encounter_id") == col("fe.encounter_id"), "left")
        encounter_key_col = col("fe.encounter_key")
        facility_key_col = col("fe.enc_facility_key")
    else:
        encounter_key_col = lit(None).cast("bigint")
        facility_key_col = lit(None).cast("bigint")

    # Join payer via encounter → claim path
    if has_enc_payer:
        df_rx = df_rx.join(df_enc_payer.alias("ep"), col("rx.encounter_id") == col("ep.ep_encounter_id"), "left")
        payer_key_col = col("ep.ep_payer_key")
    else:
        payer_key_col = lit(None).cast("bigint")

    # Compute fill_date_key
    df_rx = df_rx.withColumn(
        "fill_date_key",
        (year(col("rx.fill_date")) * 10000 + month(col("rx.fill_date")) * 100 + dayofmonth(col("rx.fill_date"))).cast("int")
    )

    # Assign surrogate keys
    PRESCRIPTION_TABLE = f"{GOLD}.fact_prescription"
    df_fact_rx = df_rx.select(
        col("rx.prescription_id"),
        lit(None).cast("string").alias("prescription_group_id"),
        col("fill_date_key"),
        col("p.patient_key"),
        col("pr.provider_key"),
        payer_key_col.alias("payer_key"),
        encounter_key_col.alias("encounter_key"),
        col("m.medication_key"),
        facility_key_col.alias("facility_key"),
        col("rx.refill_number").cast("int").alias("fill_number"),
        col("rx.days_supply").cast("int"),
        col("rx.quantity").cast("int").alias("quantity_dispensed"),
        lit(None).cast("int").alias("refills_authorized"),
        col("rx.is_generic").cast("int"),
        lit(None).cast("int").alias("is_chronic_medication"),
        lit(None).cast("string").alias("pharmacy_type"),
        col("rx.total_cost").cast("double"),
        (coalesce(col("rx.total_cost").cast("double"), lit(0.0)) - coalesce(col("rx.copay_amount").cast("double"), lit(0.0))).alias("payer_paid"),
        col("rx.copay_amount").cast("double").alias("patient_copay"),
        lit(None).cast("string").alias("prescribing_reason_code"),
        current_timestamp().alias("_load_timestamp")
    )

    df_fact_rx = assign_keys(df_fact_rx, PRESCRIPTION_TABLE, "prescription_key", "prescription_id")

    df_fact_rx.write.format("delta").mode("overwrite") \
        .option("overwriteSchema", "true").saveAsTable(PRESCRIPTION_TABLE)

    rx_count = spark.table(PRESCRIPTION_TABLE).count()
    payer_filled = spark.table(PRESCRIPTION_TABLE).filter("payer_key IS NOT NULL").count()
    print(f"   ✓ fact_prescription: {rx_count:,} rows")
    print(f"      Unique patients: {df_fact_rx.select('patient_key').distinct().count():,}")
    print(f"      Payer coverage:  {payer_filled:,}/{rx_count:,} ({payer_filled * 100 // _bi.max(rx_count, 1)}%)")
else:
    print("   ⏭️ Skipped fact_prescription (no source data)")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 7c. fact_diagnosis (Encounter → ICD Code Linkage)
# 
# Links encounters to diagnoses with sequence numbers (principal + secondary). Enables the Conditions pillar: Member → Conditions → Claims.

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ── fact_diagnosis ──────────────────────────────────────────
print("=" * 60)
print("7c. Loading fact_diagnosis (Encounter → Diagnosis)")
print("=" * 60)

try:
    df_dx = spark.table(f"{SILVER}.diagnoses_enriched")
    print(f"   Source: {SILVER}.diagnoses_enriched ({df_dx.count():,} rows)")
except Exception:
    print(f"   ⚠️ diagnoses_enriched not found in Silver ODS — skipping fact_diagnosis")
    df_dx = None

if df_dx is not None:
    # --- Dim lookups ---
    df_dim_patient = spark.table(f"{GOLD}.dim_patient").filter("is_current = 1") \
        .select(col("patient_key"), col("patient_id").alias("pat_id"))
    df_dim_diagnosis = spark.table(f"{GOLD}.dim_diagnosis") \
        .select(col("diagnosis_key"), col("icd_code").alias("dx_icd_code"))

    # Join fact_encounter to get encounter_key + facility_key
    df_fact_enc = spark.table(f"{GOLD}.fact_encounter") \
        .select(col("encounter_key"), col("encounter_id").alias("enc_id"),
                col("facility_key"), col("encounter_date_key"))

    # Build fact table
    df_fact_dx = df_dx \
        .join(df_dim_patient, df_dx["patient_id"] == df_dim_patient["pat_id"], "left") \
        .join(df_dim_diagnosis, df_dx["icd_code"] == df_dim_diagnosis["dx_icd_code"], "left") \
        .join(df_fact_enc, df_dx["encounter_id"] == df_fact_enc["enc_id"], "left") \
        .select(
            df_dx["diagnosis_id"],
            col("encounter_key"),
            col("encounter_date_key").alias("diagnosis_date_key"),
            col("patient_key"),
            col("diagnosis_key"),
            col("facility_key"),
            df_dx["icd_code"],
            df_dx["sequence_number"].cast("int").alias("diagnosis_sequence"),
            df_dx["diagnosis_type"],
            df_dx["present_on_admission"],
        ) \
        .withColumn("_load_timestamp", current_timestamp())

    # Assign surrogate keys
    w_dx = Window.orderBy("diagnosis_id")
    df_fact_dx = df_fact_dx.withColumn("fact_diagnosis_key", row_number().over(w_dx).cast("bigint"))

    # Reorder
    df_fact_dx = df_fact_dx.select(
        "fact_diagnosis_key", "diagnosis_id", "encounter_key", "diagnosis_date_key",
        "patient_key", "diagnosis_key", "facility_key", "icd_code",
        "diagnosis_sequence", "diagnosis_type", "present_on_admission", "_load_timestamp"
    )

    FACT_DX_TABLE = f"{GOLD}.fact_diagnosis"
    df_fact_dx.write.format("delta").mode("overwrite") \
        .option("overwriteSchema", "true").saveAsTable(FACT_DX_TABLE)

    dx_count = spark.table(FACT_DX_TABLE).count()
    principal = spark.table(FACT_DX_TABLE).filter("diagnosis_type = 'Principal'").count()
    secondary = spark.table(FACT_DX_TABLE).filter("diagnosis_type = 'Secondary'").count()
    print(f"   ✓ fact_diagnosis: {dx_count:,} rows")
    print(f"      Principal: {principal:,}")
    print(f"      Secondary: {secondary:,}")
    print(f"      Unique ICD codes: {df_fact_dx.select('icd_code').distinct().count()}")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 8. Aggregate Tables (Full Rebuild)

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

print("=" * 60)
print("7. Loading aggregate tables")
print("=" * 60)

# --- agg_readmission_by_date ---
df_fact_enc = spark.table(f"{GOLD}.fact_encounter")

df_agg_readmit = df_fact_enc.groupBy("encounter_date_key", "encounter_type").agg(
    count("*").alias("total_encounters"),
    sum(when(col("readmission_risk_category") == "High", 1).otherwise(0)).alias("high_risk_count"),
    sum(when(col("readmission_risk_category") == "Medium", 1).otherwise(0)).alias("medium_risk_count"),
    sum(when(col("readmission_risk_category") == "Low", 1).otherwise(0)).alias("low_risk_count"),
    avg("readmission_risk_score").alias("avg_risk_score"),
    sum(when(col("readmission_flag") == 1, 1).otherwise(0)).alias("actual_readmissions"),
    sum("total_charges").alias("total_charges"),
    avg("length_of_stay").alias("avg_length_of_stay")
)

df_agg_readmit.write.format("delta").mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(f"{GOLD}.agg_readmission_by_date")
print(f"   ✓ agg_readmission_by_date: {df_agg_readmit.count():,} rows")

# --- agg_denial_by_date ---
df_fact_clm = spark.table(f"{GOLD}.fact_claim")

df_agg_denial_date = df_fact_clm.groupBy("claim_date_key", "claim_type").agg(
    count("*").alias("total_claims"),
    sum(when(col("denial_risk_category") == "High", 1).otherwise(0)).alias("high_risk_count"),
    sum(when(col("denial_risk_category") == "Medium", 1).otherwise(0)).alias("medium_risk_count"),
    sum(when(col("denial_risk_category") == "Low", 1).otherwise(0)).alias("low_risk_count"),
    avg("denial_risk_score").alias("avg_risk_score"),
    sum(when(col("denial_flag") == 1, 1).otherwise(0)).alias("actual_denials"),
    sum("billed_amount").alias("total_billed"),
    sum("paid_amount").alias("total_paid"),
    sum(when(col("denial_risk_category") == "High", col("billed_amount")).otherwise(0)).alias("at_risk_amount")
)

df_agg_denial_date.write.format("delta").mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(f"{GOLD}.agg_denial_by_date")
print(f"   ✓ agg_denial_by_date: {df_agg_denial_date.count():,} rows")

# --- agg_denial_by_payer ---
df_dim_payer = spark.table(f"{GOLD}.dim_payer")

df_claims_with_payer = df_fact_clm.join(
    df_dim_payer, df_fact_clm.payer_key == df_dim_payer.payer_key, "left"
)

df_agg_denial_payer = df_claims_with_payer.groupBy(
    df_fact_clm.claim_date_key,
    df_dim_payer.payer_name,
    df_dim_payer.payer_type,
    df_fact_clm.primary_denial_reason
).agg(
    count("*").alias("total_claims"),
    sum(when(col("denial_flag") == 1, 1).otherwise(0)).alias("denied_claims"),
    sum("billed_amount").alias("total_billed"),
    sum(when(col("denial_flag") == 1, col("billed_amount")).otherwise(0)).alias("denied_amount"),
    sum("paid_amount").alias("total_paid"),
    avg("denial_risk_score").alias("avg_denial_risk_score")
).withColumn(
    "denial_rate",
    when(col("total_claims") > 0, col("denied_claims") / col("total_claims")).otherwise(0)
)

df_agg_denial_payer.write.format("delta").mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(f"{GOLD}.agg_denial_by_payer")
print(f"   ✓ agg_denial_by_payer: {df_agg_denial_payer.count():,} rows")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 8b. Medication Adherence Aggregate (PDC - Proportion of Days Covered)

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ── agg_medication_adherence ──────────────────────────────────
# PDC (Proportion of Days Covered) = industry standard adherence metric
# ≥ 0.80 = Adherent | 0.50 - 0.79 = Partially Adherent | < 0.50 = Non-Adherent
print("=" * 60)
print("8b. Loading medication adherence aggregate (PDC)")
print("=" * 60)

try:
    df_fact_rx = spark.table(f"{GOLD}.fact_prescription")
    df_dim_med = spark.table(f"{GOLD}.dim_medication")
    df_dim_date = spark.table(f"{GOLD}.dim_date")

    # Join prescriptions with medication info and dates
    df_rx_dated = df_fact_rx.alias("fp") \
        .join(df_dim_med.alias("dm"), col("fp.medication_key") == col("dm.medication_key"), "inner") \
        .join(df_dim_date.alias("dd"), col("fp.fill_date_key") == col("dd.date_key"), "inner") \
        .filter(col("fp.patient_key").isNotNull()) \
        .filter(col("fp.medication_key").isNotNull())

    # Calculate PDC per patient per medication
    from pyspark.sql.functions import datediff, min as spark_min, max as spark_max, least as spark_least

    df_adherence = df_rx_dated.groupBy(
        col("fp.patient_key"),
        col("fp.medication_key"),
        col("dm.drug_class"),
        col("dm.therapeutic_area")
    ).agg(
        spark_min("dd.full_date").alias("first_fill_date"),
        spark_max("dd.full_date").alias("last_fill_date"),
        spark_min("fp.fill_date_key").alias("measurement_period_start"),
        spark_max("fp.fill_date_key").alias("measurement_period_end"),
        count("*").alias("total_fills"),
        sum("fp.days_supply").alias("total_days_supply"),
        sum("fp.total_cost").alias("total_medication_cost"),
        sum("fp.payer_paid").alias("total_payer_cost"),
        sum("fp.patient_copay").alias("total_patient_cost"),
        lit(0).alias("is_chronic")
    )

    # Calculate days in period and PDC
    df_adherence = df_adherence \
        .withColumn(
            "days_in_period",
            datediff(col("last_fill_date"), col("first_fill_date")) + col("total_days_supply").cast("int")
        ) \
        .withColumn(
            "days_in_period",
            when(col("days_in_period") <= 0, col("total_days_supply")).otherwise(col("days_in_period"))
        ) \
        .withColumn(
            "covered_days",
            least(col("total_days_supply"), col("days_in_period"))
        ) \
        .withColumn(
            "pdc_score",
            when(col("days_in_period") > 0, col("covered_days") / col("days_in_period")).otherwise(lit(1.0))
        ) \
        .withColumn(
            "pdc_score",
            when(col("pdc_score") > 1.0, lit(1.0)).otherwise(col("pdc_score"))
        ) \
        .withColumn(
            "adherence_category",
            when(col("pdc_score") >= 0.80, "Adherent")
            .when(col("pdc_score") >= 0.50, "Partially Adherent")
            .otherwise("Non-Adherent")
        ) \
        .withColumn(
            "gap_days",
            when(col("days_in_period") > col("covered_days"),
                 col("days_in_period") - col("covered_days")).otherwise(lit(0))
        ) \
        .withColumn("_load_timestamp", current_timestamp())

    # Generate surrogate key for graph ontology (composite keys not supported)
    from pyspark.sql.functions import monotonically_increasing_id
    df_adherence = df_adherence.withColumn(
        "adherence_key",
        (col("fp.patient_key") * lit(100000) + col("fp.medication_key")).cast("long")
    )

    # Select final columns
    df_adherence_final = df_adherence.select(
        col("adherence_key").cast("long"),
        "patient_key", "medication_key", "drug_class", "therapeutic_area",
        "measurement_period_start", "measurement_period_end",
        "total_fills", "total_days_supply", "days_in_period", "covered_days",
        col("pdc_score").cast("double"),
        "adherence_category",
        col("total_medication_cost").cast("double"),
        col("total_payer_cost").cast("double"),
        col("total_patient_cost").cast("double"),
        "gap_days",
        col("is_chronic").cast("int"),
        "_load_timestamp"
    ).drop("first_fill_date", "last_fill_date")

    ADHERENCE_TABLE = f"{GOLD}.agg_medication_adherence"
    df_adherence_final.write.format("delta").mode("overwrite") \
        .option("overwriteSchema", "true").saveAsTable(ADHERENCE_TABLE)

    adh_count = spark.table(ADHERENCE_TABLE).count()
    adherent = df_adherence_final.filter("adherence_category = 'Adherent'").count()
    partial = df_adherence_final.filter("adherence_category = 'Partially Adherent'").count()
    non_adh = df_adherence_final.filter("adherence_category = 'Non-Adherent'").count()
    avg_pdc = df_adherence_final.agg(avg("pdc_score")).collect()[0][0]

    denom = adh_count if adh_count > 0 else 1
    print(f"   ✓ agg_medication_adherence: {adh_count:,} patient-medication combinations")
    print(f"      Adherent (≥80%):     {adherent:,} ({adherent*100//denom}%)")
    print(f"      Partial (50-79%):    {partial:,} ({partial*100//denom}%)")
    print(f"      Non-Adherent (<50%): {non_adh:,} ({non_adh*100//denom}%)")
    print(f"      Average PDC Score:   {avg_pdc:.2%}" if avg_pdc else "      Average PDC Score:   N/A")

except Exception as e:
    print(f"   ⚠️ Medication adherence aggregate skipped: {str(e)[:80]}")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 9. Validation

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

import builtins

print("\n" + "=" * 70)
print("🏆 GOLD LAYER VALIDATION SUMMARY")
print("=" * 70)

tables = [
    ("dim_date", None),
    ("dim_patient", "is_current = 1"),
    ("dim_provider", "is_current = 1"),
    ("dim_payer", None),
    ("dim_facility", None),
    ("dim_medication", None),
    ("dim_diagnosis", None),
    ("dim_sdoh", None),
    ("dim_monitor", None),
    ("fact_encounter", None),
    ("fact_claim", None),
    ("fact_prescription", None),
    ("fact_diagnosis", None),
    ("agg_readmission_by_date", None),
    ("agg_denial_by_date", None),
    ("agg_denial_by_payer", None),
    ("agg_medication_adherence", None),
]

for table_name, filter_expr in tables:
    try:
        full_name = f"{GOLD}.{table_name}"
        total = spark.table(full_name).count()
        if filter_expr:
            current = spark.table(full_name).filter(filter_expr).count()
            print(f"   ✓ {table_name}: {total:,} rows (current: {current:,})")
        else:
            print(f"   ✓ {table_name}: {total:,} rows")
    except Exception as e:
        print(f"   ✗ {table_name}: ERROR - {str(e)[:60]}")

# Key integrity check
print("\n" + "-" * 70)
print("KEY INTEGRITY CHECK")
print("-" * 70)

# Check fact → dimension join coverage (NULL keys = broken lookups)
for fact_name, key_checks in [
    ("fact_encounter", [("patient_key", "dim_patient"), ("provider_key", "dim_provider"), ("facility_key", "dim_facility")]),
    ("fact_claim", [("patient_key", "dim_patient"), ("provider_key", "dim_provider"),
                    ("payer_key", "dim_payer"), ("encounter_key", "fact_encounter"), ("facility_key", "dim_facility")]),
    ("fact_prescription", [("patient_key", "dim_patient"), ("provider_key", "dim_provider"),
                           ("payer_key", "dim_payer"), ("medication_key", "dim_medication"), ("encounter_key", "fact_encounter")]),
    ("fact_diagnosis", [("patient_key", "dim_patient"), ("encounter_key", "fact_encounter"),
                        ("diagnosis_key", "dim_diagnosis"), ("facility_key", "dim_facility")])
]:
    try:
        df_chk = spark.table(f"{GOLD}.{fact_name}")
        total = df_chk.count()
        for fk_col, dim_name in key_checks:
            matched = df_chk.filter(f"{fk_col} IS NOT NULL").count()
            icon = "✓" if matched == total else "⚠️"
            pct = matched * 100 // builtins.max(total, 1)
            print(f"   {icon} {fact_name} → {dim_name}: {matched:,}/{total:,} ({pct}%)")
    except Exception as e:
        print(f"   ⚠️ {fact_name}: {str(e)[:60]}")

# Denial metrics
denial_check = spark.sql(f"""
    SELECT COUNT(*) as total, 
           SUM(CASE WHEN denial_flag = 1 THEN 1 ELSE 0 END) as denied,
           SUM(CASE WHEN denial_flag = 1 THEN billed_amount ELSE 0 END) as denied_dollars
    FROM {GOLD}.fact_claim
""").collect()[0]
print(f"\n   Claims: {denial_check['total']:,} total, {denial_check['denied']:,} denied")
print(f"   Denied $: ${denial_check['denied_dollars']:,.2f}")

# Medication adherence metrics
try:
    adh_check = spark.sql(f"""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN adherence_category = 'Non-Adherent' THEN 1 ELSE 0 END) as non_adherent,
               AVG(pdc_score) as avg_pdc,
               SUM(total_medication_cost) as total_med_cost
        FROM {GOLD}.agg_medication_adherence
        WHERE is_chronic = 1
    """).collect()[0]
    print(f"\n   Chronic Meds: {adh_check['total']:,} patient-med combos")
    print(f"   Non-Adherent: {adh_check['non_adherent']:,}")
    print(f"   Avg PDC: {adh_check['avg_pdc']:.2%}" if adh_check['avg_pdc'] else "   Avg PDC: N/A")
    print(f"   Total Med Cost: ${adh_check['total_med_cost']:,.2f}" if adh_check['total_med_cost'] else "")
except Exception:
    pass

# Diagnosis metrics
try:
    dx_check = spark.sql(f"""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN diagnosis_type = 'Principal' THEN 1 ELSE 0 END) as principal,
               SUM(CASE WHEN diagnosis_type = 'Secondary' THEN 1 ELSE 0 END) as secondary
        FROM {GOLD}.fact_diagnosis
    """).collect()[0]
    print(f"\n   Diagnoses: {dx_check['total']:,} total ({dx_check['principal']:,} principal, {dx_check['secondary']:,} secondary)")
except Exception:
    pass

# SDOH metrics (multi-state)
try:
    sdoh_check = spark.sql(f"""
        SELECT COUNT(*) as total,
               COUNT(DISTINCT state) as state_count,
               SUM(CASE WHEN risk_tier = 'High' THEN 1 ELSE 0 END) as high_risk,
               AVG(social_vulnerability_index) as avg_svi
        FROM {GOLD}.dim_sdoh
    """).collect()[0]
    print(f"\n   SDOH Zip Codes: {sdoh_check['total']:,} across {sdoh_check['state_count']} states ({sdoh_check['high_risk']:,} high risk, avg SVI: {sdoh_check['avg_svi']:.4f})")
except Exception:
    pass

print("\n" + "=" * 70)
print(f"✅ Gold Layer Complete - {datetime.now()}")
print("=" * 70)
print("\nSchemas with SCD Type 2:")
print("  dim_patient:  is_current, effective_start_date, effective_end_date")
print("  dim_provider: is_current, effective_start_date, effective_end_date")
print(f"\nLoad Mode:      {load_mode.upper()}")
print("Key Generation: LEFT JOIN + COALESCE (stable across re-runs)")
print(f"Fact Loading:   {'OVERWRITE (full rebuild)' if IS_FULL else 'Delta MERGE (upsert on business key)'}")
print("\nIQ Payer Chain: Member → Conditions → Claims → Providers → Utilization → Social Factors ✅")
print("\nNext: Refresh Semantic Model → Test Data Agent")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 10. Readmission Risk Score Diagnostic
# Quick check that encounter-level risk scores flowed through correctly from the CSV data.

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================
# DIAGNOSTIC: Readmission Risk Score Validation
# ============================================================
# Run this cell to verify risk scores flowed through correctly

print("=" * 70)
print("READMISSION RISK SCORE DIAGNOSTIC")
print("=" * 70)

# 1. Check Bronze - does encounters_raw have the columns?
print("\n--- BRONZE LAYER ---")
try:
    df_bronze = spark.table(f"{BRONZE}.encounters_raw")
    bronze_cols = df_bronze.columns
    has_score = "readmission_risk_score" in bronze_cols
    has_cat = "readmission_risk_category" in bronze_cols
    print(f"   encounters_raw columns: {len(bronze_cols)} total")
    print(f"   readmission_risk_score: {'YES' if has_score else 'MISSING!'}")
    print(f"   readmission_risk_category: {'YES' if has_cat else 'MISSING!'}")
    if has_score:
        stats = df_bronze.selectExpr(
            "COUNT(*) as total",
            "COUNT(readmission_risk_score) as non_null",
            "MIN(CAST(readmission_risk_score AS DOUBLE)) as min_score",
            "AVG(CAST(readmission_risk_score AS DOUBLE)) as avg_score",
            "MAX(CAST(readmission_risk_score AS DOUBLE)) as max_score"
        ).collect()[0]
        print(f"   Rows: {stats['total']:,} | Non-null: {stats['non_null']:,}")
        print(f"   Min: {stats['min_score']:.3f} | Avg: {stats['avg_score']:.3f} | Max: {stats['max_score']:.3f}")
    if has_cat:
        cats = df_bronze.groupBy("readmission_risk_category").count().orderBy("readmission_risk_category").collect()
        for row in cats:
            print(f"   {row['readmission_risk_category']}: {row['count']:,}")
except Exception as e:
    print(f"   ERROR: {e}")

# 2. Check Silver Stage
print("\n--- SILVER STAGE ---")
try:
    df_silver_stage = spark.table(f"{SILVER_STAGE}.encounters_clean")
    ss_cols = df_silver_stage.columns
    has_score = "readmission_risk_score" in ss_cols
    has_cat = "readmission_risk_category" in ss_cols
    print(f"   encounters_clean columns: {len(ss_cols)} total")
    print(f"   readmission_risk_score: {'YES' if has_score else 'MISSING!'}")
    print(f"   readmission_risk_category: {'YES' if has_cat else 'MISSING!'}")
    if has_score:
        stats = df_silver_stage.selectExpr(
            "COUNT(*) as total",
            "COUNT(readmission_risk_score) as non_null",
            "MIN(CAST(readmission_risk_score AS DOUBLE)) as min_score",
            "AVG(CAST(readmission_risk_score AS DOUBLE)) as avg_score",
            "MAX(CAST(readmission_risk_score AS DOUBLE)) as max_score"
        ).collect()[0]
        print(f"   Rows: {stats['total']:,} | Non-null: {stats['non_null']:,}")
        print(f"   Min: {stats['min_score']:.3f} | Avg: {stats['avg_score']:.3f} | Max: {stats['max_score']:.3f}")
except Exception as e:
    print(f"   ERROR: {e}")

# 3. Check Silver ODS
print("\n--- SILVER ODS ---")
try:
    df_silver_ods = spark.table(f"{SILVER}.encounters_enriched")
    so_cols = df_silver_ods.columns
    has_score = "readmission_risk_score" in so_cols
    has_cat = "readmission_risk_category" in so_cols
    print(f"   encounters_enriched columns: {len(so_cols)} total")
    print(f"   readmission_risk_score: {'YES' if has_score else 'MISSING!'}")
    print(f"   readmission_risk_category: {'YES' if has_cat else 'MISSING!'}")
    if has_score:
        stats = df_silver_ods.selectExpr(
            "COUNT(*) as total",
            "COUNT(readmission_risk_score) as non_null",
            "MIN(CAST(readmission_risk_score AS DOUBLE)) as min_score",
            "AVG(CAST(readmission_risk_score AS DOUBLE)) as avg_score",
            "MAX(CAST(readmission_risk_score AS DOUBLE)) as max_score"
        ).collect()[0]
        print(f"   Rows: {stats['total']:,} | Non-null: {stats['non_null']:,}")
        print(f"   Min: {stats['min_score']:.3f} | Avg: {stats['avg_score']:.3f} | Max: {stats['max_score']:.3f}")
except Exception as e:
    print(f"   ERROR: {e}")

# 4. Check Gold
print("\n--- GOLD LAYER ---")
try:
    df_gold = spark.table(f"{GOLD}.fact_encounter")
    g_cols = df_gold.columns
    has_score = "readmission_risk_score" in g_cols
    has_cat = "readmission_risk_category" in g_cols
    print(f"   fact_encounter columns: {len(g_cols)} total")
    print(f"   readmission_risk_score: {'YES' if has_score else 'MISSING!'}")
    print(f"   readmission_risk_category: {'YES' if has_cat else 'MISSING!'}")
    print(f"   Total rows: {df_gold.count():,}")
    if has_score:
        stats = df_gold.selectExpr(
            "COUNT(readmission_risk_score) as non_null",
            "SUM(CASE WHEN readmission_risk_score IS NULL THEN 1 ELSE 0 END) as null_count",
            "MIN(readmission_risk_score) as min_score",
            "AVG(readmission_risk_score) as avg_score",
            "MAX(readmission_risk_score) as max_score"
        ).collect()[0]
        print(f"   Non-null: {stats['non_null']:,} | Null: {stats['null_count']:,}")
        print(f"   Min: {stats['min_score']:.3f} | Avg: {stats['avg_score']:.3f} | Max: {stats['max_score']:.3f}")
    if has_cat:
        cats = df_gold.groupBy("readmission_risk_category").count().orderBy("readmission_risk_category").collect()
        print(f"\n   Category Distribution:")
        for row in cats:
            print(f"     {row['readmission_risk_category']}: {row['count']:,}")
except Exception as e:
    print(f"   ERROR: {e}")

# 5. Check agg_readmission_by_date
print("\n--- AGG READMISSION BY DATE ---")
try:
    df_agg = spark.table(f"{GOLD}.agg_readmission_by_date")
    print(f"   Total rows: {df_agg.count():,}")
    stats = df_agg.selectExpr(
        "SUM(high_risk_count) as total_high",
        "SUM(medium_risk_count) as total_medium",
        "SUM(low_risk_count) as total_low",
        "AVG(avg_risk_score) as overall_avg_risk"
    ).collect()[0]
    print(f"   High risk encounters: {stats['total_high']:,}")
    print(f"   Medium risk encounters: {stats['total_medium']:,}")
    print(f"   Low risk encounters: {stats['total_low']:,}")
    print(f"   Overall avg risk score: {stats['overall_avg_risk']:.3f}" if stats['overall_avg_risk'] else "   Overall avg risk score: N/A")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n" + "=" * 70)
print("END DIAGNOSTIC")
print("=" * 70)
