# Fabric notebook source

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# NB_Generate_Sample_Data
# ============================================================================
# Generates fresh synthetic healthcare data with dates anchored to today,
# then writes CSV files to lh_bronze_raw/Files/ for the Bronze ingest layer.
#
# This notebook is called by the Healthcare_Launcher after artifact deployment.
# It replaces the local generate_data.py + generate_diagnosis_sdoh.py scripts
# that were previously run from a local Python environment.
#
# Default lakehouse: lh_bronze_raw
# ============================================================================

print("NB_Generate_Sample_Data: Starting...")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# Install Faker (not pre-installed in Fabric Spark)
# Uses subprocess instead of %pip so this notebook can be called via
# notebookutils.notebook.run() — %pip magic is disabled in child notebooks.
import subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "faker", "--quiet", "--disable-pip-version-check"])

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import random
import os
import hashlib
import csv
import io

fake = Faker()
Faker.seed(42)
np.random.seed(42)
random.seed(42)

# Parameters (can be overridden by pipeline/launcher)
try:
    NUM_PATIENTS = int(spark.conf.get("spark.num_patients", "10000"))
except:
    NUM_PATIENTS = 10000

NUM_PROVIDERS = 500
NUM_ENCOUNTERS = NUM_PATIENTS * 10  # ~10 encounters per patient
NUM_CLAIMS = NUM_ENCOUNTERS
NUM_PRESCRIPTIONS = int(NUM_ENCOUNTERS * 2.5)

# Dynamic date range: 2 years back from today through tomorrow
DATA_END_DATE = datetime.now() + timedelta(days=1)
DATA_START_DATE = DATA_END_DATE - timedelta(days=730)

print(f"Generating data for {NUM_PATIENTS} patients, {NUM_ENCOUNTERS} encounters")
print(f"Date range: {DATA_START_DATE.strftime('%Y-%m-%d')} to {DATA_END_DATE.strftime('%Y-%m-%d')}")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# REFERENCE DATA
# ============================================================================

SPECIALTIES = [
    "Internal Medicine", "Family Medicine", "Cardiology", "Orthopedics",
    "Neurology", "Oncology", "Pediatrics", "Emergency Medicine",
    "Psychiatry", "Radiology", "Anesthesiology", "Surgery",
    "Obstetrics/Gynecology", "Dermatology", "Ophthalmology"
]

FACILITIES = [
    {"id": "FAC001", "name": "Lakeside Main Hospital", "type": "Hospital", "city": "Grand Rapids", "state": "MI", "beds": 450, "latitude": 42.9634, "longitude": -85.6681},
    {"id": "FAC002", "name": "Lakeside Heart Center", "type": "Specialty", "city": "Grand Rapids", "state": "MI", "beds": 120, "latitude": 42.9554, "longitude": -85.6561},
    {"id": "FAC003", "name": "Lakeside Urgent Care North", "type": "Urgent Care", "city": "Traverse City", "state": "MI", "beds": 0, "latitude": 44.7631, "longitude": -85.6206},
    {"id": "FAC004", "name": "Lakeside Cancer Institute", "type": "Specialty", "city": "Ann Arbor", "state": "MI", "beds": 80, "latitude": 42.2808, "longitude": -83.7430},
    {"id": "FAC005", "name": "Lakeside Community Clinic", "type": "Clinic", "city": "Lansing", "state": "MI", "beds": 0, "latitude": 42.7325, "longitude": -84.5555},
    {"id": "FAC006", "name": "Lakeside Children's Hospital", "type": "Hospital", "city": "Detroit", "state": "MI", "beds": 200, "latitude": 42.3314, "longitude": -83.0458},
    {"id": "FAC007", "name": "Lakeside Rehabilitation Center", "type": "Rehab", "city": "Kalamazoo", "state": "MI", "beds": 100, "latitude": 42.2917, "longitude": -85.5872},
    {"id": "FAC008", "name": "Lakeside South Campus", "type": "Hospital", "city": "Toledo", "state": "OH", "beds": 350, "latitude": 41.6528, "longitude": -83.5379},
]

ENCOUNTER_TYPES = ["Inpatient", "Outpatient", "Emergency", "Observation", "Telehealth"]
ADMISSION_TYPES = ["Emergency", "Elective", "Urgent", "Newborn", "Trauma"]
DISCHARGE_DISPOSITIONS = ["Home", "SNF", "Rehab", "Home Health", "Expired", "AMA", "Transfer"]
CLAIM_TYPES = ["Professional", "Institutional", "Pharmacy"]
CLAIM_STATUSES = ["Submitted", "Pending", "Approved", "Denied", "Paid", "Appealed"]
DENIAL_REASONS = [None, "Prior Auth Required", "Not Medically Necessary", "Duplicate Claim",
                  "Invalid Code", "Coverage Expired", "Out of Network", "Missing Documentation"]

