# Fabric notebook source

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# NB_Generate_Incremental_Data
# ============================================================================
# Generates NEW encounters, claims, prescriptions, diagnoses, patient updates,
# and new patient registrations for "today", simulating daily operational data.
#
# Use this notebook AFTER the initial full load to demo incremental pipeline.
#   1. Run this notebook (creates incremental CSVs in lh_bronze_raw)
#   2. Run the pipeline with load_mode=incremental
#   3. Bronze picks up base + incremental, Silver deduplicates, Gold MERGEs
#
# Default lakehouse: lh_bronze_raw
# ============================================================================

print("NB_Generate_Incremental_Data: Starting...")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from notebookutils import mssparkutils

random.seed()
np.random.seed()

# Parameters — override via spark.conf or use defaults
try:
    NUM_ENCOUNTERS = int(spark.conf.get("spark.incr_encounters", "50"))
except:
    NUM_ENCOUNTERS = 50

try:
    NUM_CLAIMS = int(spark.conf.get("spark.incr_claims", "50"))
except:
    NUM_CLAIMS = 50

NUM_PATIENT_UPDATES = 3
NUM_NEW_PATIENTS = 2

# Date range: today only
START_DATE = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
END_DATE = START_DATE
DATE_TAG = START_DATE.strftime("%Y-%m-%d")
TIMESTAMP_TAG = datetime.now().strftime("%Y%m%d_%H%M%S")

print(f"Generating incremental data for: {DATE_TAG}")
print(f"  Encounters: {NUM_ENCOUNTERS}, Claims: {NUM_CLAIMS}")
print(f"  Patient updates: {NUM_PATIENT_UPDATES}, New patients: {NUM_NEW_PATIENTS}")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# REFERENCE DATA (must match NB_Generate_Sample_Data)
# ============================================================================

ENCOUNTER_TYPES = ["Inpatient", "Outpatient", "Emergency", "Observation", "Telehealth"]
ADMISSION_TYPES = ["Emergency", "Elective", "Urgent"]
DISCHARGE_DISPOSITIONS = ["Home", "SNF", "Rehab", "Home Health", "Expired", "AMA", "Transfer"]
CLAIM_TYPES = ["Professional", "Institutional", "Pharmacy"]
CLAIM_STATUSES_APPROVED = ["Approved", "Paid"]
CLAIM_STATUSES_DENIED = ["Denied", "Appealed"]
DENIAL_REASONS = [
    "Prior Auth Required", "Not Medically Necessary", "Duplicate Claim",
    "Invalid Code", "Coverage Expired", "Out of Network", "Missing Documentation"
]
PAYERS = [
    {"payer_id": "PAY001", "name": "Blue Cross Blue Shield of Michigan", "type": "Commercial", "contract_rate": 0.85},
    {"payer_id": "PAY002", "name": "Aetna", "type": "Commercial", "contract_rate": 0.80},
    {"payer_id": "PAY003", "name": "United Healthcare", "type": "Commercial", "contract_rate": 0.82},
    {"payer_id": "PAY004", "name": "Cigna", "type": "Commercial", "contract_rate": 0.78},
    {"payer_id": "PAY005", "name": "Humana", "type": "Commercial", "contract_rate": 0.75},
    {"payer_id": "PAY006", "name": "Medicare Part A", "type": "Medicare", "contract_rate": 0.65},
    {"payer_id": "PAY007", "name": "Medicare Part B", "type": "Medicare", "contract_rate": 0.60},
    {"payer_id": "PAY008", "name": "Medicaid Michigan", "type": "Medicaid", "contract_rate": 0.45},
    {"payer_id": "PAY009", "name": "Priority Health", "type": "Commercial", "contract_rate": 0.83},
    {"payer_id": "PAY010", "name": "Tricare", "type": "Government", "contract_rate": 0.70},
    {"payer_id": "PAY011", "name": "Workers Compensation", "type": "Workers Comp", "contract_rate": 0.90},
    {"payer_id": "PAY012", "name": "Self-Pay", "type": "Self-Pay", "contract_rate": 1.00},
]
ICD_CODES = ["I10", "E11.9", "J06.9", "M54.5", "F32.9", "J18.9", "N39.0",
             "I25.10", "K21.0", "J45.909", "I50.9", "E78.5", "J44.9"]
