# Fabric notebook source

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# # 🏆 Create Gold Lakehouse Tables
# 
# **Run this notebook ONCE to create empty Delta tables in `lh_gold_curated`**
# 
# ## Architecture
# ```
# ┌─────────────────────────────────────────────────────────────────────┐
# │                    COMPUTE (T-SQL Stored Procs)                     │
# │                      wh_gold_analytics                              │
# │   ┌─────────────────┐         ┌─────────────────┐                   │
# │   │ usp_Merge_Dim_* │  ───►   │  lh_gold_curated │                  │
# │   │ usp_Merge_Fact_*│  WRITE  │  (Lakehouse)     │                  │
# │   └─────────────────┘   TO    └─────────────────┘                   │
# └─────────────────────────────────────────────────────────────────────┘
#                                         │
#                                         ▼ (Direct Lake)
#                               ┌─────────────────────┐
#                               │   Power BI Report   │
#                               │   (Fastest Mode!)   │
#                               └─────────────────────┘
# ```
# 
# ## ⚠️ Prerequisites
# 1. Create a lakehouse named: `lh_gold_curated`
# 2. Set it as the default lakehouse for this notebook

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

from pyspark.sql import SparkSession
from pyspark.sql.types import *
from datetime import datetime

spark = SparkSession.builder.getOrCreate()
print(f"Creating Gold Lakehouse tables at: {datetime.now()}")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 1. ETL Process Log

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Process log table for monitoring ETL
spark.sql("""
    CREATE TABLE IF NOT EXISTS etl_process_log (
        process_name STRING,
        status STRING,
        records_processed INT,
        error_message STRING,
        log_timestamp TIMESTAMP
    )
    USING DELTA
""")
print("✓ etl_process_log created")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 2. Dimension Tables

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# dim_date
spark.sql("""
    CREATE TABLE IF NOT EXISTS dim_date (
        date_key INT,
        full_date DATE,
        day_of_week INT,
        day_name STRING,
        day_of_month INT,
        day_of_year INT,
        week_of_year INT,
        month_number INT,
        month_name STRING,
        quarter INT,
        year INT,
        is_weekend INT,
        is_holiday INT,
        fiscal_year INT,
        fiscal_quarter INT
    )
    USING DELTA
""")
print("✓ dim_date created")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# dim_patient (SCD Type 2)
spark.sql("""
    CREATE TABLE IF NOT EXISTS dim_patient (
        patient_key BIGINT,
        patient_id STRING,
        first_name STRING,
        last_name STRING,
        date_of_birth DATE,
        gender STRING,
        age INT,
        age_group STRING,
        address STRING,
        city STRING,
        state STRING,
        zip_code STRING,
        phone STRING,
        email STRING,
        insurance_type STRING,
        insurance_provider STRING,
        insurance_policy_number STRING,
        -- SCD Type 2 columns
        effective_start_date TIMESTAMP,
        effective_end_date TIMESTAMP,
        is_current INT,
        _load_timestamp TIMESTAMP
    )
    USING DELTA
""")
print("✓ dim_patient created")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# dim_provider (SCD Type 2)
spark.sql("""
    CREATE TABLE IF NOT EXISTS dim_provider (
        provider_key BIGINT,
        provider_id STRING,
        first_name STRING,
        last_name STRING,
        display_name STRING,
        npi_number STRING,
        specialty STRING,
        department STRING,
        facility_id STRING,
        is_active INT,
        -- SCD Type 2 columns
        effective_start_date TIMESTAMP,
        effective_end_date TIMESTAMP,
        is_current INT,
        _load_timestamp TIMESTAMP
    )
    USING DELTA
""")
print("✓ dim_provider created")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# dim_payer
spark.sql("""
    CREATE TABLE IF NOT EXISTS dim_payer (
        payer_key BIGINT,
        payer_id STRING,
        payer_name STRING,
        payer_type STRING,
        is_active INT,
        _load_timestamp TIMESTAMP
    )
    USING DELTA
""")
print("✓ dim_payer created")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# dim_facility
spark.sql("""
    CREATE TABLE IF NOT EXISTS dim_facility (
        facility_key BIGINT,
        facility_id STRING,
        facility_name STRING,
        facility_type STRING,
        city STRING,
        state STRING,
        bed_count INT,
        is_active INT,
        _load_timestamp TIMESTAMP
    )
    USING DELTA
""")
print("✓ dim_facility created")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# dim_monitor (Ontology PatientMonitor entity - static device data)
spark.sql("""
    CREATE TABLE IF NOT EXISTS dim_monitor (
        monitor_key BIGINT,
        device_id STRING,
        device_type STRING,
        device_model STRING,
        location_id STRING,
        unit_name STRING,
        floor_number INT,
        building STRING,
        facility_id STRING,
        -- Surrogate FK columns for ontology relationships
        patient_key BIGINT,
        facility_key BIGINT,
        location_key BIGINT,
        is_active INT,
        _load_timestamp TIMESTAMP
    )
    USING DELTA
""")
print("✓ dim_monitor created")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# dim_medication (Type 1 - RxNorm reference data)
spark.sql("""
    CREATE TABLE IF NOT EXISTS dim_medication (
        medication_key BIGINT,
        rxnorm_code STRING,
        medication_name STRING,
        generic_name STRING,
        drug_class STRING,
        therapeutic_area STRING,
        route STRING,
        form STRING,
        strength STRING,
        is_chronic INT,
        is_active INT,
        _load_timestamp TIMESTAMP
    )
    USING DELTA
""")
print("✓ dim_medication created")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# dim_diagnosis (Type 1 - ICD-10 code reference)
spark.sql("""
    CREATE TABLE IF NOT EXISTS dim_diagnosis (
        diagnosis_key BIGINT,
        icd_code STRING,
        icd_description STRING,
        icd_category STRING,
        is_chronic INT,
        is_active INT,
        _load_timestamp TIMESTAMP
    )
    USING DELTA
""")
print("✓ dim_diagnosis created")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# dim_sdoh (Type 1 - Social Determinants of Health by zip code)
spark.sql("""
    CREATE TABLE IF NOT EXISTS dim_sdoh (
        sdoh_key BIGINT,
        zip_code STRING,
        state STRING,
        poverty_rate DOUBLE,
        food_desert_flag INT,
        transportation_score DOUBLE,
        housing_instability_rate DOUBLE,
        uninsured_rate DOUBLE,
        broadband_access_pct DOUBLE,
        median_household_income INT,
        population INT,
        social_vulnerability_index DOUBLE,
        risk_tier STRING,
        is_active INT,
        _load_timestamp TIMESTAMP
    )
    USING DELTA
""")
print("✓ dim_sdoh created")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 3. Fact Tables

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# fact_encounter
spark.sql("""
    CREATE TABLE IF NOT EXISTS fact_encounter (
        encounter_key BIGINT,
        encounter_id STRING,
        encounter_date_key INT,
        discharge_date_key INT,
        patient_key BIGINT,
        provider_key BIGINT,
        facility_key BIGINT,
        encounter_type STRING,
        admission_type STRING,
        discharge_disposition STRING,
        length_of_stay INT,
        total_charges DOUBLE,
        total_cost DOUBLE,
        readmission_flag INT,
        -- ML Predictions
        readmission_risk_score DOUBLE,
        readmission_risk_category STRING,
        _load_timestamp TIMESTAMP
    )
    USING DELTA
""")
print("✓ fact_encounter created")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# fact_claim
spark.sql("""
    CREATE TABLE IF NOT EXISTS fact_claim (
        claim_key BIGINT,
        claim_id STRING,
        claim_date_key INT,
        payment_date_key INT,
        patient_key BIGINT,
        provider_key BIGINT,
        payer_key BIGINT,
        encounter_key BIGINT,
        facility_key BIGINT,
        claim_type STRING,
        claim_status STRING,
        billed_amount DOUBLE,
        allowed_amount DOUBLE,
        paid_amount DOUBLE,
        denial_flag INT,
        -- ML Predictions
        denial_risk_score DOUBLE,
        denial_risk_category STRING,
        primary_denial_reason STRING,
        recommended_action STRING,
        _load_timestamp TIMESTAMP
    )
    USING DELTA
""")
print("✓ fact_claim created")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# fact_prescription (medication fills with adherence tracking)
spark.sql("""
    CREATE TABLE IF NOT EXISTS fact_prescription (
        prescription_key BIGINT,
        prescription_id STRING,
        prescription_group_id STRING,
        fill_date_key INT,
        patient_key BIGINT,
        provider_key BIGINT,
        payer_key BIGINT,
        encounter_key BIGINT,
        medication_key BIGINT,
        facility_key BIGINT,
        fill_number INT,
        days_supply INT,
        quantity_dispensed INT,
        refills_authorized INT,
        is_generic INT,
        is_chronic_medication INT,
        pharmacy_type STRING,
        total_cost DOUBLE,
        payer_paid DOUBLE,
        patient_copay DOUBLE,
        prescribing_reason_code STRING,
        _load_timestamp TIMESTAMP
    )
    USING DELTA
""")
print("✓ fact_prescription created")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# fact_diagnosis (encounter → ICD code linkage)
spark.sql("""
    CREATE TABLE IF NOT EXISTS fact_diagnosis (
        fact_diagnosis_key BIGINT,
        diagnosis_id STRING,
        encounter_key BIGINT,
        diagnosis_date_key INT,
        patient_key BIGINT,
        diagnosis_key BIGINT,
        facility_key BIGINT,
        icd_code STRING,
        diagnosis_sequence INT,
        diagnosis_type STRING,
        present_on_admission STRING,
        _load_timestamp TIMESTAMP
    )
    USING DELTA
""")
print("✓ fact_diagnosis created")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 4. Aggregate Tables

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# agg_readmission_by_date
spark.sql("""
    CREATE TABLE IF NOT EXISTS agg_readmission_by_date (
        encounter_date_key INT,
        encounter_type STRING,
        total_encounters INT,
        high_risk_count INT,
        medium_risk_count INT,
        low_risk_count INT,
        avg_risk_score DOUBLE,
        actual_readmissions INT,
        total_charges DOUBLE,
        avg_length_of_stay DOUBLE
    )
    USING DELTA
""")
print("✓ agg_readmission_by_date created")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# agg_denial_by_date
spark.sql("""
    CREATE TABLE IF NOT EXISTS agg_denial_by_date (
        claim_date_key INT,
        claim_type STRING,
        total_claims INT,
        high_risk_count INT,
        medium_risk_count INT,
        low_risk_count INT,
        avg_risk_score DOUBLE,
        actual_denials INT,
        total_billed DOUBLE,
        total_paid DOUBLE,
        at_risk_amount DOUBLE
    )
    USING DELTA
""")
print("✓ agg_denial_by_date created")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# agg_medication_adherence (PDC by patient + medication)
spark.sql("""
    CREATE TABLE IF NOT EXISTS agg_medication_adherence (
        adherence_key BIGINT,
        patient_key BIGINT,
        medication_key BIGINT,
        drug_class STRING,
        therapeutic_area STRING,
        measurement_period_start INT,
        measurement_period_end INT,
        total_fills INT,
        total_days_supply INT,
        days_in_period INT,
        covered_days INT,
        pdc_score DOUBLE,
        adherence_category STRING,
        total_medication_cost DOUBLE,
        total_payer_cost DOUBLE,
        total_patient_cost DOUBLE,
        gap_days INT,
        is_chronic INT,
        _load_timestamp TIMESTAMP
    )
    USING DELTA
""")
print("✓ agg_medication_adherence created")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 4b. Streaming Tables (Vitals / Alerts)

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# dim_location (Hospital location dimension for streaming data)
spark.sql("""
    CREATE TABLE IF NOT EXISTS dim_location (
        location_key BIGINT,
        location_id STRING,
        unit STRING,
        floor INT,
        building STRING,
        unit_type STRING,
        is_critical_care INT,
        created_at TIMESTAMP,
        updated_at TIMESTAMP
    )
    USING DELTA
""")
print("✓ dim_location created")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# fact_vitals (Hourly aggregated vital sign readings)
spark.sql("""
    CREATE TABLE IF NOT EXISTS fact_vitals (
        vitals_key BIGINT,
        patient_key BIGINT,
        date_key INT,
        hour_of_day INT,
        location_key BIGINT,
        avg_heart_rate DOUBLE,
        max_heart_rate INT,
        min_heart_rate INT,
        avg_bp_systolic DOUBLE,
        max_bp_systolic INT,
        avg_bp_diastolic DOUBLE,
        avg_spo2 DOUBLE,
        min_spo2 INT,
        avg_temperature DOUBLE,
        max_temperature DOUBLE,
        avg_respiratory_rate DOUBLE,
        avg_risk_score DOUBLE,
        max_risk_score INT,
        risk_flag STRING,
        critical_reading_count INT,
        reading_count INT,
        created_at TIMESTAMP
    )
    USING DELTA
""")
print("✓ fact_vitals created")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# fact_alerts (Clinical alert records from streaming vitals)
spark.sql("""
    CREATE TABLE IF NOT EXISTS fact_alerts (
        alert_key BIGINT,
        alert_id STRING,
        vitals_id STRING,
        patient_key BIGINT,
        date_key INT,
        alert_hour INT,
        alert_datetime TIMESTAMP,
        location_key BIGINT,
        alert_code STRING,
        alert_description STRING,
        severity STRING,
        severity_rank INT,
        measured_value DOUBLE,
        threshold_value STRING,
        was_acknowledged INT,
        acknowledged_by STRING,
        acknowledged_at TIMESTAMP,
        response_time_minutes DOUBLE,
        created_at TIMESTAMP
    )
    USING DELTA
""")
print("✓ fact_alerts created")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## 5. Summary

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

print("="*70)
print("🏆 GOLD LAKEHOUSE TABLES CREATED")
print("="*70)

tables = spark.sql("SHOW TABLES").collect()
print(f"\nTotal tables: {len(tables)}")

print("\n📊 DIMENSION TABLES:")
for t in tables:
    if t['tableName'].startswith('dim_'):
        print(f"   • {t['tableName']}")

print("\n📈 FACT TABLES:")
for t in tables:
    if t['tableName'].startswith('fact_'):
        print(f"   • {t['tableName']}")

print("\n📊 AGGREGATE TABLES:")
for t in tables:
    if t['tableName'].startswith('agg_'):
        print(f"   • {t['tableName']}")

print("\n" + "="*70)
print("NEXT STEPS:")
print("="*70)
print("1. Run the Warehouse stored procedures (02b_Stored_Procedures_Lakehouse_Target.sql)")
print("2. The procs will WRITE to these lh_gold_curated tables")
print("3. Connect Power BI using DIRECT LAKE to this lakehouse")
print("\n✅ Best of both worlds: T-SQL procs + Direct Lake performance!")