MEDICATIONS = [
    {"rxnorm_code": "314076", "medication_name": "Lisinopril 10 MG Oral Tablet", "generic_name": "Lisinopril", "drug_class": "ACE Inhibitor", "therapeutic_area": "Cardiovascular", "route": "Oral", "form": "Tablet", "strength": "10 MG", "avg_cost": 12.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "197361", "medication_name": "Amlodipine 5 MG Oral Tablet", "generic_name": "Amlodipine", "drug_class": "Calcium Channel Blocker", "therapeutic_area": "Cardiovascular", "route": "Oral", "form": "Tablet", "strength": "5 MG", "avg_cost": 15.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "200031", "medication_name": "Atorvastatin 20 MG Oral Tablet", "generic_name": "Atorvastatin", "drug_class": "Statin", "therapeutic_area": "Cardiovascular", "route": "Oral", "form": "Tablet", "strength": "20 MG", "avg_cost": 18.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "866924", "medication_name": "Metoprolol Succinate 50 MG Extended Release Oral Tablet", "generic_name": "Metoprolol", "drug_class": "Beta Blocker", "therapeutic_area": "Cardiovascular", "route": "Oral", "form": "Tablet", "strength": "50 MG", "avg_cost": 14.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "310798", "medication_name": "Losartan 50 MG Oral Tablet", "generic_name": "Losartan", "drug_class": "ARB", "therapeutic_area": "Cardiovascular", "route": "Oral", "form": "Tablet", "strength": "50 MG", "avg_cost": 16.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "836585", "medication_name": "Warfarin Sodium 5 MG Oral Tablet", "generic_name": "Warfarin", "drug_class": "Anticoagulant", "therapeutic_area": "Cardiovascular", "route": "Oral", "form": "Tablet", "strength": "5 MG", "avg_cost": 11.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "860974", "medication_name": "Metformin 500 MG Oral Tablet", "generic_name": "Metformin", "drug_class": "Biguanide", "therapeutic_area": "Endocrine", "route": "Oral", "form": "Tablet", "strength": "500 MG", "avg_cost": 8.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "311040", "medication_name": "Glipizide 5 MG Oral Tablet", "generic_name": "Glipizide", "drug_class": "Sulfonylurea", "therapeutic_area": "Endocrine", "route": "Oral", "form": "Tablet", "strength": "5 MG", "avg_cost": 10.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "1373463", "medication_name": "Insulin Glargine 100 UNT/ML Injectable Solution", "generic_name": "Insulin Glargine", "drug_class": "Insulin", "therapeutic_area": "Endocrine", "route": "Subcutaneous", "form": "Injectable", "strength": "100 UNT/ML", "avg_cost": 280.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "895994", "medication_name": "Albuterol 0.09 MG/ACTUAT Metered Dose Inhaler", "generic_name": "Albuterol", "drug_class": "Beta-2 Agonist", "therapeutic_area": "Respiratory", "route": "Inhalation", "form": "Inhaler", "strength": "0.09 MG/ACTUAT", "avg_cost": 45.00, "days_supply_typical": 30, "is_chronic": False},
    {"rxnorm_code": "896188", "medication_name": "Fluticasone Propionate 110 MCG/ACTUAT Inhaler", "generic_name": "Fluticasone", "drug_class": "Inhaled Corticosteroid", "therapeutic_area": "Respiratory", "route": "Inhalation", "form": "Inhaler", "strength": "110 MCG/ACTUAT", "avg_cost": 85.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "310965", "medication_name": "Ibuprofen 200 MG Oral Tablet", "generic_name": "Ibuprofen", "drug_class": "NSAID", "therapeutic_area": "Pain", "route": "Oral", "form": "Tablet", "strength": "200 MG", "avg_cost": 6.00, "days_supply_typical": 14, "is_chronic": False},
    {"rxnorm_code": "313782", "medication_name": "Acetaminophen 500 MG Oral Tablet", "generic_name": "Acetaminophen", "drug_class": "Analgesic", "therapeutic_area": "Pain", "route": "Oral", "form": "Tablet", "strength": "500 MG", "avg_cost": 5.00, "days_supply_typical": 14, "is_chronic": False},
    {"rxnorm_code": "856987", "medication_name": "Hydrocodone-Acetaminophen 5-325 MG Oral Tablet", "generic_name": "Hydrocodone/APAP", "drug_class": "Opioid", "therapeutic_area": "Pain", "route": "Oral", "form": "Tablet", "strength": "5-325 MG", "avg_cost": 22.00, "days_supply_typical": 7, "is_chronic": False},
    {"rxnorm_code": "312938", "medication_name": "Sertraline 50 MG Oral Tablet", "generic_name": "Sertraline", "drug_class": "SSRI", "therapeutic_area": "Mental Health", "route": "Oral", "form": "Tablet", "strength": "50 MG", "avg_cost": 14.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "312036", "medication_name": "Escitalopram 10 MG Oral Tablet", "generic_name": "Escitalopram", "drug_class": "SSRI", "therapeutic_area": "Mental Health", "route": "Oral", "form": "Tablet", "strength": "10 MG", "avg_cost": 16.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "835564", "medication_name": "Lorazepam 0.5 MG Oral Tablet", "generic_name": "Lorazepam", "drug_class": "Benzodiazepine", "therapeutic_area": "Mental Health", "route": "Oral", "form": "Tablet", "strength": "0.5 MG", "avg_cost": 12.00, "days_supply_typical": 14, "is_chronic": False},
    {"rxnorm_code": "311700", "medication_name": "Omeprazole 20 MG Delayed Release Oral Capsule", "generic_name": "Omeprazole", "drug_class": "Proton Pump Inhibitor", "therapeutic_area": "Digestive", "route": "Oral", "form": "Capsule", "strength": "20 MG", "avg_cost": 12.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "308182", "medication_name": "Amoxicillin 500 MG Oral Capsule", "generic_name": "Amoxicillin", "drug_class": "Penicillin Antibiotic", "therapeutic_area": "Infectious Disease", "route": "Oral", "form": "Capsule", "strength": "500 MG", "avg_cost": 10.00, "days_supply_typical": 10, "is_chronic": False},
    {"rxnorm_code": "197511", "medication_name": "Azithromycin 250 MG Oral Tablet", "generic_name": "Azithromycin", "drug_class": "Macrolide Antibiotic", "therapeutic_area": "Infectious Disease", "route": "Oral", "form": "Tablet", "strength": "250 MG", "avg_cost": 15.00, "days_supply_typical": 5, "is_chronic": False},
    {"rxnorm_code": "310429", "medication_name": "Furosemide 40 MG Oral Tablet", "generic_name": "Furosemide", "drug_class": "Loop Diuretic", "therapeutic_area": "Cardiovascular", "route": "Oral", "form": "Tablet", "strength": "40 MG", "avg_cost": 9.00, "days_supply_typical": 30, "is_chronic": True},
    {"rxnorm_code": "966247", "medication_name": "Levothyroxine Sodium 0.05 MG Oral Tablet", "generic_name": "Levothyroxine", "drug_class": "Thyroid Hormone", "therapeutic_area": "Endocrine", "route": "Oral", "form": "Tablet", "strength": "0.05 MG", "avg_cost": 13.00, "days_supply_typical": 30, "is_chronic": True},
]

MED_LOOKUP = {m["rxnorm_code"]: m for m in MEDICATIONS}

ICD_TO_MEDICATIONS = {
    "I10": ["314076", "197361", "310798", "310429", "310965"],
    "E11.9": ["860974", "311040", "1373463"],
    "J06.9": ["308182", "197511", "313782"],
    "M54.5": ["310965", "313782", "856987"],
    "F32.9": ["312938", "312036", "835564"],
    "J18.9": ["308182", "197511", "895994"],
    "N39.0": ["308182", "197511"],
    "I25.10": ["200031", "866924", "836585", "314076"],
    "K21.0": ["311700"],
    "J45.909": ["895994", "896188"],
    "G43.909": ["310965", "313782"],
    "I50.9": ["310429", "314076", "866924", "836585"],
    "E78.5": ["200031"],
    "J44.9": ["895994", "896188"],
    "M79.3": ["310965", "313782"],
    "R10.9": ["313782"],
    "S72.001A": ["856987", "310965"],
    "K80.20": ["313782", "856987"],
    "N18.3": ["310429", "314076"],
    "C50.911": ["312938", "835564"],
}