MEDICATIONS = [
    {"rxnorm_code": "314076", "medication_name": "Lisinopril 10 MG Oral Tablet", "generic_name": "Lisinopril", "drug_class": "ACE Inhibitor", "therapeutic_area": "Cardiovascular", "route": "Oral", "strength": "10 MG", "avg_cost": 12.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "197361", "medication_name": "Amlodipine 5 MG Oral Tablet", "generic_name": "Amlodipine", "drug_class": "Calcium Channel Blocker", "therapeutic_area": "Cardiovascular", "route": "Oral", "strength": "5 MG", "avg_cost": 15.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "200031", "medication_name": "Atorvastatin 20 MG Oral Tablet", "generic_name": "Atorvastatin", "drug_class": "Statin", "therapeutic_area": "Cardiovascular", "route": "Oral", "strength": "20 MG", "avg_cost": 18.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "866924", "medication_name": "Metoprolol Succinate 50 MG Extended Release Oral Tablet", "generic_name": "Metoprolol", "drug_class": "Beta Blocker", "therapeutic_area": "Cardiovascular", "route": "Oral", "strength": "50 MG", "avg_cost": 14.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "310798", "medication_name": "Losartan 50 MG Oral Tablet", "generic_name": "Losartan", "drug_class": "ARB", "therapeutic_area": "Cardiovascular", "route": "Oral", "strength": "50 MG", "avg_cost": 16.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "836585", "medication_name": "Warfarin Sodium 5 MG Oral Tablet", "generic_name": "Warfarin", "drug_class": "Anticoagulant", "therapeutic_area": "Cardiovascular", "route": "Oral", "strength": "5 MG", "avg_cost": 11.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "860974", "medication_name": "Metformin 500 MG Oral Tablet", "generic_name": "Metformin", "drug_class": "Biguanide", "therapeutic_area": "Endocrine", "route": "Oral", "strength": "500 MG", "avg_cost": 8.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "311040", "medication_name": "Glipizide 5 MG Oral Tablet", "generic_name": "Glipizide", "drug_class": "Sulfonylurea", "therapeutic_area": "Endocrine", "route": "Oral", "strength": "5 MG", "avg_cost": 10.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "895994", "medication_name": "Albuterol 0.09 MG/ACTUAT Metered Dose Inhaler", "generic_name": "Albuterol", "drug_class": "Beta-2 Agonist", "therapeutic_area": "Respiratory", "route": "Inhalation", "strength": "0.09 MG/ACTUAT", "avg_cost": 45.00, "days_supply_typical": 30, "is_chronic": False},
    {"rxnorm_code": "310965", "medication_name": "Ibuprofen 200 MG Oral Tablet", "generic_name": "Ibuprofen", "drug_class": "NSAID", "therapeutic_area": "Pain", "route": "Oral", "strength": "200 MG", "avg_cost": 6.00, "days_supply_typical": 14, "is_chronic": False},
    {"rxnorm_code": "313782", "medication_name": "Acetaminophen 500 MG Oral Tablet", "generic_name": "Acetaminophen", "drug_class": "Analgesic", "therapeutic_area": "Pain", "route": "Oral", "strength": "500 MG", "avg_cost": 5.00, "days_supply_typical": 14, "is_chronic": False},
    {"rxnorm_code": "312938", "medication_name": "Sertraline 50 MG Oral Tablet", "generic_name": "Sertraline", "drug_class": "SSRI", "therapeutic_area": "Mental Health", "route": "Oral", "strength": "50 MG", "avg_cost": 14.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "311700", "medication_name": "Omeprazole 20 MG Delayed Release Oral Capsule", "generic_name": "Omeprazole", "drug_class": "Proton Pump Inhibitor", "therapeutic_area": "Digestive", "route": "Oral", "strength": "20 MG", "avg_cost": 12.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "308182", "medication_name": "Amoxicillin 500 MG Oral Capsule", "generic_name": "Amoxicillin", "drug_class": "Penicillin Antibiotic", "therapeutic_area": "Infectious Disease", "route": "Oral", "strength": "500 MG", "avg_cost": 10.00, "days_supply_typical": 10, "is_chronic": False},
    {"rxnorm_code": "197511", "medication_name": "Azithromycin 250 MG Oral Tablet", "generic_name": "Azithromycin", "drug_class": "Macrolide Antibiotic", "therapeutic_area": "Infectious Disease", "route": "Oral", "strength": "250 MG", "avg_cost": 15.00, "days_supply_typical": 5, "is_chronic": False},
    {"rxnorm_code": "310429", "medication_name": "Furosemide 40 MG Oral Tablet", "generic_name": "Furosemide", "drug_class": "Loop Diuretic", "therapeutic_area": "Cardiovascular", "route": "Oral", "strength": "40 MG", "avg_cost": 9.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "856987", "medication_name": "Hydrocodone-Acetaminophen 5-325 MG Oral Tablet", "generic_name": "Hydrocodone/APAP", "drug_class": "Opioid", "therapeutic_area": "Pain", "route": "Oral", "strength": "5-325 MG", "avg_cost": 22.00, "days_supply_typical": 7, "is_chronic": False},
]
MED_LOOKUP = {m["rxnorm_code"]: m for m in MEDICATIONS}

