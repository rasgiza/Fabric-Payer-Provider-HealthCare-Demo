# Fabric notebook source

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# # Bronze Layer - Data Ingest (CSV Source)
# 
# Loads CSV data into the Bronze Lakehouse — supports full and incremental modes.
# 
# ## ⚠️ IMPORTANT: Set Default Lakehouse
# **Before running manually, set `lh_bronze_raw` as the default lakehouse in the Fabric UI.**
# 
# ## Load Modes
# 
# | Mode | Source | Action | Use Case |
# |------|--------|--------|----------|
# | `full` | Base CSVs in `Files/` | Truncate & reload all tables | Initial load, data refresh |
# | `incremental` | Timestamped CSVs in `Files/incremental/` | Append new rows to existing tables | Daily/hourly updates |
# 
# ## Parameters (from Pipeline)
# - `load_mode` - "full" or "incremental" (default: full)

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Configuration and imports
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from datetime import datetime
import traceback

spark = SparkSession.builder.getOrCreate()

# ============================================================================
# Lakehouse configuration
# ============================================================================
BRONZE_LAKEHOUSE = "lh_bronze_raw"

# OneLake ABFSS path — MUST use lowercase .lakehouse extension
# Format: abfss://{workspace_name}@onelake.dfs.fabric.microsoft.com/{lakehouse_name}.lakehouse/Files/
# When running in Fabric with default lakehouse set, use the shorter relative path instead
BRONZE_SCHEMA = f"{BRONZE_LAKEHOUSE}"

# Use the relative Files/ path (works when default lakehouse is set)
# This avoids hardcoding workspace GUIDs and item type extensions
SOURCE_FILES_PATH = "Files/"

print(f"Bronze CSV Ingest started at: {datetime.now()}")
print(f"Target: {BRONZE_SCHEMA}")
print(f"Source: {SOURCE_FILES_PATH}")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Get parameters from pipeline (or use defaults for manual run)
try:
    load_mode = spark.conf.get("spark.load_mode", "full")
except:
    load_mode = "full"

# Validate load_mode
load_mode = load_mode.lower().strip()
if load_mode not in ["full", "incremental"]:
    print(f"Warning: Invalid load_mode '{load_mode}', defaulting to 'full'")
    load_mode = "full"

print(f"\n{'='*60}")
print(f"LOAD MODE: {load_mode.upper()}")
print(f"{'='*60}")

if load_mode == "full":
    print("→ Will read base CSVs from Files/")
    print("→ Will truncate and reload all tables (overwrite)")
else:
    print("→ Will read incremental CSVs from Files/incremental/")
    print("→ Will append new rows to existing Bronze tables")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## Table Configuration
# 
# Define the transactional and reference tables to load from CSV files.

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Table configuration
# Each table has:
#   - name: table name (will be stored as {name}_raw in Bronze)
#   - source_file: CSV filename in Files/ folder
#   - key_column: primary key column for reference
#   - raw_suffix (optional): if False table is saved as-is (e.g. ref_icd_codes)

# ── Transactional tables (stored as {name}_raw) ──────────────
TRANSACTIONAL_TABLES = [
    {"name": "patients",      "source_file": "patients.csv",      "key_column": "patient_id"},
    {"name": "providers",     "source_file": "providers.csv",     "key_column": "provider_id"},
    {"name": "encounters",    "source_file": "encounters.csv",    "key_column": "encounter_id"},
    {"name": "claims",        "source_file": "claims.csv",        "key_column": "claim_id"},
    {"name": "prescriptions", "source_file": "prescriptions.csv", "key_column": "prescription_id"},
    {"name": "diagnoses",     "source_file": "diagnoses.csv",     "key_column": "diagnosis_id"},
]

# ── Reference / metadata tables (stored as ref_{name}, NO _raw suffix) ──
REFERENCE_TABLES = [
    {"name": "ref_icd_codes",      "source_file": "metadata/icd_codes.csv",       "key_column": "icd_code",       "raw_suffix": False},
    {"name": "ref_cpt_codes",      "source_file": "metadata/cpt_codes.csv",       "key_column": "cpt_code",       "raw_suffix": False},
    {"name": "ref_payers",         "source_file": "metadata/payers.csv",          "key_column": "payer_id",       "raw_suffix": False},
    {"name": "ref_facilities",     "source_file": "metadata/facilities.csv",      "key_column": "facility_id",    "raw_suffix": False},
    {"name": "ref_medications",    "source_file": "metadata/medications_ref.csv", "key_column": "medication_name","raw_suffix": False},
    {"name": "ref_sdoh_zipcode",   "source_file": "metadata/sdoh_zipcode.csv",   "key_column": "zipcode",        "raw_suffix": False},
    {"name": "ref_monitors",       "source_file": "metadata/monitors.csv",        "key_column": "monitor_id",     "raw_suffix": False},
]