ICD_CODES = [
    {"code": "I10", "description": "Essential (primary) hypertension", "category": "Cardiovascular", "is_chronic": True},
    {"code": "E11.9", "description": "Type 2 diabetes mellitus without complications", "category": "Endocrine", "is_chronic": True},
    {"code": "J06.9", "description": "Acute upper respiratory infection, unspecified", "category": "Respiratory", "is_chronic": False},
    {"code": "M54.5", "description": "Low back pain", "category": "Musculoskeletal", "is_chronic": False},
    {"code": "F32.9", "description": "Major depressive disorder, single episode, unspecified", "category": "Mental Health", "is_chronic": True},
    {"code": "J18.9", "description": "Pneumonia, unspecified organism", "category": "Respiratory", "is_chronic": False},
    {"code": "N39.0", "description": "Urinary tract infection, site not specified", "category": "Genitourinary", "is_chronic": False},
    {"code": "I25.10", "description": "Atherosclerotic heart disease of native coronary artery", "category": "Cardiovascular", "is_chronic": True},
    {"code": "K21.0", "description": "Gastro-esophageal reflux disease with esophagitis", "category": "Digestive", "is_chronic": True},
    {"code": "J45.909", "description": "Unspecified asthma, uncomplicated", "category": "Respiratory", "is_chronic": True},
    {"code": "G43.909", "description": "Migraine, unspecified, not intractable", "category": "Neurological", "is_chronic": True},
    {"code": "I50.9", "description": "Heart failure, unspecified", "category": "Cardiovascular", "is_chronic": True},
    {"code": "E78.5", "description": "Hyperlipidemia, unspecified", "category": "Endocrine", "is_chronic": True},
    {"code": "J44.9", "description": "Chronic obstructive pulmonary disease, unspecified", "category": "Respiratory", "is_chronic": True},
    {"code": "M79.3", "description": "Panniculitis, unspecified", "category": "Musculoskeletal", "is_chronic": False},
    {"code": "R10.9", "description": "Unspecified abdominal pain", "category": "Symptoms", "is_chronic": False},
    {"code": "S72.001A", "description": "Fracture of unspecified part of neck of right femur", "category": "Injury", "is_chronic": False},
    {"code": "K80.20", "description": "Calculus of gallbladder without cholecystitis", "category": "Digestive", "is_chronic": False},
    {"code": "N18.3", "description": "Chronic kidney disease, stage 3", "category": "Genitourinary", "is_chronic": True},
    {"code": "C50.911", "description": "Malignant neoplasm of unspecified site of right female breast", "category": "Oncology", "is_chronic": True},
]

CPT_CODES = [
    {"code": "99213", "description": "Office visit, established patient, low complexity", "category": "E&M", "avg_charge": 150.00},
    {"code": "99214", "description": "Office visit, established patient, moderate complexity", "category": "E&M", "avg_charge": 200.00},
    {"code": "99215", "description": "Office visit, established patient, high complexity", "category": "E&M", "avg_charge": 275.00},
    {"code": "99283", "description": "Emergency department visit, moderate severity", "category": "E&M", "avg_charge": 450.00},
    {"code": "99284", "description": "Emergency department visit, high severity", "category": "E&M", "avg_charge": 650.00},
    {"code": "99285", "description": "Emergency department visit, highest severity", "category": "E&M", "avg_charge": 950.00},
    {"code": "99221", "description": "Initial hospital care, low complexity", "category": "E&M", "avg_charge": 350.00},
    {"code": "99222", "description": "Initial hospital care, moderate complexity", "category": "E&M", "avg_charge": 500.00},
    {"code": "99223", "description": "Initial hospital care, high complexity", "category": "E&M", "avg_charge": 700.00},
    {"code": "99281", "description": "Emergency department visit, self-limited", "category": "E&M", "avg_charge": 200.00},
    {"code": "99282", "description": "Emergency department visit, low severity", "category": "E&M", "avg_charge": 300.00},
    {"code": "71046", "description": "Chest X-ray, 2 views", "category": "Radiology", "avg_charge": 250.00},
    {"code": "93000", "description": "Electrocardiogram (ECG), complete", "category": "Cardiology", "avg_charge": 150.00},
    {"code": "80053", "description": "Comprehensive metabolic panel", "category": "Lab", "avg_charge": 120.00},
    {"code": "85025", "description": "Complete blood count (CBC) with differential", "category": "Lab", "avg_charge": 75.00},
    {"code": "36415", "description": "Venipuncture for blood draw", "category": "Lab", "avg_charge": 25.00},
    {"code": "99232", "description": "Subsequent hospital care, moderate complexity", "category": "E&M", "avg_charge": 200.00},
    {"code": "99238", "description": "Hospital discharge day management, 30 minutes or less", "category": "E&M", "avg_charge": 175.00},
    {"code": "99395", "description": "Preventive visit, established patient, 18-39", "category": "Preventive", "avg_charge": 275.00},
    {"code": "99396", "description": "Preventive visit, established patient, 40-64", "category": "Preventive", "avg_charge": 300.00},
]

PAYERS = [
    {"payer_id": "PAY001", "payer_name": "Blue Cross Blue Shield of Michigan", "payer_type": "Commercial", "plan_type": "PPO", "state": "MI", "network_size": "Large", "avg_reimbursement_pct": 0.82},
    {"payer_id": "PAY002", "payer_name": "Priority Health", "payer_type": "Commercial", "plan_type": "HMO", "state": "MI", "network_size": "Medium", "avg_reimbursement_pct": 0.78},
    {"payer_id": "PAY003", "payer_name": "Medicare Part A", "payer_type": "Government", "plan_type": "FFS", "state": "Federal", "network_size": "National", "avg_reimbursement_pct": 0.65},
    {"payer_id": "PAY004", "payer_name": "Medicare Part B", "payer_type": "Government", "plan_type": "FFS", "state": "Federal", "network_size": "National", "avg_reimbursement_pct": 0.60},
    {"payer_id": "PAY005", "payer_name": "Medicaid Michigan", "payer_type": "Government", "plan_type": "Managed", "state": "MI", "network_size": "Medium", "avg_reimbursement_pct": 0.45},
    {"payer_id": "PAY006", "payer_name": "United Healthcare", "payer_type": "Commercial", "plan_type": "PPO", "state": "National", "network_size": "Large", "avg_reimbursement_pct": 0.80},
    {"payer_id": "PAY007", "payer_name": "Aetna", "payer_type": "Commercial", "plan_type": "EPO", "state": "National", "network_size": "Large", "avg_reimbursement_pct": 0.79},
    {"payer_id": "PAY008", "payer_name": "Cigna", "payer_type": "Commercial", "plan_type": "PPO", "state": "National", "network_size": "Large", "avg_reimbursement_pct": 0.81},
    {"payer_id": "PAY009", "payer_name": "Humana", "payer_type": "Commercial", "plan_type": "HMO", "state": "National", "network_size": "Medium", "avg_reimbursement_pct": 0.76},
    {"payer_id": "PAY010", "payer_name": "Self-Pay", "payer_type": "Self-Pay", "plan_type": "None", "state": "N/A", "network_size": "N/A", "avg_reimbursement_pct": 1.00},
    {"payer_id": "PAY011", "payer_name": "Tricare", "payer_type": "Government", "plan_type": "Managed", "state": "Federal", "network_size": "National", "avg_reimbursement_pct": 0.70},
    {"payer_id": "PAY012", "payer_name": "Workers Compensation MI", "payer_type": "Workers Comp", "plan_type": "State", "state": "MI", "network_size": "State", "avg_reimbursement_pct": 0.85},
]

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

