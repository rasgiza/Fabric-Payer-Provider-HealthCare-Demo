# Fabric notebook source

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# # Silver ODS: Enriched Operational Data Store
# 
# This notebook enriches Silver Stage data with reference data.
# 
# ## ⚠️ IMPORTANT: Set Default Lakehouse
# **Before running, set `lh_silver_ods` as the default lakehouse in the Fabric UI.**
# 
# Also attach:
# - `lh_bronze_raw` (for ref_ tables)
# - `lh_silver_stage` (for cleaned transactional data)
# 
# ## Data Flow
# ```
# lh_silver_stage.patients_clean + lh_bronze_raw.ref_*  →  patients_enriched (default)
# ```

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Configuration - use fully qualified table names for pipeline execution
BRONZE = "lh_bronze_raw"
SILVER_STAGE = "lh_silver_stage"
SILVER_ODS = "lh_silver_ods"  # Target schema

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from datetime import datetime

spark = SparkSession.builder.getOrCreate()
print(f"Spark version: {spark.version}")
print(f"Processing started at: {datetime.now()}")
print(f"\nSource (Bronze): {BRONZE}")
print(f"Source (Silver Stage): {SILVER_STAGE}")
print(f"Target (Silver ODS): {SILVER_ODS}")

# Verify tables
print(f"\nBronze tables:")
try:
    spark.sql(f"SHOW TABLES IN {BRONZE}").show(truncate=False)
except Exception as e:
    print(f"Could not list tables: {e}")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## Load Reference Data from Bronze

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Load reference tables from Bronze
ref_icd_codes = spark.sql(f"SELECT * FROM {BRONZE}.ref_icd_codes")
ref_cpt_codes = spark.sql(f"SELECT * FROM {BRONZE}.ref_cpt_codes")
ref_payers = spark.sql(f"SELECT * FROM {BRONZE}.ref_payers")
ref_facilities = spark.sql(f"SELECT * FROM {BRONZE}.ref_facilities")
ref_medications = spark.sql(f"SELECT * FROM {BRONZE}.ref_medications")

print("Reference Data Loaded:")
print(f"  ICD Codes:    {ref_icd_codes.count():,}")
print(f"  CPT Codes:    {ref_cpt_codes.count():,}")
print(f"  Payers:       {ref_payers.count():,}")
print(f"  Facilities:   {ref_facilities.count():,}")
print(f"  Medications:  {ref_medications.count():,}")

# Show ref_facilities schema

print("\nref_facilities columns:")
ref_facilities.printSchema()

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## Load Cleaned Data from Silver Stage

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Load cleaned data from Silver Stage
patients_clean = spark.sql(f"SELECT * FROM {SILVER_STAGE}.patients_clean")
providers_clean = spark.sql(f"SELECT * FROM {SILVER_STAGE}.providers_clean")
encounters_clean = spark.sql(f"SELECT * FROM {SILVER_STAGE}.encounters_clean")
claims_clean = spark.sql(f"SELECT * FROM {SILVER_STAGE}.claims_clean")
prescriptions_clean = spark.sql(f"SELECT * FROM {SILVER_STAGE}.prescriptions_clean")
diagnoses_clean = spark.sql(f"SELECT * FROM {SILVER_STAGE}.diagnoses_clean")

print("Silver Stage Data Loaded:")
print(f"  patients_clean:      {patients_clean.count():,}")
print(f"  providers_clean:     {providers_clean.count():,}")
print(f"  encounters_clean:    {encounters_clean.count():,}")
print(f"  claims_clean:        {claims_clean.count():,}")
print(f"  prescriptions_clean: {prescriptions_clean.count():,}")
print(f"  diagnoses_clean:     {diagnoses_clean.count():,}")

# Show columns for debugging

print("\npatients_clean columns:", patients_clean.columns)
print("diagnoses_clean columns:", diagnoses_clean.columns)

print("providers_clean columns:", providers_clean.columns)
print("prescriptions_clean columns:", prescriptions_clean.columns)

print("encounters_clean columns:", encounters_clean.columns)
print("claims_clean columns:", claims_clean.columns)

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 1. Enrich Patients

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Add age calculation and risk stratification
patients_enriched = patients_clean \
    .withColumn("age", 
        floor(datediff(current_date(), col("date_of_birth")) / 365.25)
    ) \
    .withColumn("age_group",
        when(col("age") < 18, "Pediatric")
        .when(col("age") < 40, "Young Adult")
        .when(col("age") < 65, "Adult")
        .otherwise("Senior")
    ) \
    .withColumn("_ods_load_timestamp", current_timestamp())

# Write to Silver ODS using fully qualified name
patients_enriched.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(f"{SILVER_ODS}.patients_enriched")