ICD_TO_MEDICATIONS = {
    "I10": ["314076", "197361", "310798", "310429", "310965"],
    "E11.9": ["860974", "311040"],
    "J06.9": ["308182", "197511", "313782"],
    "M54.5": ["310965", "313782", "856987"],
    "F32.9": ["312938"],
    "J18.9": ["308182", "197511", "895994"],
    "N39.0": ["308182", "197511"],
    "I25.10": ["200031", "866924", "836585", "314076"],
    "K21.0": ["311700"],
    "J45.909": ["895994"],
    "I50.9": ["310429", "314076", "866924", "836585"],
    "E78.5": ["200031"],
    "J44.9": ["895994"],
}

COMORBIDITY_MAP = {
    "I10": ["E11.9", "E78.5", "I25.10", "I50.9"],
    "E11.9": ["I10", "E78.5", "N39.0"],
    "I25.10": ["I10", "E78.5", "I50.9"],
    "I50.9": ["I10", "I25.10", "E11.9"],
    "J44.9": ["J45.909", "J18.9"],
    "F32.9": ["M54.5", "K21.0"],
}

MALE_FIRST_NAMES = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph",
                    "Thomas", "Christopher", "Charles", "Daniel", "Matthew", "Anthony", "Mark", "Donald"]
FEMALE_FIRST_NAMES = ["Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica",
                      "Sarah", "Karen", "Nancy", "Lisa", "Betty", "Margaret", "Sandra", "Ashley"]
FIRST_NAMES = MALE_FIRST_NAMES + FEMALE_FIRST_NAMES
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
              "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
              "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White"]
CITIES_MI = ["Grand Rapids", "Detroit", "Ann Arbor", "Lansing", "Kalamazoo", "Traverse City",
             "Flint", "Saginaw", "Muskegon", "Battle Creek"]
INSURANCE_TYPES = ["Commercial", "Medicare", "Medicaid", "Self-Pay"]
INSURANCE_PROVIDERS = ["Blue Cross Blue Shield", "Aetna", "United Healthcare", "Cigna",
                       "Humana", "Medicare", "Medicaid", "Priority Health"]

print("Reference data loaded")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# LOAD EXISTING PATIENTS & PROVIDERS FROM LAKEHOUSE
# ============================================================================

# Read the base CSV files from lh_bronze_raw/Files/
patients_sdf = spark.read.option("header", True).csv("Files/patients.csv")
providers_sdf = spark.read.option("header", True).csv("Files/providers.csv")

patient_ids = [row["patient_id"] for row in patients_sdf.select("patient_id").collect()]
provider_ids = [row["provider_id"] for row in providers_sdf.select("provider_id").collect()]
patients_pdf = patients_sdf.toPandas()

print(f"Loaded {len(patient_ids)} existing patients, {len(provider_ids)} existing providers")