INSURANCE_TYPES = ["Commercial", "Medicare", "Medicaid", "Self-Pay", "Workers Comp", "Tricare"]
INSURANCE_PROVIDERS = ["Blue Cross Blue Shield", "Aetna", "United Healthcare", "Cigna",
                       "Humana", "Medicare", "Medicaid", "Priority Health"]

MONITOR_TYPES = [
    {"type": "Blood Pressure Monitor", "manufacturer": "Omron", "models": ["BP786N", "BP7450", "BP742N"]},
    {"type": "Pulse Oximeter", "manufacturer": "Masimo", "models": ["MightySat Rx", "Rad-67"]},
    {"type": "Glucose Monitor", "manufacturer": "Dexcom", "models": ["G7", "G6"]},
    {"type": "Weight Scale", "manufacturer": "Withings", "models": ["Body+", "Body Cardio"]},
    {"type": "Heart Rate Monitor", "manufacturer": "Polar", "models": ["H10", "Verity Sense"]},
    {"type": "Temperature Sensor", "manufacturer": "Kinsa", "models": ["QuickCare", "Smart Ear"]},
    {"type": "Activity Tracker", "manufacturer": "Fitbit", "models": ["Charge 5", "Inspire 3"]},
    {"type": "ECG Monitor", "manufacturer": "AliveCor", "models": ["KardiaMobile 6L", "KardiaMobile"]},
    {"type": "Spirometer", "manufacturer": "NuvoAir", "models": ["Air Next"]},
    {"type": "Sleep Monitor", "manufacturer": "ResMed", "models": ["AirSense 11"]},
]

print("Reference data loaded successfully")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# GENERATE PATIENTS
# ============================================================================

def generate_patients(n):
    patients = []
    for i in range(n):
        pid = f"PAT{i+1:06d}"
        gender = random.choice(["M", "F"])
        fn = random.choice(MALE_FIRST_NAMES) if gender == "M" else random.choice(FEMALE_FIRST_NAMES)
        ln = random.choice(LAST_NAMES)
        dob = fake.date_of_birth(minimum_age=18, maximum_age=90)
        city = random.choice(CITIES_MI)
        zipcode = f"{random.randint(48000, 49999)}"
        patients.append({
            "patient_id": pid,
            "first_name": fn,
            "last_name": ln,
            "date_of_birth": dob.strftime("%Y-%m-%d"),
            "gender": gender,
            "address": fake.street_address(),
            "city": city,
            "state": "MI",
            "zip_code": zipcode,
            "phone": fake.phone_number()[:12],
            "email": f"{fn.lower()}.{ln.lower()}{i}@email.com",
            "insurance_type": random.choice(INSURANCE_TYPES),
            "insurance_provider": random.choice(INSURANCE_PROVIDERS),
            "pcp_provider_id": f"PRV{random.randint(1, NUM_PROVIDERS):05d}",
            "created_date": DATA_START_DATE.strftime("%Y-%m-%d"),
            "modified_date": datetime.now().strftime("%Y-%m-%d"),
        })
    return pd.DataFrame(patients)

print("Generating patients...")
patients_df = generate_patients(NUM_PATIENTS)
print(f"  Generated {len(patients_df)} patients")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# GENERATE PROVIDERS
# ============================================================================

def generate_providers(n):
    providers = []
    for i in range(n):
        pid = f"PRV{i+1:05d}"
        gender = random.choice(["M", "F"])
        fn = random.choice(MALE_FIRST_NAMES) if gender == "M" else random.choice(FEMALE_FIRST_NAMES)
        ln = random.choice(LAST_NAMES)
        npi = f"{random.randint(1000000000, 9999999999)}"
        specialty = random.choice(SPECIALTIES)
        facility = random.choice(FACILITIES)
        providers.append({
            "provider_id": pid,
            "first_name": fn,
            "last_name": ln,
            "npi": npi,
            "specialty": specialty,
            "department": specialty,
            "facility_id": facility["id"],
            "facility_name": facility["name"],
            "phone": fake.phone_number()[:12],
            "email": f"dr.{ln.lower()}{i}@lakesidehealth.org",
            "status": random.choices(["Active", "Inactive", "On Leave"], weights=[0.9, 0.05, 0.05])[0],
            "hire_date": fake.date_between(start_date="-15y", end_date="-1y").strftime("%Y-%m-%d"),
        })
    return pd.DataFrame(providers)

print("Generating providers...")
providers_df = generate_providers(NUM_PROVIDERS)
print(f"  Generated {len(providers_df)} providers")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# GENERATE ENCOUNTERS
# ============================================================================

def calculate_readmission_risk(enc_type, los, total_charges, primary_icd, discharge_disposition):
    """Calculate readmission risk score with correlated clinical factors."""
    risk = 0.15  # base
    if enc_type in ("Inpatient", "Emergency"):
        risk += 0.10
    if los > 7:
        risk += 0.15
    elif los > 3:
        risk += 0.08
    if total_charges > 50000:
        risk += 0.10
    elif total_charges > 20000:
        risk += 0.05
    chronic_codes = {c["code"] for c in ICD_CODES if c.get("is_chronic")}
    if primary_icd in chronic_codes:
        risk += 0.12
    if primary_icd in ("I50.9", "J44.9", "N18.3"):
        risk += 0.10
    if discharge_disposition in ("SNF", "Rehab", "Home Health"):
        risk += 0.08
    elif discharge_disposition == "AMA":
        risk += 0.20
    risk += random.uniform(-0.05, 0.05)
    return round(min(max(risk, 0.01), 0.99), 4)