# Combined list drives the processing loop
TABLES_CONFIG = TRANSACTIONAL_TABLES + REFERENCE_TABLES

print(f"Transactional tables ({len(TRANSACTIONAL_TABLES)}): {[t['name'] for t in TRANSACTIONAL_TABLES]}")
print(f"Reference tables     ({len(REFERENCE_TABLES)}): {[t['name'] for t in REFERENCE_TABLES]}")
print(f"Total tables to process: {len(TABLES_CONFIG)}")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## Helper Functions

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

def load_full_csv(table_config):
    """
    Full Load: Read base CSV + any incremental CSVs.
    Used for initial load or data refresh.
    Returns a DataFrame with Bronze metadata columns.
    """
    table_name = table_config["name"]
    source_file = table_config["source_file"]
    base_path = f"{SOURCE_FILES_PATH}{source_file}"
    
    # Read the base CSV
    print(f"  Reading base CSV: {source_file}")
    df = spark.read.format("csv") \
        .option("header", "true") \
        .option("inferSchema", "true") \
        .load(base_path)
    
    df = df.withColumn("_bronze_load_timestamp", current_timestamp()) \
           .withColumn("_bronze_source", lit("full_load")) \
           .withColumn("_bronze_file", lit(source_file))
    
    base_count = df.count()
    print(f"    → {base_count:,} rows from base CSV")
    
    # Also pick up any incremental files (date subfolders + legacy flat files)
    incremental_path = f"{SOURCE_FILES_PATH}incremental/"
    try:
        incr_paths = [
            f"{incremental_path}{table_name}_*.csv",       # legacy flat
            f"{incremental_path}*/{table_name}_*.csv",     # date subfolders
        ]
        
        # Count matching files across both patterns
        matching_count = 0
        date_folders = set()
        try:
            for item in mssparkutils.fs.ls(incremental_path):
                if item.isDir:
                    try:
                        sub_files = mssparkutils.fs.ls(item.path)
                        sub_matching = [f.name for f in sub_files if f.name.startswith(f"{table_name}_") and f.name.endswith(".csv")]
                        matching_count += len(sub_matching)
                        if sub_matching:
                            date_folders.add(item.name)
                    except Exception:
                        pass
                elif item.name.startswith(f"{table_name}_") and item.name.endswith(".csv"):
                    matching_count += 1  # legacy flat file
        except Exception:
            pass
        
        if matching_count > 0:
            folder_info = f" from {len(date_folders)} date folder(s)" if date_folders else ""
            print(f"  Reading {matching_count} incremental file(s){folder_info}")
            
            df_incr = spark.read.format("csv") \
                .option("header", "true") \
                .option("inferSchema", "true") \
                .load(incr_paths)
            
            df_incr = df_incr.withColumn("_bronze_load_timestamp", current_timestamp()) \
                             .withColumn("_bronze_source", lit("full_load_incr")) \
                             .withColumn("_bronze_file", input_file_name())
            
            incr_count = df_incr.count()
            print(f"    → {incr_count:,} rows from incremental files")
            
            df = df.unionByName(df_incr, allowMissingColumns=True)
            print(f"    → {base_count + incr_count:,} total rows (base + incremental)")
    except Exception:
        pass  # No incremental folder — that's fine for full load
    
    return df


def load_incremental_csv(table_config):
    """
    Incremental Load: Read timestamped CSVs from Files/incremental/ date subfolders.
    Reads from both date subfolders (incremental/YYYY-MM-DD/*.csv) and legacy flat files.
    """
    table_name = table_config["name"]
    incremental_path = f"{SOURCE_FILES_PATH}incremental/"
    
    try:
        # Read from both legacy flat files and date subfolders
        incr_paths = [
            f"{incremental_path}{table_name}_*.csv",       # legacy flat
            f"{incremental_path}*/{table_name}_*.csv",     # date subfolders
        ]
        
        # Count matching files + discover date folders
        matching_files = []
        date_folders = set()
        try:
            for item in mssparkutils.fs.ls(incremental_path):
                if item.isDir:
                    try:
                        sub_files = mssparkutils.fs.ls(item.path)
                        for f in sub_files:
                            if f.name.startswith(f"{table_name}_") and f.name.endswith(".csv"):
                                matching_files.append(f"{item.name}/{f.name}")
                                date_folders.add(item.name)
                    except Exception:
                        pass
                elif item.name.startswith(f"{table_name}_") and item.name.endswith(".csv"):
                    matching_files.append(item.name)
        except Exception:
            pass
        
        if not matching_files:
            print(f"  No incremental files found for {table_name}")
            return None
        
        folder_info = f" from {len(date_folders)} date folder(s)" if date_folders else ""
        print(f"  Reading {len(matching_files)} incremental file(s){folder_info}")
        if date_folders:
            print(f"    Folders: {sorted(date_folders)}")
        
        df = spark.read.format("csv") \
            .option("header", "true") \
            .option("inferSchema", "true") \
            .load(incr_paths)
        
        df = df.withColumn("_bronze_load_timestamp", current_timestamp()) \
               .withColumn("_bronze_source", lit("incremental_csv")) \
               .withColumn("_bronze_file", input_file_name())
        
        row_count = df.count()
        print(f"    → {row_count:,} incremental rows")
        return df
        
    except Exception:
        print(f"  No incremental folder found — skipping {table_name}")
        return None