# Scan for max IDs from existing CSV data to avoid collisions
def scan_max_id_from_csv(path, id_col):
    """Read CSV and find max numeric ID."""
    try:
        df = spark.read.option("header", True).csv(path)
        import pyspark.sql.functions as F
        max_val = df.select(F.max(F.regexp_extract(F.col(id_col), r"(\d+)", 1).cast("int"))).collect()[0][0]
        return max_val if max_val else 0
    except:
        return 0

next_enc = scan_max_id_from_csv("Files/encounters.csv", "encounter_id") + 1
next_clm = scan_max_id_from_csv("Files/claims.csv", "claim_id") + 1
next_rx = scan_max_id_from_csv("Files/prescriptions.csv", "prescription_id") + 1
next_dx = scan_max_id_from_csv("Files/diagnoses.csv", "diagnosis_id") + 1
next_pat = int(patients_pdf["patient_id"].str.extract(r"(\d+)").astype(int).max().iloc[0]) + 1

# Also scan incremental/ for even higher IDs
try:
    incr_files = mssparkutils.fs.ls("Files/incremental")
    for folder_info in incr_files:
        folder_path = folder_info.path
        for entity in ["encounters", "claims", "prescriptions", "diagnoses"]:
            try:
                id_col_map = {"encounters": "encounter_id", "claims": "claim_id",
                              "prescriptions": "prescription_id", "diagnoses": "diagnosis_id"}
                entity_files = [f for f in mssparkutils.fs.ls(folder_path) if entity in f.name]
                for ef in entity_files:
                    val = scan_max_id_from_csv(ef.path, id_col_map[entity])
                    if entity == "encounters":
                        next_enc = max(next_enc, val + 1)
                    elif entity == "claims":
                        next_clm = max(next_clm, val + 1)
                    elif entity == "prescriptions":
                        next_rx = max(next_rx, val + 1)
                    elif entity == "diagnoses":
                        next_dx = max(next_dx, val + 1)
            except:
                pass
except:
    pass  # No incremental folder yet — that's fine

print(f"Next IDs: ENC{next_enc:08d} | CLM{next_clm:09d} | RX{next_rx:09d} | DX{next_dx:08d} | PAT{next_pat:06d}")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# GENERATE ENCOUNTERS
# ============================================================================

def random_time_on_date(target_date):
    return target_date.replace(hour=random.randint(6, 22), minute=random.randint(0, 59), second=random.randint(0, 59))

def generate_encounters_incr(num, patient_ids, provider_ids, start_date, end_date, next_id):
    total_days = max((end_date - start_date).days + 1, 1)
    encounters = []
    for i in range(num):
        enc_id = f"ENC{next_id + i:08d}"
        day_offset = random.randint(0, total_days - 1)
        enc_date = start_date + timedelta(days=day_offset)
        enc_dt = random_time_on_date(enc_date)
        enc_type = random.choices(ENCOUNTER_TYPES, weights=[0.20, 0.40, 0.25, 0.10, 0.05])[0]

        if enc_type == "Inpatient":
            los = random.choices(range(1, 15), weights=[20,15,12,10,8,7,6,5,4,3,3,3,2,2])[0]
        elif enc_type == "Emergency":
            los = random.choices([0, 1, 2], weights=[60, 30, 10])[0]
        else:
            los = 0

        discharge_date = enc_date + timedelta(days=los) if los > 0 else enc_date
        icd_code = random.choice(ICD_CODES)
        total_charges = round(random.uniform(200, 5000) * max(los, 1), 2)
        total_cost = round(total_charges * random.uniform(0.5, 0.8), 2)
        base_risk = 0.08
        if enc_type == "Inpatient": base_risk += 0.12
        if los > 5: base_risk += 0.10
        readmission_risk = min(round(base_risk + random.uniform(-0.05, 0.15), 4), 0.99)

        encounters.append({
            "encounter_id": enc_id,
            "patient_id": random.choice(patient_ids),
            "provider_id": random.choice(provider_ids),
            "encounter_type": enc_type,
            "admit_date": enc_date.strftime("%Y-%m-%d"),
            "discharge_date": discharge_date.strftime("%Y-%m-%d"),
            "length_of_stay": los,
            "primary_diagnosis_code": icd_code,
            "facility_id": f"FAC{random.randint(1,8):03d}",
            "admission_type": random.choice(ADMISSION_TYPES),
            "discharge_disposition": random.choice(DISCHARGE_DISPOSITIONS),
            "total_charges": total_charges,
            "readmission_risk": readmission_risk,
        })
    return pd.DataFrame(encounters)