def generate_encounters(n, patient_ids, provider_ids):
    encounters = []
    icd_list = [c["code"] for c in ICD_CODES]
    icd_weights = [0.15, 0.12, 0.10, 0.08, 0.07, 0.06, 0.06, 0.05, 0.04, 0.04,
                   0.03, 0.03, 0.03, 0.03, 0.02, 0.02, 0.02, 0.02, 0.02, 0.01]

    for i in range(n):
        eid = f"ENC{i+1:08d}"
        pid = random.choice(patient_ids)
        prov = random.choice(provider_ids)
        enc_type = random.choices(ENCOUNTER_TYPES, weights=[0.25, 0.35, 0.20, 0.10, 0.10])[0]
        facility = random.choice(FACILITIES)

        admit_date = DATA_START_DATE + timedelta(days=random.randint(0, (DATA_END_DATE - DATA_START_DATE).days))

        if enc_type == "Inpatient":
            los = max(1, int(np.random.lognormal(1.2, 0.8)))
        elif enc_type == "Observation":
            los = random.choice([1, 2])
        elif enc_type == "Emergency":
            los = random.choices([0, 1, 2, 3], weights=[0.4, 0.3, 0.2, 0.1])[0]
        else:
            los = 0

        discharge_date = admit_date + timedelta(days=los)
        primary_icd = random.choices(icd_list, weights=icd_weights)[0]

        if enc_type in ("Inpatient", "Observation"):
            base_charge = random.uniform(5000, 80000)
        elif enc_type == "Emergency":
            base_charge = random.uniform(1500, 25000)
        else:
            base_charge = random.uniform(150, 2000)

        total_charges = round(base_charge * (1 + los * 0.15), 2)
        admission_type = random.choice(ADMISSION_TYPES) if enc_type in ("Inpatient", "Emergency") else None
        discharge_disp = random.choice(DISCHARGE_DISPOSITIONS) if los > 0 else "Home"

        risk = calculate_readmission_risk(enc_type, los, total_charges, primary_icd, discharge_disp)

        encounters.append({
            "encounter_id": eid,
            "patient_id": pid,
            "provider_id": prov,
            "encounter_type": enc_type,
            "admit_date": admit_date.strftime("%Y-%m-%d"),
            "discharge_date": discharge_date.strftime("%Y-%m-%d"),
            "length_of_stay": los,
            "primary_diagnosis_code": primary_icd,
            "facility_id": facility["id"],
            "admission_type": admission_type,
            "discharge_disposition": discharge_disp,
            "total_charges": total_charges,
            "readmission_risk": risk,
        })
    return pd.DataFrame(encounters)

print("Generating encounters...")
encounters_df = generate_encounters(NUM_ENCOUNTERS, patients_df["patient_id"].tolist(), providers_df["provider_id"].tolist())
print(f"  Generated {len(encounters_df)} encounters")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# GENERATE CLAIMS
# ============================================================================

def generate_claims(encounters_df):
    claims = []
    payer_ids = [p["payer_id"] for p in PAYERS]
    cpt_list = [c["code"] for c in CPT_CODES]

    for _, enc in encounters_df.iterrows():
        cid = enc["encounter_id"].replace("ENC", "CLM")
        claim_type = random.choice(CLAIM_TYPES)
        payer = random.choice(payer_ids)
        cpt = random.choice(cpt_list)
        billed = enc["total_charges"]
        allowed = round(billed * random.uniform(0.5, 0.9), 2)
        paid = round(allowed * random.uniform(0.6, 0.95), 2)
        status = random.choices(CLAIM_STATUSES, weights=[0.05, 0.05, 0.30, 0.08, 0.50, 0.02])[0]
        denial = random.choice(DENIAL_REASONS) if status == "Denied" else None

        submit_date = datetime.strptime(enc["discharge_date"], "%Y-%m-%d") + timedelta(days=random.randint(1, 14))
        process_date = submit_date + timedelta(days=random.randint(7, 45))

        claims.append({
            "claim_id": cid,
            "encounter_id": enc["encounter_id"],
            "patient_id": enc["patient_id"],
            "provider_id": enc["provider_id"],
            "payer_id": payer,
            "claim_type": claim_type,
            "cpt_code": cpt,
            "primary_diagnosis_code": enc["primary_diagnosis_code"],
            "service_date": enc["admit_date"],
            "submit_date": submit_date.strftime("%Y-%m-%d"),
            "process_date": process_date.strftime("%Y-%m-%d"),
            "billed_amount": billed,
            "allowed_amount": allowed,
            "paid_amount": paid if status != "Denied" else 0,
            "patient_responsibility": round(billed - paid if status != "Denied" else billed, 2),
            "claim_status": status,
            "denial_reason": denial,
        })
    return pd.DataFrame(claims)

print("Generating claims...")
claims_df = generate_claims(encounters_df)
print(f"  Generated {len(claims_df)} claims")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# GENERATE PRESCRIPTIONS
# ============================================================================

def generate_prescriptions(encounters_df, num_rx):
    prescriptions = []
    rx_id = 1

    for _, enc in encounters_df.iterrows():
        icd = enc["primary_diagnosis_code"]
        possible_meds = ICD_TO_MEDICATIONS.get(icd, [])
        if not possible_meds:
            possible_meds = [random.choice(MEDICATIONS)["rxnorm_code"]]

        # Chronic conditions get more fills
        icd_info = next((c for c in ICD_CODES if c["code"] == icd), None)
        is_chronic = icd_info["is_chronic"] if icd_info else False
        num_fills = random.randint(6, 12) if is_chronic else random.randint(1, 2)

        # Pick 1-2 medications per encounter
        num_meds = min(len(possible_meds), random.randint(1, 2))
        selected_meds = random.sample(possible_meds, num_meds)

        for med_code in selected_meds:
            med = MED_LOOKUP.get(med_code)
            if not med:
                continue

            fill_date = datetime.strptime(enc["admit_date"], "%Y-%m-%d")
            adherence = random.choices(
                ["adherent", "partial", "non_adherent"],
                weights=[0.70, 0.20, 0.10]
            )[0]

            for fill_num in range(num_fills):
                rxid = f"RX{rx_id:08d}"
                rx_id += 1
                days_supply = med["days_supply_typical"]
                cost = round(med["avg_cost"] * random.uniform(0.8, 1.3), 2)
                copay = round(cost * random.uniform(0.1, 0.3), 2)

                # Adherence affects fill gaps
                if adherence == "adherent":
                    gap = random.randint(0, 3)
                elif adherence == "partial":
                    gap = random.randint(5, 15)
                else:
                    gap = random.randint(15, 45)

                actual_fill = fill_date + timedelta(days=gap)
                if actual_fill > DATA_END_DATE:
                    break

                prescriptions.append({
                    "prescription_id": rxid,
                    "encounter_id": enc["encounter_id"],
                    "patient_id": enc["patient_id"],
                    "provider_id": enc["provider_id"],
                    "rxnorm_code": med_code,
                    "medication_name": med["medication_name"],
                    "fill_date": actual_fill.strftime("%Y-%m-%d"),
                    "days_supply": days_supply,
                    "quantity": random.randint(30, 90),
                    "refill_number": fill_num,
                    "total_cost": cost,
                    "copay_amount": copay,
                    "pharmacy_id": f"PHR{random.randint(1, 50):04d}",
                    "prescriber_id": enc["provider_id"],
                    "is_generic": random.choices([True, False], weights=[0.8, 0.2])[0],
                    "prior_auth_required": random.choices([True, False], weights=[0.1, 0.9])[0],
                })

                fill_date = actual_fill + timedelta(days=days_supply)

                if rx_id > num_rx:
                    break
            if rx_id > num_rx:
                break
        if rx_id > num_rx:
            break

    return pd.DataFrame(prescriptions)

