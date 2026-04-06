# Fabric notebook source

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# # Silver Stage: Data Cleaning and Validation
# 
# This notebook transforms Bronze raw data into Silver Stage cleaned data.
# 
# ## ⚠️ IMPORTANT: Set Default Lakehouse
# **Before running, set `lh_silver_stage` as the default lakehouse in the Fabric UI.**
# 
# Also attach `lh_bronze_raw` as an additional lakehouse (not default).
# 
# ## Data Flow
# ```
# lh_bronze_raw.patients_raw      →  patients_clean (default)
# lh_bronze_raw.providers_raw     →  providers_clean (default)
# lh_bronze_raw.encounters_raw    →  encounters_clean (default)
# lh_bronze_raw.claims_raw        →  claims_clean (default)
# lh_bronze_raw.prescriptions_raw →  prescriptions_clean (default)
# 
# lh_bronze_raw.diagnoses_raw     →  diagnoses_clean (default)```

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Configuration - use fully qualified table names for pipeline execution
# In Fabric, tables are in lakehouse.table format
BRONZE_LAKEHOUSE = "lh_bronze_raw"
BRONZE_SCHEMA = f"{BRONZE_LAKEHOUSE}"  # Tables schema

SILVER_LAKEHOUSE = "lh_silver_stage"
SILVER_SCHEMA = f"{SILVER_LAKEHOUSE}"  # Target schema

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from datetime import datetime

spark = SparkSession.builder.getOrCreate()
print(f"Spark version: {spark.version}")
print(f"Processing started at: {datetime.now()}")
print(f"\nSource: {BRONZE_SCHEMA}")
print(f"Target: {SILVER_SCHEMA}")

# Verify Bronze tables
print(f"\nBronze tables ({BRONZE_SCHEMA}):")
try:
    spark.sql(f"SHOW TABLES IN {BRONZE_SCHEMA}").show(truncate=False)
except Exception as e:
    print(f"Could not list tables: {e}")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 1. Clean Patients Data

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Read from Bronze using fully qualified table name
patients_raw = spark.sql(f"SELECT * FROM {BRONZE_SCHEMA}.patients_raw")
print(f"Bronze patients count: {patients_raw.count():,}")

# Clean and transform
patients_clean = patients_raw \
    .withColumn("first_name", initcap(trim(col("first_name")))) \
    .withColumn("last_name", initcap(trim(col("last_name")))) \
    .withColumn("gender", 
        when(upper(col("gender")).isin("M", "MALE"), "Male")
        .when(upper(col("gender")).isin("F", "FEMALE"), "Female")
        .otherwise("Unknown")
    ) \
    .withColumn("state", upper(trim(col("state")))) \
    .withColumn("zip_code", regexp_replace(col("zip_code"), "[^0-9]", "")) \
    .withColumn("phone", regexp_replace(col("phone"), "[^0-9]", "")) \
    .withColumn("email", lower(trim(col("email")))) \
    .withColumn("date_of_birth", to_date(col("date_of_birth"))) \
    .withColumn("_silver_load_timestamp", current_timestamp()) \
    .dropDuplicates(["patient_id"])

# Write to Silver lakehouse using fully qualified name
patients_clean.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(f"{SILVER_SCHEMA}.patients_clean")

print(f"✓ {SILVER_SCHEMA}.patients_clean: {patients_clean.count():,} rows")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 2. Clean Providers Data

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Read from Bronze
providers_raw = spark.sql(f"SELECT * FROM {BRONZE_SCHEMA}.providers_raw")
print(f"Bronze providers count: {providers_raw.count():,}")