enc_df = generate_encounters_incr(NUM_ENCOUNTERS, patient_ids, provider_ids, START_DATE, END_DATE, next_enc)
print(f"Generated {len(enc_df)} encounters")
print(f"  Types: {enc_df['encounter_type'].value_counts().to_dict()}")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# GENERATE CLAIMS
# ============================================================================

def generate_claims_incr(num, encounters_df, next_id):
    claims = []
    for i in range(num):
        clm_id = f"CLM{next_id + i:09d}"
        enc_row = encounters_df.iloc[random.randint(0, len(encounters_df) - 1)]
        payer = random.choice(PAYERS)
        claim_type = random.choice(CLAIM_TYPES)
        if claim_type == "Institutional":
            billed = round(random.uniform(1000, 50000), 2)
        elif claim_type == "Professional":
            billed = round(random.uniform(100, 2000), 2)
        else:
            billed = round(random.uniform(10, 500), 2)

        allowed = round(billed * payer["contract_rate"], 2)
        is_denied = random.choices([0, 1], weights=[0.92, 0.08])[0]
        if is_denied:
            status = random.choice(CLAIM_STATUSES_DENIED)
            denial = random.choice(DENIAL_REASONS)
            paid = 0
        else:
            status = random.choice(CLAIM_STATUSES_APPROVED)
            denial = None
            paid = round(allowed * random.uniform(0.85, 1.0), 2)

        service_date = datetime.strptime(enc_row["admit_date"], "%Y-%m-%d")
        submit_date = service_date + timedelta(days=random.randint(1, 5))

        claims.append({
            "claim_id": clm_id,
            "encounter_id": enc_row["encounter_id"],
            "patient_id": enc_row["patient_id"],
            "provider_id": enc_row["provider_id"],
            "payer_id": payer["payer_id"],
            "claim_type": claim_type,
            "cpt_code": f"99{random.randint(200,299)}",
            "primary_diagnosis_code": enc_row["primary_diagnosis_code"],
            "service_date": service_date.strftime("%Y-%m-%d"),
            "submit_date": submit_date.strftime("%Y-%m-%d"),
            "process_date": (submit_date + timedelta(days=random.randint(14, 45))).strftime("%Y-%m-%d"),
            "billed_amount": billed,
            "allowed_amount": allowed,
            "paid_amount": paid,
            "patient_responsibility": round(billed - paid if paid > 0 else billed * 0.2, 2),
            "claim_status": status,
            "denial_reason": denial,
        })
    return pd.DataFrame(claims)

clm_df = generate_claims_incr(NUM_CLAIMS, enc_df, next_clm)
denied = clm_df["denial_reason"].notna().sum() if len(clm_df) > 0 else 0
print(f"Generated {len(clm_df)} claims ({denied} denied)")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# GENERATE PRESCRIPTIONS (1-3 per encounter)
# ============================================================================