print("Generating prescriptions...")
prescriptions_df = generate_prescriptions(encounters_df, NUM_PRESCRIPTIONS)
print(f"  Generated {len(prescriptions_df)} prescriptions")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# GENERATE DIAGNOSES  (1-3 per encounter, with comorbidity patterns)
# ============================================================================

COMORBIDITY_MAP = {
    "I10":     [("E78.5", 0.4), ("E11.9", 0.3), ("I25.10", 0.2), ("N18.3", 0.15)],
    "E11.9":   [("I10", 0.5), ("E78.5", 0.4), ("N18.3", 0.2), ("I25.10", 0.15)],
    "I50.9":   [("I10", 0.6), ("I25.10", 0.4), ("N18.3", 0.3), ("J44.9", 0.2)],
    "I25.10":  [("I10", 0.5), ("E78.5", 0.4), ("E11.9", 0.2)],
    "J44.9":   [("J45.909", 0.3), ("I10", 0.2), ("I50.9", 0.15)],
    "N18.3":   [("I10", 0.5), ("E11.9", 0.4), ("I50.9", 0.2)],
    "J18.9":   [("J44.9", 0.2), ("J45.909", 0.15), ("I50.9", 0.1)],
    "F32.9":   [("G43.909", 0.2), ("M54.5", 0.15)],
}

def generate_diagnoses(encounters_df):
    diagnoses = []
    dx_id = 1
    icd_list = [c["code"] for c in ICD_CODES]

    for _, enc in encounters_df.iterrows():
        primary = enc["primary_diagnosis_code"]
        # Principal diagnosis
        diagnoses.append({
            "diagnosis_id": f"DX{dx_id:08d}",
            "encounter_id": enc["encounter_id"],
            "patient_id": enc["patient_id"],
            "icd_code": primary,
            "diagnosis_type": "Principal",
            "sequence_number": 1,
            "diagnosis_date": enc["admit_date"],
            "present_on_admission": random.choices(["Y", "N", "U"], weights=[0.8, 0.1, 0.1])[0],
        })
        dx_id += 1

        # Secondary diagnoses based on enc type
        enc_type = enc["encounter_type"]
        if enc_type == "Inpatient":
            num_secondary = random.choices([0, 1, 2], weights=[0.2, 0.5, 0.3])[0]
        elif enc_type in ("Emergency", "Observation"):
            num_secondary = random.choices([0, 1, 2], weights=[0.4, 0.4, 0.2])[0]
        else:
            num_secondary = random.choices([0, 1], weights=[0.6, 0.4])[0]

        used_codes = {primary}
        combos = COMORBIDITY_MAP.get(primary, [])

        for seq in range(num_secondary):
            if combos:
                # Weighted comorbidity selection
                candidate = None
                for code, prob in combos:
                    if code not in used_codes and random.random() < prob:
                        candidate = code
                        break
                if not candidate:
                    candidate = random.choice([c for c in icd_list if c not in used_codes])
            else:
                candidate = random.choice([c for c in icd_list if c not in used_codes])

            used_codes.add(candidate)
            diagnoses.append({
                "diagnosis_id": f"DX{dx_id:08d}",
                "encounter_id": enc["encounter_id"],
                "patient_id": enc["patient_id"],
                "icd_code": candidate,
                "diagnosis_type": "Secondary",
                "sequence_number": seq + 2,
                "diagnosis_date": enc["admit_date"],
                "present_on_admission": random.choices(["Y", "N", "U"], weights=[0.6, 0.25, 0.15])[0],
            })
            dx_id += 1

    return pd.DataFrame(diagnoses)

print("Generating diagnoses...")
diagnoses_df = generate_diagnoses(encounters_df)
print(f"  Generated {len(diagnoses_df)} diagnoses")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# GENERATE SDOH DATA
# ============================================================================

STATES_CONFIG = {
    "MI": {"zips": range(48001, 49972), "urban_pct": 0.45, "suburban_pct": 0.35, "lat_range": (41.70, 46.00), "lon_range": (-86.80, -82.40)},
    "NY": {"zips": range(10001, 14976), "urban_pct": 0.55, "suburban_pct": 0.30, "lat_range": (40.50, 45.00), "lon_range": (-79.80, -71.80)},
    "OH": {"zips": range(43001, 45999), "urban_pct": 0.40, "suburban_pct": 0.35, "lat_range": (38.40, 42.00), "lon_range": (-84.80, -80.50)},
    "TX": {"zips": range(75001, 79999), "urban_pct": 0.50, "suburban_pct": 0.30, "lat_range": (25.80, 36.50), "lon_range": (-106.60, -93.50)},
    "CA": {"zips": range(90001, 96162), "urban_pct": 0.55, "suburban_pct": 0.30, "lat_range": (32.50, 42.00), "lon_range": (-124.40, -114.10)},
    "FL": {"zips": range(32003, 34997), "urban_pct": 0.45, "suburban_pct": 0.35, "lat_range": (24.50, 31.00), "lon_range": (-87.60, -80.00)},
    "PA": {"zips": range(15001, 19640), "urban_pct": 0.45, "suburban_pct": 0.35, "lat_range": (39.70, 42.30), "lon_range": (-80.50, -74.70)},
    "IL": {"zips": range(60001, 62999), "urban_pct": 0.50, "suburban_pct": 0.30, "lat_range": (37.00, 42.50), "lon_range": (-91.50, -87.50)},
}