# Clean and transform
providers_clean = providers_raw \
    .withColumn("first_name", initcap(trim(col("first_name")))) \
    .withColumn("last_name", initcap(trim(col("last_name")))) \
    .withColumn("specialty", initcap(trim(col("specialty")))) \
    .withColumn("department", initcap(trim(col("department")))) \
    .withColumn("npi", regexp_replace(col("npi").cast("string"), "[^0-9]", "")) \
    .withColumn("email", lower(trim(col("email")))) \
    .withColumn("hire_date", to_date(col("hire_date"))) \
    .withColumn("is_active", when(col("status") == "Active", True).otherwise(False)) \
    .withColumn("_silver_load_timestamp", current_timestamp()) \
    .dropDuplicates(["provider_id"])

# Write to Silver lakehouse using fully qualified name
providers_clean.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(f"{SILVER_SCHEMA}.providers_clean")

print(f"✓ {SILVER_SCHEMA}.providers_clean: {providers_clean.count():,} rows")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 3. Clean Encounters Data

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Read from Bronze
encounters_raw = spark.sql(f"SELECT * FROM {BRONZE_SCHEMA}.encounters_raw")
print(f"Bronze encounters count: {encounters_raw.count():,}")
print("Columns:", encounters_raw.columns)

# Clean and transform (admit_date from Bronze → encounter_date alias for downstream)
encounters_clean = encounters_raw \
    .withColumn("encounter_type", initcap(trim(col("encounter_type")))) \
    .withColumn("admission_type", initcap(trim(col("admission_type")))) \
    .withColumn("discharge_disposition", initcap(trim(col("discharge_disposition")))) \
    .withColumn("encounter_date", to_date(col("admit_date"))) \
    .withColumn("discharge_date", to_date(col("discharge_date"))) \
    .withColumn("length_of_stay", 
        when(col("discharge_date").isNotNull() & col("encounter_date").isNotNull(),
             datediff(col("discharge_date"), col("encounter_date")))
        .otherwise(col("length_of_stay"))
    ) \
    .withColumn("total_charges", col("total_charges").cast("decimal(18,2)")) \
    .withColumn("readmission_risk", col("readmission_risk").cast("double")) \
    .withColumn("_silver_load_timestamp", current_timestamp()) \
    .dropDuplicates(["encounter_id"])

# Write to Silver lakehouse using fully qualified name
encounters_clean.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(f"{SILVER_SCHEMA}.encounters_clean")

print(f"✓ {SILVER_SCHEMA}.encounters_clean: {encounters_clean.count():,} rows")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 4. Clean Claims Data

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Read from Bronze
claims_raw = spark.sql(f"SELECT * FROM {BRONZE_SCHEMA}.claims_raw")
print(f"Bronze claims count: {claims_raw.count():,}")
print("Columns:", claims_raw.columns)

# Clean and transform (submit_date → claim_date, process_date → payment_date for downstream)
claims_clean = claims_raw \
    .withColumn("claim_type", initcap(trim(col("claim_type")))) \
    .withColumn("claim_status", initcap(trim(col("claim_status")))) \
    .withColumn("service_date", to_date(col("service_date"))) \
    .withColumn("claim_date", to_date(col("submit_date"))) \
    .withColumn("payment_date", to_date(col("process_date"))) \
    .withColumn("billed_amount", col("billed_amount").cast("decimal(18,2)")) \
    .withColumn("allowed_amount", col("allowed_amount").cast("decimal(18,2)")) \
    .withColumn("paid_amount", col("paid_amount").cast("decimal(18,2)")) \
    .withColumn("_silver_load_timestamp", current_timestamp()) \
    .dropDuplicates(["claim_id"])

# Write to Silver lakehouse using fully qualified name
claims_clean.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(f"{SILVER_SCHEMA}.claims_clean")

print(f"✓ {SILVER_SCHEMA}.claims_clean: {claims_clean.count():,} rows")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 5. Clean Prescriptions Data

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Read from Bronze
prescriptions_raw = spark.sql(f"SELECT * FROM {BRONZE_SCHEMA}.prescriptions_raw")
print(f"Bronze prescriptions count: {prescriptions_raw.count():,}")
print("Columns:", prescriptions_raw.columns)