print(f"✓ {SILVER_ODS}.patients_enriched: {patients_enriched.count():,} rows")
patients_enriched.groupBy("age_group").count().orderBy("age_group").show()

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 2. Enrich Providers

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Check if providers has facility_id column
if "facility_id" in providers_clean.columns:
    # Drop facility_name/facility_type if they already exist in source (from data gen)
    # to avoid COLUMN_ALREADY_EXISTS when joining with ref_facilities
    _prov = providers_clean
    for _col in ["facility_name", "facility_type"]:
        if _col in _prov.columns:
            _prov = _prov.drop(_col)
    # Join providers with facilities
    providers_enriched = _prov \
        .join(
            ref_facilities.select(
                col("id").alias("fac_id"),
                col("name").alias("facility_name"),
                col("type").alias("facility_type")
            ),
            _prov["facility_id"] == col("fac_id"),
            "left"
        ) \
        .drop("fac_id") \
        .withColumn("years_of_service",
            floor(datediff(current_date(), col("hire_date")) / 365.25)
        ) \
        .withColumn("_ods_load_timestamp", current_timestamp())
else:
    # No facility_id, just add calculated columns
    print("Note: providers_clean does not have facility_id column")
    providers_enriched = providers_clean
    if "facility_name" not in providers_enriched.columns:
        providers_enriched = providers_enriched.withColumn("facility_name", lit(None).cast("string"))
    if "facility_type" not in providers_enriched.columns:
        providers_enriched = providers_enriched.withColumn("facility_type", lit(None).cast("string"))
    providers_enriched = providers_enriched \
        .withColumn("years_of_service",
            floor(datediff(current_date(), col("hire_date")) / 365.25)
        ) \
        .withColumn("_ods_load_timestamp", current_timestamp())

# Write to Silver ODS using fully qualified name
providers_enriched.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(f"{SILVER_ODS}.providers_enriched")

print(f"✓ {SILVER_ODS}.providers_enriched: {providers_enriched.count():,} rows")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 3. Enrich Encounters

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Start with encounters_clean
encounters_enriched = encounters_clean

# Join with patients (always has patient_id)
encounters_enriched = encounters_enriched \
    .join(
        patients_clean.select("patient_id", "first_name", "last_name", "date_of_birth"),
        "patient_id",
        "left"
    ) \
    .withColumnRenamed("first_name", "patient_first_name") \
    .withColumnRenamed("last_name", "patient_last_name")

# Join with providers (always has provider_id)
encounters_enriched = encounters_enriched \
    .join(
        providers_clean.select("provider_id", "first_name", "last_name", "specialty"),
        "provider_id",
        "left"
    ) \
    .withColumnRenamed("first_name", "provider_first_name") \
    .withColumnRenamed("last_name", "provider_last_name")

# Join with facilities only if facility_id exists
if "facility_id" in encounters_clean.columns:
    encounters_enriched = encounters_enriched \
        .join(
            ref_facilities.select(
                col("id").alias("fac_id"),
                col("name").alias("facility_name"),
                col("type").alias("facility_type")
            ),
            encounters_clean["facility_id"] == col("fac_id"),
            "left"
        ) \
        .drop("fac_id")
else:
    print("Note: encounters_clean does not have facility_id column")
    encounters_enriched = encounters_enriched \
        .withColumn("facility_name", lit(None).cast("string")) \
        .withColumn("facility_type", lit(None).cast("string"))

# Add timestamp
encounters_enriched = encounters_enriched \
    .withColumn("_ods_load_timestamp", current_timestamp())

# Write to Silver ODS using fully qualified name
encounters_enriched.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(f"{SILVER_ODS}.encounters_enriched")

print(f"✓ {SILVER_ODS}.encounters_enriched: {encounters_enriched.count():,} rows")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 4. Enrich Claims

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Start with claims_clean
claims_enriched = claims_clean

# Join with payers only if payer_id exists
if "payer_id" in claims_clean.columns:
    claims_enriched = claims_enriched \
        .join(
            ref_payers.select(
                col("payer_id").alias("payer_id_ref"),
                col("payer_name"),
                col("payer_type")
            ),
            claims_clean["payer_id"] == col("payer_id_ref"),
            "left"
        ) \
        .drop("payer_id_ref")
else:
    print("Note: claims_clean does not have payer_id column")
    claims_enriched = claims_enriched \
        .withColumn("payer_name", lit(None).cast("string")) \
        .withColumn("payer_type", lit(None).cast("string"))

# Add calculated columns
claims_enriched = claims_enriched \
    .withColumn("payment_ratio",
        when(col("billed_amount") > 0, 
             round(col("paid_amount") / col("billed_amount"), 4))
        .otherwise(0)
    ) \
    .withColumn("claim_age_days",
        datediff(current_date(), col("claim_date"))
    ) \
    .withColumn("_ods_load_timestamp", current_timestamp())

# Write to Silver ODS using fully qualified name
claims_enriched.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(f"{SILVER_ODS}.claims_enriched")

print(f"✓ {SILVER_ODS}.claims_enriched: {claims_enriched.count():,} rows")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 5. Enrich Prescriptions

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Enrich prescriptions with medication reference data and provider info
prescriptions_enriched = prescriptions_clean