def generate_sdoh():
    sdoh_data = []
    for state, config in STATES_CONFIG.items():
        zips = list(config["zips"])
        sample_size = min(70, len(zips))
        selected = random.sample(zips, sample_size)
        for z in selected:
            locale = random.choices(
                ["Urban", "Suburban", "Rural"],
                weights=[config["urban_pct"], config["suburban_pct"], 1 - config["urban_pct"] - config["suburban_pct"]]
            )[0]

            if locale == "Urban":
                income = random.randint(35000, 85000)
                uninsured = round(random.uniform(0.08, 0.22), 3)
                food_insecure = round(random.uniform(0.10, 0.25), 3)
            elif locale == "Suburban":
                income = random.randint(55000, 120000)
                uninsured = round(random.uniform(0.04, 0.12), 3)
                food_insecure = round(random.uniform(0.05, 0.15), 3)
            else:
                income = random.randint(28000, 65000)
                uninsured = round(random.uniform(0.12, 0.30), 3)
                food_insecure = round(random.uniform(0.15, 0.35), 3)

            poverty = round(random.uniform(0.05, 0.35), 3)
            unemployment = round(random.uniform(0.03, 0.12), 3)
            no_vehicle = round(random.uniform(0.02, 0.25), 3)
            composite = round((poverty * 0.25 + uninsured * 0.20 + food_insecure * 0.20 +
                               unemployment * 0.15 + no_vehicle * 0.10 +
                               (1 - income / 120000) * 0.10), 4)
            risk_tier = "High" if composite > 0.25 else ("Medium" if composite > 0.15 else "Low")

            sdoh_data.append({
                "zip_code": str(z).zfill(5),
                "state": state,
                "locale_type": locale,
                "median_household_income": income,
                "poverty_rate": poverty,
                "unemployment_rate": unemployment,
                "uninsured_rate": uninsured,
                "food_insecurity_rate": food_insecure,
                "no_vehicle_pct": no_vehicle,
                "composite_svi_score": composite,
                "risk_tier": risk_tier,
                "latitude": round(random.uniform(*config["lat_range"]), 4),
                "longitude": round(random.uniform(*config["lon_range"]), 4),
            })
    return pd.DataFrame(sdoh_data)

print("Generating SDOH data...")
sdoh_df = generate_sdoh()
print(f"  Generated {len(sdoh_df)} SDOH zip records")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# GENERATE MONITORS (reference data for IoT/RPM)
# ============================================================================

def generate_monitors():
    monitors = []
    mid = 1
    for mt in MONITOR_TYPES:
        for model in mt["models"]:
            monitors.append({
                "monitor_id": f"MON{mid:04d}",
                "monitor_type": mt["type"],
                "manufacturer": mt["manufacturer"],
                "model": model,
                "connectivity": random.choice(["Bluetooth", "WiFi", "Cellular", "USB"]),
                "battery_life_days": random.randint(7, 365),
                "fda_cleared": random.choices([True, False], weights=[0.85, 0.15])[0],
                "unit_cost": round(random.uniform(25, 500), 2),
            })
            mid += 1
    return pd.DataFrame(monitors)

monitors_df = generate_monitors()
print(f"  Generated {len(monitors_df)} monitor records")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# GENERATE HEDIS CARE GAP STATUS PER PATIENT
# ============================================================================
# Care gaps are the foundation for the RTI Care Gap Closure use case.
# When a patient arrives (ADT event), we check their gap status in real-time.

HEDIS_MEASURES = [
    {"measure_id": "CDC", "measure_name": "Comprehensive Diabetes Care", "description": "HbA1c testing for diabetics", "target_icd": ["E11.9"], "frequency_months": 12, "age_min": 18, "age_max": 75},
    {"measure_id": "COL", "measure_name": "Colorectal Cancer Screening", "description": "FIT or colonoscopy", "target_icd": [], "frequency_months": 12, "age_min": 45, "age_max": 75},
    {"measure_id": "BCS", "measure_name": "Breast Cancer Screening", "description": "Mammography for women", "target_icd": [], "frequency_months": 24, "age_min": 50, "age_max": 74},
    {"measure_id": "SPC", "measure_name": "Statin Therapy - Cholesterol", "description": "LDL-C test for statin users", "target_icd": ["E78.5", "I25.10"], "frequency_months": 12, "age_min": 21, "age_max": 75},
    {"measure_id": "CBP", "measure_name": "Controlling Blood Pressure", "description": "BP control <140/90", "target_icd": ["I10"], "frequency_months": 12, "age_min": 18, "age_max": 85},
    {"measure_id": "SPD", "measure_name": "Statin Use in Diabetes", "description": "Statin prescribed for diabetics 40-75", "target_icd": ["E11.9"], "frequency_months": 12, "age_min": 40, "age_max": 75},
    {"measure_id": "OMW", "measure_name": "Osteoporosis Management in Women", "description": "BMD test or treatment after fracture", "target_icd": ["S72.001A"], "frequency_months": 6, "age_min": 67, "age_max": 85},
    {"measure_id": "PPC", "measure_name": "Prenatal and Postpartum Care", "description": "Timely prenatal visits", "target_icd": [], "frequency_months": 12, "age_min": 15, "age_max": 44},
]

def generate_care_gaps(patients_df, diagnoses_df):
    """Generate care gap status for eligible patients based on their conditions."""
    care_gaps = []

    # Build patient→diagnoses lookup
    pt_dx = {}
    for _, row in diagnoses_df.iterrows():
        pid = row["patient_id"]
        if pid not in pt_dx:
            pt_dx[pid] = set()
        pt_dx[pid].add(row["icd_code"])

    for _, patient in patients_df.iterrows():
        pid = patient["patient_id"]
        dob = datetime.strptime(patient["date_of_birth"], "%Y-%m-%d")
        age = (datetime.now() - dob).days // 365
        gender = patient["gender"]
        dx_set = pt_dx.get(pid, set())

        for measure in HEDIS_MEASURES:
            # Check age eligibility
            if age < measure["age_min"] or age > measure["age_max"]:
                continue

            # Check gender-specific (BCS is female only)
            if measure["measure_id"] == "BCS" and gender != "F":
                continue

            # Check condition-specific eligibility
            if measure["target_icd"]:
                if not dx_set.intersection(measure["target_icd"]):
                    continue

            # Simulate gap status: ~30% of eligible patients have open gaps
            is_gap_open = random.random() < 0.30
            last_service = None
            if not is_gap_open:
                months_ago = random.randint(1, measure["frequency_months"])
                last_service = (datetime.now() - timedelta(days=months_ago * 30)).strftime("%Y-%m-%d")

            care_gaps.append({
                "patient_id": pid,
                "measure_id": measure["measure_id"],
                "measure_name": measure["measure_name"],
                "is_gap_open": is_gap_open,
                "last_service_date": last_service,
                "due_date": (datetime.now() - timedelta(days=random.randint(-60, 180))).strftime("%Y-%m-%d") if is_gap_open else None,
                "gap_days_overdue": random.randint(0, 365) if is_gap_open else 0,
            })

    return pd.DataFrame(care_gaps)