def generate_prescriptions_incr(encounters_df, next_id):
    prescriptions = []
    rx_counter = next_id
    for _, enc in encounters_df.iterrows():
        icd = enc.get("primary_diagnosis_code", "I10")
        enc_date = datetime.strptime(enc["admit_date"], "%Y-%m-%d")
        applicable_rx = ICD_TO_MEDICATIONS.get(icd, ["313782"])
        num_rx = random.choices([0, 1, 2, 3], weights=[0.10, 0.40, 0.35, 0.15])[0]
        selected = random.sample(applicable_rx, min(num_rx, len(applicable_rx)))

        for rxnorm in selected:
            med = MED_LOOKUP.get(rxnorm)
            if not med:
                continue
            rx_counter += 1
            fill_date = enc_date + timedelta(days=random.randint(0, 3))
            cost = round(med["avg_cost"] * random.uniform(0.85, 1.15), 2)
            copay = round(cost * random.uniform(0.1, 0.3), 2)

            prescriptions.append({
                "prescription_id": f"RX{rx_counter:08d}",
                "encounter_id": enc["encounter_id"],
                "patient_id": enc["patient_id"],
                "provider_id": enc["provider_id"],
                "rxnorm_code": rxnorm,
                "medication_name": med["medication_name"],
                "fill_date": fill_date.strftime("%Y-%m-%d"),
                "days_supply": med["days_supply_typical"],
                "quantity": random.choice([30, 60, 90]) if med["is_chronic"] else random.choice([10, 14, 30]),
                "refill_number": 0,
                "total_cost": cost,
                "copay_amount": copay,
                "pharmacy_id": f"PHR{random.randint(1, 50):04d}",
                "prescriber_id": enc["provider_id"],
                "is_generic": random.choices([True, False], weights=[0.8, 0.2])[0],
                "prior_auth_required": random.choices([True, False], weights=[0.1, 0.9])[0],
            })
    return pd.DataFrame(prescriptions)

rx_df = generate_prescriptions_incr(enc_df, next_rx)
print(f"Generated {len(rx_df)} prescriptions")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# GENERATE DIAGNOSES (1 principal + 0-2 secondary per encounter)
# ============================================================================

def generate_diagnoses_incr(encounters_df, next_id):
    all_icd = ICD_CODES
    diagnoses = []
    dx_counter = next_id
    for _, enc in encounters_df.iterrows():
        primary = enc.get("primary_diagnosis_code", "I10")
        enc_type = enc.get("encounter_type", "Outpatient")
        dx_counter += 1
        diagnoses.append({
            "diagnosis_id": f"DX{dx_counter:08d}",
            "encounter_id": enc["encounter_id"],
            "patient_id": enc["patient_id"],
            "icd_code": primary,
            "diagnosis_type": "Principal",
            "sequence_number": 1,
            "diagnosis_date": enc["admit_date"],
            "present_on_admission": random.choice(["Y", "N", "U"]) if enc_type == "Inpatient" else None,
        })
        if enc_type in ["Inpatient", "Emergency"]:
            num_sec = random.choices([0, 1, 2], weights=[0.10, 0.60, 0.30])[0]
        else:
            num_sec = random.choices([0, 1, 2], weights=[0.60, 0.30, 0.10])[0]

        combos = COMORBIDITY_MAP.get(primary, [])
        pool = [c for c in all_icd if c != primary]
        weighted = []
        for c in pool:
            weighted.extend([c] * (3 if c in combos else 1))

        chosen = list(dict.fromkeys(random.sample(weighted, min(num_sec, len(weighted)))))
        for seq, sec_icd in enumerate(chosen, start=2):
            dx_counter += 1
            diagnoses.append({
                "diagnosis_id": f"DX{dx_counter:08d}",
                "encounter_id": enc["encounter_id"],
                "patient_id": enc["patient_id"],
                "icd_code": sec_icd,
                "diagnosis_type": "Secondary",
                "sequence_number": seq,
                "diagnosis_date": enc["admit_date"],
                "present_on_admission": random.choice(["Y", "N"]) if enc_type == "Inpatient" else None,
            })
    return pd.DataFrame(diagnoses)

dx_df = generate_diagnoses_incr(enc_df, next_dx)
principal = len(dx_df[dx_df["diagnosis_type"] == "Principal"]) if len(dx_df) > 0 else 0
secondary = len(dx_df[dx_df["diagnosis_type"] == "Secondary"]) if len(dx_df) > 0 else 0
print(f"Generated {len(dx_df)} diagnoses ({principal} principal, {secondary} secondary)")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# GENERATE PATIENT UPDATES & NEW PATIENTS
# ============================================================================