# Join with ref_medications for drug classification details
# Alias any columns that already exist in prescriptions_clean to avoid duplicates
if "medication_name" in ref_medications.columns:
    rx_cols = set(prescriptions_clean.columns)
    ref_med_select = [col("medication_name").alias("ref_med_name")]
    for c in ref_medications.columns:
        if c == "medication_name":
            continue
        if c in rx_cols:
            ref_med_select.append(col(c).alias(f"ref_{c}"))
        else:
            ref_med_select.append(col(c))
    prescriptions_enriched = prescriptions_enriched \
        .join(
            ref_medications.select(*ref_med_select),
            prescriptions_clean["medication_name"] == col("ref_med_name"),
            "left"
        ) \
        .drop("ref_med_name")

# Add calculated columns
prescriptions_enriched = prescriptions_enriched \
    .withColumn("cost_per_day",
        when(col("days_supply") > 0,
             round(col("total_cost") / col("days_supply"), 2))
        .otherwise(lit(0))
    ) \
    .withColumn("payer_coverage_pct",
        when((col("total_cost") > 0) & col("copay_amount").isNotNull(),
             round((col("total_cost") - col("copay_amount")) / col("total_cost"), 4))
        .otherwise(lit(0))
    ) \
    .withColumn("_ods_load_timestamp", current_timestamp())

# Write to Silver ODS
prescriptions_enriched.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(f"{SILVER_ODS}.prescriptions_enriched")

print(f"✓ {SILVER_ODS}.prescriptions_enriched: {prescriptions_enriched.count():,} rows")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 6. Enrich Diagnoses

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Enrich diagnoses with ICD code descriptions and encounter context
diagnoses_enriched = diagnoses_clean

# Join with ref_icd_codes for descriptions
icd_join_col = "icd_code" if "icd_code" in ref_icd_codes.columns else "code"
if icd_join_col in ref_icd_codes.columns:
    icd_select_cols = [col(icd_join_col).alias("ref_icd_code")]
    for c in ref_icd_codes.columns:
        if c != icd_join_col:
            icd_select_cols.append(col(c).alias(f"icd_{c}") if c in diagnoses_clean.columns else col(c))
    diagnoses_enriched = diagnoses_enriched \
        .join(
            ref_icd_codes.select(*icd_select_cols),
            diagnoses_clean["icd_code"] == col("ref_icd_code"),
            "left"
        ) \
        .drop("ref_icd_code")

# Join with encounters for context
diagnoses_enriched = diagnoses_enriched \
    .join(
        encounters_clean.select(
            col("encounter_id").alias("enc_id"),
            col("encounter_type"),
            col("facility_id")
        ),
        diagnoses_clean["encounter_id"] == col("enc_id"),
        "left"
    ) \
    .drop("enc_id")

# Add timestamp
diagnoses_enriched = diagnoses_enriched \
    .withColumn("_ods_load_timestamp", current_timestamp())

# Write to Silver ODS
diagnoses_enriched.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(f"{SILVER_ODS}.diagnoses_enriched")

print(f"✓ {SILVER_ODS}.diagnoses_enriched: {diagnoses_enriched.count():,} rows")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 7. Verify ODS Tables

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

print("="*60)
print("SILVER ODS PROCESSING COMPLETE")
print("="*60)

# Show tables in Silver ODS using fully qualified names
print(f"\nSilver ODS Tables ({SILVER_ODS}):")
try:
    spark.sql(f"SHOW TABLES IN {SILVER_ODS}").show(truncate=False)
except Exception as e:
    print(f"Could not list tables: {e}")

# Row counts using fully qualified names
print("\nRow Counts:")
try:
    print(f"  patients_enriched:      {spark.sql(f'SELECT COUNT(*) FROM {SILVER_ODS}.patients_enriched').collect()[0][0]:,}")
    print(f"  providers_enriched:     {spark.sql(f'SELECT COUNT(*) FROM {SILVER_ODS}.providers_enriched').collect()[0][0]:,}")
    print(f"  encounters_enriched:    {spark.sql(f'SELECT COUNT(*) FROM {SILVER_ODS}.encounters_enriched').collect()[0][0]:,}")
    print(f"  claims_enriched:        {spark.sql(f'SELECT COUNT(*) FROM {SILVER_ODS}.claims_enriched').collect()[0][0]:,}")
    print(f"  prescriptions_enriched: {spark.sql(f'SELECT COUNT(*) FROM {SILVER_ODS}.prescriptions_enriched').collect()[0][0]:,}")
    print(f"  diagnoses_enriched:     {spark.sql(f'SELECT COUNT(*) FROM {SILVER_ODS}.diagnoses_enriched').collect()[0][0]:,}")
except Exception as e:
    print(f"Could not count tables: {e}")

print(f"\n✅ Processing completed at: {datetime.now()}")