def save_to_bronze(df, table_name, mode="overwrite", table_config=None):
    """
    Save DataFrame to Bronze Delta table.
    - overwrite: replaces table AND schema (handles type mismatches from Copy Activity)
    - append: adds rows, merges schema if new columns appear
    """
    # Reference tables get saved as-is (ref_icd_codes); transactional get _raw suffix
    use_raw = table_config.get("raw_suffix", True) if (table_config and isinstance(table_config, dict)) else True
    full_table_name = f"{BRONZE_SCHEMA}.{table_name}_raw" if use_raw else f"{BRONZE_SCHEMA}.{table_name}"
    
    if mode == "overwrite":
        # Full load: overwrite both data AND schema
        # This avoids DELTA_FAILED_TO_MERGE_FIELDS when CSV schema differs
        # from existing table schema (e.g., Copy Activity created different types)
        df.write.format("delta") \
            .mode("overwrite") \
            .option("overwriteSchema", "true") \
            .saveAsTable(full_table_name)
    else:
        # Incremental: append rows, merge schema for any new columns
        df.write.format("delta") \
            .mode("append") \
            .option("mergeSchema", "true") \
            .saveAsTable(full_table_name)

    return spark.sql(f"SELECT COUNT(*) as cnt FROM {full_table_name}").collect()[0]["cnt"]

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## Verify Source Files
# 
# Check that CSV files are available in Files/ before processing.

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Verify source files are available
print(f"\nChecking source files ({load_mode} mode)...")
print("-" * 40)

try:
    files = mssparkutils.fs.ls(SOURCE_FILES_PATH)
    available_files = [f.name for f in files]
    print(f"Found {len(files)} items in Files/ folder:")
    for f in sorted(files, key=lambda x: x.name):
        print(f"  {'📁' if f.isDir else '📄'} {f.name}")
    
    # Also list metadata subfolder if it exists
    metadata_files = []
    if "metadata" in available_files:
        try:
            meta_items = mssparkutils.fs.ls(f"{SOURCE_FILES_PATH}metadata/")
            metadata_files = [f.name for f in meta_items if f.name.endswith(".csv")]
            print(f"\nMetadata folder: {len(metadata_files)} CSV(s)")
            for mf in sorted(metadata_files):
                print(f"    📄 {mf}")
        except Exception:
            print("\nMetadata folder: empty or inaccessible")
    
    # Verify required CSVs are present
    print(f"\nRequired files check:")
    all_present = True
    for tc in TABLES_CONFIG:
        src = tc["source_file"]
        if src.startswith("metadata/"):
            # Check in metadata subfolder
            fname = src.replace("metadata/", "")
            found = fname in metadata_files
        else:
            found = src in available_files
        
        if found:
            print(f"  ✓ {src}")
        else:
            print(f"  ✗ {src} — MISSING")
            all_present = False
    
    if not all_present and load_mode == "full":
        print("\n⚠️ WARNING: Some source CSVs are missing. Full load may fail for those tables.")
    
    # Check for incremental folder
    if "incremental" in available_files:
        try:
            incr_files = mssparkutils.fs.ls(f"{SOURCE_FILES_PATH}incremental/")
            csv_files = [f.name for f in incr_files if f.name.endswith(".csv")]
            print(f"\nIncremental folder: {len(csv_files)} CSV file(s) found")
            for cf in csv_files[:10]:
                print(f"    {cf}")
        except Exception:
            print("\nIncremental folder: empty or inaccessible")
    else:
        if load_mode == "incremental":
            print("\n⚠️ WARNING: No incremental/ folder found. Incremental load will have nothing to process.")
        else:
            print("\nIncremental folder: not present (OK for full load)")

except Exception as e:
    print(f"Error checking source files: {str(e)[:200]}")
    print("Make sure lh_bronze_raw is set as the default lakehouse for this notebook.")
    available_files = []

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## Process Tables
# 
# Read each CSV file and write to Bronze Delta tables.

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Process all tables based on load_mode
results = []