print("Generating HEDIS care gap data...")
care_gaps_df = generate_care_gaps(patients_df, diagnoses_df)
print(f"  Generated {len(care_gaps_df)} care gap records")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# WRITE CSV FILES TO ONELAKE (lh_bronze_raw/Files/)
# ============================================================================
# Use absolute OneLake paths so this works both when run directly (with default
# lakehouse) and when called via notebookutils.notebook.run() from the launcher.

import requests

def write_csv_to_lakehouse(df, path):
    """Write a pandas DataFrame as CSV to OneLake via notebookutils."""
    csv_content = df.to_csv(index=False)
    notebookutils.fs.put(path, csv_content, True)
    print(f"  Written: {path.split('/')[-1]} ({len(df):,} rows)")

# Resolve absolute ABFSS path to lh_bronze_raw
ws_id = spark.conf.get("trident.artifact.workspace.id")
token = notebookutils.credentials.getToken("pbi")
resp = requests.get(
    f"https://api.fabric.microsoft.com/v1/workspaces/{ws_id}/items?type=Lakehouse",
    headers={"Authorization": f"Bearer {token}"}
)
lakehouses = {lh["displayName"]: lh["id"] for lh in resp.json().get("value", [])}
lh_id = lakehouses.get("lh_bronze_raw")

if lh_id:
    FILES_BASE = f"abfss://{ws_id}@onelake.dfs.fabric.microsoft.com/{lh_id}/Files"
    print(f"Resolved lh_bronze_raw ({lh_id})")
else:
    FILES_BASE = "Files"
    print("WARNING: lh_bronze_raw not found, using relative path")

# Transactional CSVs → root of Files/
print("\nWriting transactional CSVs...")
write_csv_to_lakehouse(patients_df, f"{FILES_BASE}/patients.csv")
write_csv_to_lakehouse(providers_df, f"{FILES_BASE}/providers.csv")
write_csv_to_lakehouse(encounters_df, f"{FILES_BASE}/encounters.csv")
write_csv_to_lakehouse(claims_df, f"{FILES_BASE}/claims.csv")
write_csv_to_lakehouse(prescriptions_df, f"{FILES_BASE}/prescriptions.csv")
write_csv_to_lakehouse(diagnoses_df, f"{FILES_BASE}/diagnoses.csv")

# Metadata CSVs → Files/metadata/
print("\nWriting metadata CSVs...")
write_csv_to_lakehouse(pd.DataFrame(ICD_CODES), f"{FILES_BASE}/metadata/icd_codes.csv")
write_csv_to_lakehouse(pd.DataFrame(CPT_CODES), f"{FILES_BASE}/metadata/cpt_codes.csv")
write_csv_to_lakehouse(pd.DataFrame(PAYERS), f"{FILES_BASE}/metadata/payers.csv")
write_csv_to_lakehouse(pd.DataFrame(FACILITIES), f"{FILES_BASE}/metadata/facilities.csv")
write_csv_to_lakehouse(pd.DataFrame(MEDICATIONS), f"{FILES_BASE}/metadata/medications_ref.csv")
write_csv_to_lakehouse(monitors_df, f"{FILES_BASE}/metadata/monitors.csv")
write_csv_to_lakehouse(sdoh_df, f"{FILES_BASE}/metadata/sdoh_zipcode.csv")
write_csv_to_lakehouse(pd.DataFrame(HEDIS_MEASURES), f"{FILES_BASE}/metadata/hedis_measures.csv")
write_csv_to_lakehouse(care_gaps_df, f"{FILES_BASE}/care_gaps.csv")

print("\n✅ All data generated and written to lh_bronze_raw/Files/")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# WRITE care_gaps AND hedis_measures TO lh_bronze_raw (Delta tables)
# ============================================================================
# These are reference/seed tables generated alongside the sample data.
# They belong in bronze -- the RTI Care Gap Alerts notebook reads them
# from lh_bronze_raw.care_gaps and lh_bronze_raw.hedis_measures.
print("\nWriting care_gaps and hedis_measures to lh_bronze_raw...")

if lh_id:
    # care_gaps → lh_bronze_raw.care_gaps
    spark_care_gaps = spark.createDataFrame(care_gaps_df)
    spark_care_gaps.write.format("delta").mode("overwrite").option(
        "path",
        f"abfss://{ws_id}@onelake.dfs.fabric.microsoft.com/{lh_id}/Tables/care_gaps"
    ).save()
    print(f"  Written: lh_bronze_raw.care_gaps ({len(care_gaps_df):,} rows)")

    # hedis_measures → lh_bronze_raw.hedis_measures
    hedis_df = pd.DataFrame(HEDIS_MEASURES)
    spark_hedis = spark.createDataFrame(hedis_df)
    spark_hedis.write.format("delta").mode("overwrite").option(
        "path",
        f"abfss://{ws_id}@onelake.dfs.fabric.microsoft.com/{lh_id}/Tables/hedis_measures"
    ).save()
    print(f"  Written: lh_bronze_raw.hedis_measures ({len(hedis_df):,} rows)")
else:
    print("  WARNING: lh_bronze_raw not found -- care_gaps/hedis_measures not written as Delta.")
    print("  They are still available as CSV in lh_bronze_raw/Files/.")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# SUMMARY
# ============================================================================
print("=" * 60)
print("  DATA GENERATION SUMMARY")
print("=" * 60)
print(f"  Patients:       {len(patients_df):>10,}")
print(f"  Providers:      {len(providers_df):>10,}")
print(f"  Encounters:     {len(encounters_df):>10,}")
print(f"  Claims:         {len(claims_df):>10,}")
print(f"  Prescriptions:  {len(prescriptions_df):>10,}")
print(f"  Diagnoses:      {len(diagnoses_df):>10,}")
print(f"  ICD Codes:      {len(ICD_CODES):>10,}")
print(f"  CPT Codes:      {len(CPT_CODES):>10,}")
print(f"  Payers:         {len(PAYERS):>10,}")
print(f"  Facilities:     {len(FACILITIES):>10,}")
print(f"  Medications:    {len(MEDICATIONS):>10,}")
print(f"  Monitors:       {len(monitors_df):>10,}")
print(f"  SDOH Zips:      {len(sdoh_df):>10,}")
print(f"  HEDIS Measures: {len(HEDIS_MEASURES):>10,}")
print(f"  Care Gaps:      {len(care_gaps_df):>10,}")
print(f"  Date Range:     {DATA_START_DATE.strftime('%Y-%m-%d')} → {DATA_END_DATE.strftime('%Y-%m-%d')}")
print("=" * 60)
