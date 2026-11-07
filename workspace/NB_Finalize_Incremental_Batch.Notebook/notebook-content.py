# Fabric notebook source

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# NB_Finalize_Incremental_Batch
# ============================================================================
# Archives a pending incremental batch only after the complete Bronze-to-Gold
# pipeline succeeds. The pipeline invokes this notebook after Gold_Star_Schema.
#
# Default lakehouse: lh_bronze_raw
# ============================================================================

from notebookutils import mssparkutils

try:
    load_mode = spark.conf.get("spark.load_mode", "full").lower().strip()
except Exception:
    load_mode = "full"

if load_mode not in {"full", "incremental"}:
    raise ValueError(f"Unsupported load_mode: {load_mode!r}")

if load_mode == "full":
    print("Full load mode: no incremental batch to finalize.")
    mssparkutils.notebook.exit("Full load finalization skipped")

INCREMENTAL_PATH = "Files/incremental"
PROCESSED_PATH = "Files/processed"
EXPECTED_ENTITIES = {
    "encounters",
    "claims",
    "prescriptions",
    "diagnoses",
    "patients",
}

def list_files(path):
    if not mssparkutils.fs.exists(path):
        return []
    return [item for item in mssparkutils.fs.ls(path) if not item.isDir]

def entities_in(files):
    entities = set()
    for file_info in files:
        for entity in EXPECTED_ENTITIES:
            if file_info.name.startswith(f"{entity}_") and file_info.name.endswith(".csv"):
                entities.add(entity)
                break
    return entities

def validate_complete_batch(batch_name, source_files, destination_files):
    available = entities_in(source_files) | entities_in(destination_files)
    missing = sorted(EXPECTED_ENTITIES - available)
    if missing:
        raise RuntimeError(
            f"Incremental batch {batch_name!r} is incomplete; missing files for: "
            + ", ".join(missing)
        )

mssparkutils.fs.mkdirs(PROCESSED_PATH)
pending_items = (
    mssparkutils.fs.ls(INCREMENTAL_PATH)
    if mssparkutils.fs.exists(INCREMENTAL_PATH)
    else []
)
pending_folders = [item for item in pending_items if item.isDir]
legacy_files = [item for item in pending_items if not item.isDir and item.name.endswith(".csv")]

finalized_batches = []

for folder in pending_folders:
    batch_name = folder.name.rstrip("/")
    destination_folder = f"{PROCESSED_PATH}/{batch_name}"
    mssparkutils.fs.mkdirs(destination_folder)

    source_files = list_files(folder.path)
    destination_files = list_files(destination_folder)
    validate_complete_batch(batch_name, source_files, destination_files)

    for source_file in source_files:
        destination_file = f"{destination_folder}/{source_file.name}"
        mssparkutils.fs.mv(source_file.path, destination_file, True)

    archived_files = list_files(destination_folder)
    validate_complete_batch(batch_name, [], archived_files)
    mssparkutils.fs.rm(folder.path, True)
    finalized_batches.append(batch_name)
    print(f"Finalized incremental batch: {batch_name}")

if legacy_files:
    validate_complete_batch("legacy", legacy_files, list_files(PROCESSED_PATH))
    for source_file in legacy_files:
        mssparkutils.fs.mv(
            source_file.path,
            f"{PROCESSED_PATH}/{source_file.name}",
            True,
        )
    finalized_batches.append("legacy")
    print("Finalized legacy incremental files.")

if finalized_batches:
    print(f"Incremental finalization complete: {finalized_batches}")
else:
    print("No pending incremental batch found. Finalization is already complete.")