for table_config in TABLES_CONFIG:
    table_name = table_config["name"]
    
    print(f"\n{'='*60}")
    print(f"Processing: {table_name} ({load_mode.upper()})")
    print(f"{'='*60}")
    
    try:
        if load_mode == "full":
            # Full Load: Read base CSV + incremental, overwrite table
            df = load_full_csv(table_config)
            record_count = save_to_bronze(df, table_name, mode="overwrite", table_config=table_config)
            
        else:
            # Incremental: Read ONLY incremental CSVs, append to table
            df = load_incremental_csv(table_config)
            
            if df is not None:
                record_count = df.count()
                if record_count > 0:
                    save_to_bronze(df, table_name, mode="append", table_config=table_config)
                    print(f"  → Appended {record_count:,} new rows to Bronze")
                else:
                    print(f"  → Incremental file was empty")
                    record_count = 0
            else:
                print(f"  → No incremental files to process")
                record_count = 0
        
        print(f"✓ {table_name}: {record_count:,} records processed")
        results.append({
            "table": table_name, 
            "records": record_count, 
            "status": "success"
        })
        
    except Exception as e:
        print(f"✗ {table_name}: {str(e)[:200]}")
        results.append({
            "table": table_name, 
            "records": 0, 
            "status": "failed",
            "error": str(e)
        })

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## Archive Processed Incremental Files
# 
# After incremental processing, move files from `Files/incremental/` to `Files/processed/`
# so they are **not re-read** on subsequent incremental runs.  
# Full-load mode skips this step (it overwrites tables anyway).

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# Archive incremental files after processing
# Prevents duplicate rows when running incremental multiple times
# ============================================================================
if load_mode == "incremental":
    incremental_path = f"{SOURCE_FILES_PATH}incremental/"
    processed_path = f"{SOURCE_FILES_PATH}processed/"
    
    try:
        items = mssparkutils.fs.ls(incremental_path)
        archived_count = 0
        
        # Ensure processed directory exists
        try:
            mssparkutils.fs.mkdirs(processed_path)
        except Exception:
            pass  # already exists
        
        for item in items:
            try:
                if item.isDir:
                    # Archive entire date subfolder (e.g., 2026-03-12/)
                    dest_folder = f"{processed_path}{item.name}/"
                    mssparkutils.fs.mkdirs(dest_folder)
                    sub_files = mssparkutils.fs.ls(item.path)
                    for sf in sub_files:
                        mssparkutils.fs.mv(sf.path, f"{dest_folder}{sf.name}", True)
                    # Remove the now-empty source folder
                    try:
                        mssparkutils.fs.rm(item.path, True)
                    except Exception:
                        pass
                    archived_count += 1
                    print(f"  ✓ Archived: incremental/{item.name}/ → processed/{item.name}/")
                elif item.name.endswith(".csv"):
                    # Archive legacy flat CSV file
                    mssparkutils.fs.mv(item.path, f"{processed_path}{item.name}", True)
                    archived_count += 1
                    print(f"  ✓ Archived: {item.name} → processed/{item.name}")
            except Exception as e:
                print(f"  ⚠️ Could not archive {item.name}: {str(e)[:100]}")
        
        if archived_count > 0:
            print(f"\n✓ Archived {archived_count} item(s) → Files/processed/")
            print("  Next incremental run will only process NEW files")
        else:
            print("  No items to archive in incremental/")
    except Exception:
        print("  No incremental folder found — nothing to archive")
else:
    print("Full load mode — archiving skipped (tables were overwritten)")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## Verify Loaded Data
# 
# Quick check of record counts in Bronze tables.

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Verify data in Bronze tables
print("\nVerifying Bronze tables:")
print("-" * 40)

for table_config in TABLES_CONFIG:
    table_name = table_config["name"]
    use_raw = table_config.get("raw_suffix", True)
    tbl = f"{table_name}_raw" if use_raw else table_name
    try:
        count = spark.sql(f"SELECT COUNT(*) as cnt FROM {BRONZE_SCHEMA}.{tbl}").collect()[0]['cnt']
        print(f"  {tbl}: {count:,} rows")
    except Exception as e:
        print(f"  {tbl}: Error - {e}")

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# ## Summary

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Print summary
print("\n" + "="*60)
print(f"BRONZE INGEST SUMMARY - CSV {load_mode.upper()} LOAD")
print("="*60)

print(f"\nResults:")
total_records = 0
success_count = 0
failed_count = 0

for r in results:
    if r['status'] == 'success':
        print(f"  ✓ {r['table']}: {r['records']:,} records")
        success_count += 1
    else:
        print(f"  ✗ {r['table']}: FAILED - {r.get('error', 'Unknown error')[:50]}")
        failed_count += 1
    total_records += r['records']

print(f"\n" + "-"*40)
print(f"Total records: {total_records:,}")
print(f"Tables succeeded: {success_count}")
print(f"Tables failed: {failed_count}")
print(f"Completed at: {datetime.now()}")

# Return result for pipeline
exit_message = f"csv_{load_mode}:{total_records}"
mssparkutils.notebook.exit(exit_message)