# Clean and transform (only columns that exist in Bronze)
prescriptions_clean = prescriptions_raw \
    .withColumn("medication_name", initcap(trim(col("medication_name")))) \
    .withColumn("fill_date", to_date(col("fill_date"))) \
    .withColumn("days_supply", col("days_supply").cast("int")) \
    .withColumn("quantity", col("quantity").cast("int")) \
    .withColumn("refill_number", col("refill_number").cast("int")) \
    .withColumn("is_generic", col("is_generic").cast("int")) \
    .withColumn("total_cost", col("total_cost").cast("decimal(18,2)")) \
    .withColumn("copay_amount", col("copay_amount").cast("decimal(18,2)")) \
    .withColumn("_silver_load_timestamp", current_timestamp()) \
    .dropDuplicates(["prescription_id"])

# Write to Silver lakehouse
prescriptions_clean.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(f"{SILVER_SCHEMA}.prescriptions_clean")

print(f"✓ {SILVER_SCHEMA}.prescriptions_clean: {prescriptions_clean.count():,} rows")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 6. Clean Diagnoses Data

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Read from Bronze
diagnoses_raw = spark.sql(f"SELECT * FROM {BRONZE_SCHEMA}.diagnoses_raw")
print(f"Bronze diagnoses count: {diagnoses_raw.count():,}")
print("Columns:", diagnoses_raw.columns)

# Clean and transform (sequence_number from Bronze, no created_date/modified_date)
diagnoses_clean = diagnoses_raw \
    .withColumn("icd_code", upper(trim(col("icd_code")))) \
    .withColumn("diagnosis_type", initcap(trim(col("diagnosis_type")))) \
    .withColumn("present_on_admission", upper(trim(col("present_on_admission")))) \
    .withColumn("sequence_number", col("sequence_number").cast("int")) \
    .withColumn("diagnosis_date", to_date(col("diagnosis_date"))) \
    .withColumn("_silver_load_timestamp", current_timestamp()) \
    .dropDuplicates(["diagnosis_id"])

# Write to Silver lakehouse
diagnoses_clean.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(f"{SILVER_SCHEMA}.diagnoses_clean")

print(f"✓ {SILVER_SCHEMA}.diagnoses_clean: {diagnoses_clean.count():,} rows")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 7. Verify Silver Tables

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

print("="*60)
print("SILVER STAGE PROCESSING COMPLETE")
print("="*60)

# Show tables in Silver lakehouse using fully qualified names
print(f"\nSilver Stage Tables ({SILVER_SCHEMA}):")
try:
    spark.sql(f"SHOW TABLES IN {SILVER_SCHEMA}").show(truncate=False)
except Exception as e:
    print(f"Could not list tables: {e}")

# Row counts using fully qualified names
print("\nRow Counts:")
try:
    print(f"  patients_clean:      {spark.sql(f'SELECT COUNT(*) FROM {SILVER_SCHEMA}.patients_clean').collect()[0][0]:,}")
    print(f"  providers_clean:     {spark.sql(f'SELECT COUNT(*) FROM {SILVER_SCHEMA}.providers_clean').collect()[0][0]:,}")
    print(f"  encounters_clean:    {spark.sql(f'SELECT COUNT(*) FROM {SILVER_SCHEMA}.encounters_clean').collect()[0][0]:,}")
    print(f"  claims_clean:        {spark.sql(f'SELECT COUNT(*) FROM {SILVER_SCHEMA}.claims_clean').collect()[0][0]:,}")
    print(f"  prescriptions_clean: {spark.sql(f'SELECT COUNT(*) FROM {SILVER_SCHEMA}.prescriptions_clean').collect()[0][0]:,}")
    print(f"  diagnoses_clean:     {spark.sql(f'SELECT COUNT(*) FROM {SILVER_SCHEMA}.diagnoses_clean').collect()[0][0]:,}")
except Exception as e:
    print(f"Could not count tables: {e}")

print(f"\n✅ Processing completed at: {datetime.now()}")