# Patient updates (simulate address/insurance changes for SCD2)
updated_patients = patients_pdf.sample(n=min(NUM_PATIENT_UPDATES, len(patients_pdf))).copy()
for idx in updated_patients.index:
    change = random.choice(["address", "insurance", "both"])
    if change in ("address", "both"):
        updated_patients.at[idx, "city"] = random.choice(CITIES_MI)
        updated_patients.at[idx, "zip_code"] = str(random.randint(48001, 49999))
    if change in ("insurance", "both"):
        updated_patients.at[idx, "insurance_type"] = random.choice(INSURANCE_TYPES)
        updated_patients.at[idx, "insurance_provider"] = random.choice(INSURANCE_PROVIDERS)
    updated_patients.at[idx, "modified_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

print(f"Updated {len(updated_patients)} existing patients")

# New patients
new_patients = []
for i in range(NUM_NEW_PATIENTS):
    pid = f"PAT{next_pat + i:06d}"
    gender = random.choice(["M", "F"])
    dob = datetime(random.randint(1940, 2020), random.randint(1, 12), random.randint(1, 28))
    new_patients.append({
        "patient_id": pid,
        "first_name": random.choice(MALE_FIRST_NAMES) if gender == "M" else random.choice(FEMALE_FIRST_NAMES),
        "last_name": random.choice(LAST_NAMES),
        "date_of_birth": dob.strftime("%Y-%m-%d"),
        "gender": gender,
        "address": f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Elm', 'Cedar'])} St",
        "city": random.choice(CITIES_MI),
        "state": "MI",
        "zip_code": str(random.randint(48001, 49999)),
        "phone": f"{random.randint(200,999)}-{random.randint(200,999)}-{random.randint(1000,9999)}",
        "email": f"{random.choice(FIRST_NAMES).lower()}.{random.choice(LAST_NAMES).lower()}@email.com",
        "insurance_type": random.choice(INSURANCE_TYPES),
        "insurance_provider": random.choice(INSURANCE_PROVIDERS),
        "pcp_provider_id": random.choice(provider_ids),
        "created_date": datetime.now().strftime("%Y-%m-%d"),
        "modified_date": datetime.now().strftime("%Y-%m-%d"),
    })
new_patients_df = pd.DataFrame(new_patients)
print(f"Created {len(new_patients_df)} new patients")

# Combine patient changes
pat_combined = pd.concat([updated_patients, new_patients_df], ignore_index=True)

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# WRITE INCREMENTAL CSVs TO LAKEHOUSE
# ============================================================================
# Output: Files/incremental/YYYY-MM-DD/<entity>_<timestamp>.csv

def write_csv(df, path):
    csv_content = df.to_csv(index=False)
    mssparkutils.fs.put(path, csv_content, overwrite=True)
    print(f"  Written: {path} ({len(df):,} rows)")

incr_path = f"Files/incremental/{DATE_TAG}"

print(f"\nWriting to {incr_path}/...")
write_csv(enc_df, f"{incr_path}/encounters_{TIMESTAMP_TAG}.csv")
write_csv(clm_df, f"{incr_path}/claims_{TIMESTAMP_TAG}.csv")
write_csv(rx_df, f"{incr_path}/prescriptions_{TIMESTAMP_TAG}.csv")
write_csv(dx_df, f"{incr_path}/diagnoses_{TIMESTAMP_TAG}.csv")
if len(pat_combined) > 0:
    write_csv(pat_combined, f"{incr_path}/patients_{TIMESTAMP_TAG}.csv")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# SUMMARY
# ============================================================================

print("=" * 60)
print("  INCREMENTAL DATA GENERATION COMPLETE")
print("=" * 60)
print(f"  Date:           {DATE_TAG}")
print(f"  Encounters:     {len(enc_df):>8,}")
print(f"  Claims:         {len(clm_df):>8,}")
print(f"  Prescriptions:  {len(rx_df):>8,}")
print(f"  Diagnoses:      {len(dx_df):>8,}")
print(f"  Patient updates:{len(updated_patients):>8,}")
print(f"  New patients:   {len(new_patients_df):>8,}")
print(f"  Output folder:  Files/incremental/{DATE_TAG}/")
print("=" * 60)
print()
print("NEXT STEPS:")
print("  1. Run the pipeline with load_mode=incremental")
print("  2. Bronze picks up base CSVs + incremental/**/*.csv")
print("  3. Silver deduplicates, Gold MERGEs star schema")
print("  4. Refresh the semantic model")
