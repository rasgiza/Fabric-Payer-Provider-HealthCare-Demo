# Ontology & Graph Model Setup Guide

> **Healthcare Analytics on Microsoft Fabric - FabricDemoHLS**

After your Gold lakehouse tables are populated and the semantic model (`HealthcareDemoHLS`) is deployed, create the **Ontology + linked Graph Model** from the semantic model in the Fabric UI. This approach ensures the ontology and graph are **fully linked** - enabling Fabric IQ graph traversal, Copilot integration, and visual exploration.

> **Why from the semantic model?** Creating the ontology from the semantic model auto-generates entity types and properties from all 13 tables. You then rename entities, set keys/display names, replace the auto-generated relationships with curated ones, and build the graph - all in the UI. This avoids the Fabric Preview API limitation where ontology + graph deploy as **unlinked** items.

---

## Prerequisites

- `lh_gold_curated` lakehouse with all Gold tables populated (run `PL_Healthcare_Master` with `load_mode=full` first)
- `HealthcareDemoHLS` semantic model deployed (Step 5 of `deploy_all.py`)
- Contributor or Admin role on the workspace

---

## Step 1 - Create Ontology from Semantic Model

1. Open your Fabric workspace
2. Click **+ New item** -> search for **Ontology** -> select it
3. Name it: `Healthcare_Demo_Ontology_HLS`
4. Select **Semantic model** as the data source -> choose `HealthcareDemoHLS`
5. Click **Create**

Fabric auto-generates **13 entity types** (one per SM table) and **~22 relationships** (from SM foreign keys). You will now clean these up.

---

## Step 2 - Delete Unwanted Entity Types

The semantic model has 3 tables that should **not** be in the ontology (they are analytical/aggregate tables, not domain entities). Delete these:

| Entity to Delete | Source Table | Why Remove |
|---|---|---|
| `dim_date` | `dim_date` | Date dimension - not a domain entity, relationships use date keys directly |
| `agg_medication_adherence` | `agg_medication_adherence` | Pre-aggregated analytics table, not a source-of-truth entity |
| `agg_readmission_by_date` | `agg_readmission_by_date` | Pre-aggregated analytics table, not a source-of-truth entity |

For each: select the entity -> click **Delete** (or the trash icon).

You should have **10 entity types** remaining.

---

## Step 3 - Rename Entities & Configure Keys

For each of the 10 remaining entities, update the **Name**, **Source Key** (primary key), and **Instance Display Name** (the label shown on graph nodes and in lookups).

### Master Entity Configuration Table

| # | Auto-Generated Name | Rename To | Source Key (Primary Key) | Instance Display Name |
|---|---|---|---|---|
| 1 | `dim_patient` | **Patient** | `patient_key` (BigInt) | `patient_id` |
| 2 | `fact_encounter` | **Encounter** | `encounter_key` (BigInt) | `encounter_id` |
| 3 | `fact_claim` | **Claim** | `claim_key` (BigInt) | `claim_id` |
| 4 | `dim_diagnosis` | **Diagnosis** | `diagnosis_key` (BigInt) | `icd_description` |
| 5 | `fact_diagnosis` | **PatientDiagnosis** | `fact_diagnosis_key` (BigInt) | `diagnosis_id` |
| 6 | `dim_provider` | **Provider** | `provider_key` (BigInt) | `provider_id` |
| 7 | `fact_prescription` | **Prescription** | `prescription_key` (BigInt) | `prescription_id` |
| 8 | `dim_medication` | **Medication** | `medication_key` (BigInt) | `medication_name` |
| 9 | `dim_payer` | **Payer** | `payer_key` (BigInt) | `payer_name` |
| 10 | `dim_sdoh` | **CommunityHealth** | `zip_code` (String) | `zip_code` |

> **Tip:** Properties (columns) are auto-imported from the semantic model - you generally do not need to add or remove them. Just verify the source key and display name are set correctly.

---

## Step 4 - Replace Relationships

The auto-generated relationships from the semantic model use generic FK names and include relationships to the deleted entities (`dim_date`, `agg_*`). **Delete all auto-generated relationships**, then manually add the 15 curated relationships below.

### 4a - Delete All Auto-Generated Relationships

Go to the **Relationships** section and delete every relationship that was auto-created. These were generated from the semantic model's 22 foreign keys and do not match the domain-specific naming or structure we need.

### 4b - Add Curated Relationships (15 total)

For each relationship: click **+ Add relationship** -> set the Name, Source Entity, Target Entity, and key columns.

> **Key concept:** The *Source Key Column* is the foreign key in the source entity's table. The *Target Key Column* is the primary key of the target entity's table.

### Master Relationship Table

| # | Relationship Name | Source Entity | Target Entity | Source Key Column | Target Key Column |
|---|---|---|---|---|---|
| 1 | **involves** | Encounter | Patient | `patient_key` | `patient_key` |
| 2 | **treatedBy** | Encounter | Provider | `provider_key` | `provider_key` |
| 3 | **covers** | Claim | Patient | `patient_key` | `patient_key` |
| 4 | **submittedBy** | Claim | Provider | `provider_key` | `provider_key` |
| 5 | **ClaimHasPayer** | Claim | Payer | `payer_key` | `payer_key` |
| 6 | **billsFor** | Claim | Encounter | `encounter_key` | `encounter_key` |
| 7 | **serves** | Prescription | Patient | `patient_key` | `patient_key` |
| 8 | **prescribedBy** | Prescription | Provider | `provider_key` | `provider_key` |
| 9 | **PrescriptionHasPayer** | Prescription | Payer | `payer_key` | `payer_key` |
| 10 | **dispenses** | Prescription | Medication | `medication_key` | `medication_key` |
| 11 | **originatesFrom** | Prescription | Encounter | `encounter_key` | `encounter_key` |
| 12 | **affects** | PatientDiagnosis | Patient | `patient_key` | `patient_key` |
| 13 | **references** | PatientDiagnosis | Diagnosis | `diagnosis_key` | `diagnosis_key` |
| 14 | **occursIn** | PatientDiagnosis | Encounter | `encounter_key` | `encounter_key` |
| 15 | **livesIn** | Patient | CommunityHealth | `zip_code` | `zip_code` |

---

## Step 5 - Build the Graph

1. After saving all entity types and relationships, go to the **Graph** tab
2. Click **Build a graph**
3. Select all 10 entity types and all 15 relationships
4. Fabric generates the graph model and loads data automatically (~5-15 minutes)

**Result:** The ontology and graph model are **linked**. The Graph tab shows visual nodes and edges. Fabric IQ graph traversal features are active.

---

## Step 6 - Verify

1. **Graph tab** - confirm you see 10 node types and 15 edge types with data loaded
2. **Entity explorer** - click any entity (e.g., Patient) and verify instances appear with the correct display name
3. **Relationship traversal** - click a Patient node -> verify you see linked Encounters, Claims, Prescriptions

---

## Step 7 - Deploy Data Agent

After the ontology is set up, deploy the Data Agent:

```bash
python 06_deploy_data_agent.py
```

Or run: `python deploy_all.py --from 7`

> **Important:** The data agent uses `lh_gold_curated` (the lakehouse) as its data source - not the ontology. The ontology serves as a visual/conceptual layer for Copilot and graph exploration. Analytics queries (denial rates, readmission trends, aggregations) go through the lakehouse via SQL. See the Readme for details.

---

## Entity Properties Reference

These properties are auto-imported when you create the ontology from the semantic model. Use this reference to verify all columns came through correctly.

### Patient (`dim_patient`)

| Property | Type | Column | Key / Display |
|----------|------|--------|---------------|
| patient_key | BigInt | patient_key | **Source Key** |
| patient_id | String | patient_id | **Display Name** |
| first_name | String | first_name | |
| last_name | String | last_name | |
| date_of_birth | DateTime | date_of_birth | |
| gender | String | gender | |
| address | String | address | |
| city | String | city | |
| state | String | state | |
| zip_code | String | zip_code | FK -> CommunityHealth |
| phone | String | phone | |
| email | String | email | |
| insurance_type | String | insurance_type | |
| insurance_provider | String | insurance_provider | |
| insurance_policy_number | String | insurance_policy_number | |
| age | BigInt | age | |
| age_group | String | age_group | |
| is_current | BigInt | is_current | |
| effective_start_date | DateTime | effective_start_date | |
| effective_end_date | DateTime | effective_end_date | |
| load_timestamp | DateTime | _load_timestamp | |

**Relationships from Patient:** livesIn -> CommunityHealth (via `zip_code`)
**Relationships to Patient:** involves (Encounter), covers (Claim), serves (Prescription), affects (PatientDiagnosis)

---

### Encounter (`fact_encounter`)

| Property | Type | Column | Key / Display |
|----------|------|--------|---------------|
| encounter_key | BigInt | encounter_key | **Source Key** |
| encounter_id | String | encounter_id | **Display Name** |
| encounter_date_key | BigInt | encounter_date_key | |
| discharge_date_key | BigInt | discharge_date_key | |
| patient_key | BigInt | patient_key | FK -> Patient |
| provider_key | BigInt | provider_key | FK -> Provider |
| facility_key | BigInt | facility_key | |
| encounter_type | String | encounter_type | |
| admission_type | String | admission_type | |
| discharge_disposition | String | discharge_disposition | |
| length_of_stay | BigInt | length_of_stay | |
| total_charges | Double | total_charges | |
| total_cost | Double | total_cost | |
| readmission_flag | BigInt | readmission_flag | |
| readmission_risk_score | Double | readmission_risk_score | |
| readmission_risk_category | String | readmission_risk_category | |

**Relationships from Encounter:** involves -> Patient, treatedBy -> Provider
**Relationships to Encounter:** billsFor (Claim), originatesFrom (Prescription), occursIn (PatientDiagnosis)

---

### Claim (`fact_claim`)

| Property | Type | Column | Key / Display |
|----------|------|--------|---------------|
| claim_key | BigInt | claim_key | **Source Key** |
| claim_id | String | claim_id | **Display Name** |
| claim_date_key | BigInt | claim_date_key | |
| payment_date_key | BigInt | payment_date_key | |
| patient_key | BigInt | patient_key | FK -> Patient |
| provider_key | BigInt | provider_key | FK -> Provider |
| payer_key | BigInt | payer_key | FK -> Payer |
| encounter_key | BigInt | encounter_key | FK -> Encounter |
| facility_key | BigInt | facility_key | |
| claim_type | String | claim_type | |
| claim_status | String | claim_status | |
| billed_amount | Double | billed_amount | |
| allowed_amount | Double | allowed_amount | |
| paid_amount | Double | paid_amount | |
| denial_flag | BigInt | denial_flag | |
| denial_risk_score | Double | denial_risk_score | |
| denial_risk_category | String | denial_risk_category | |
| primary_denial_reason | String | primary_denial_reason | |
| recommended_action | String | recommended_action | |
| load_timestamp | DateTime | _load_timestamp | |

**Relationships from Claim:** covers -> Patient, submittedBy -> Provider, ClaimHasPayer -> Payer, billsFor -> Encounter

---

### Diagnosis (`dim_diagnosis`)

| Property | Type | Column | Key / Display |
|----------|------|--------|---------------|
| diagnosis_key | BigInt | diagnosis_key | **Source Key** |
| icd_description | String | icd_description | **Display Name** |
| icd_code | String | icd_code | |
| icd_category | String | icd_category | |
| is_chronic | BigInt | is_chronic | |
| is_active | BigInt | is_active | |
| load_timestamp | DateTime | _load_timestamp | |

**Relationships to Diagnosis:** references (PatientDiagnosis)

---

### PatientDiagnosis (`fact_diagnosis`)

| Property | Type | Column | Key / Display |
|----------|------|--------|---------------|
| fact_diagnosis_key | BigInt | fact_diagnosis_key | **Source Key** |
| diagnosis_id | String | diagnosis_id | **Display Name** |
| encounter_key | BigInt | encounter_key | FK -> Encounter |
| diagnosis_date_key | BigInt | diagnosis_date_key | |
| patient_key | BigInt | patient_key | FK -> Patient |
| diagnosis_key | BigInt | diagnosis_key | FK -> Diagnosis |
| facility_key | BigInt | facility_key | |
| icd_code | String | icd_code | |
| diagnosis_sequence | BigInt | diagnosis_sequence | |
| diagnosis_type | String | diagnosis_type | |
| present_on_admission | String | present_on_admission | |
| load_timestamp | DateTime | _load_timestamp | |

**Relationships from PatientDiagnosis:** affects -> Patient, references -> Diagnosis, occursIn -> Encounter

---

### Provider (`dim_provider`)

| Property | Type | Column | Key / Display |
|----------|------|--------|---------------|
| provider_key | BigInt | provider_key | **Source Key** |
| provider_id | String | provider_id | **Display Name** |
| first_name | String | first_name | |
| last_name | String | last_name | |
| display_name | String | display_name | |
| npi_number | String | npi_number | |
| specialty | String | specialty | |
| department | String | department | |
| facility_id | String | facility_id | |
| is_active | BigInt | is_active | |
| is_current | BigInt | is_current | |
| effective_start_date | DateTime | effective_start_date | |
| effective_end_date | DateTime | effective_end_date | |
| load_timestamp | DateTime | _load_timestamp | |

**Relationships to Provider:** treatedBy (Encounter), submittedBy (Claim), prescribedBy (Prescription)

---

### Prescription (`fact_prescription`)

| Property | Type | Column | Key / Display |
|----------|------|--------|---------------|
| prescription_key | BigInt | prescription_key | **Source Key** |
| prescription_id | String | prescription_id | **Display Name** |
| prescription_group_id | String | prescription_group_id | |
| fill_date_key | BigInt | fill_date_key | |
| patient_key | BigInt | patient_key | FK -> Patient |
| provider_key | BigInt | provider_key | FK -> Provider |
| payer_key | BigInt | payer_key | FK -> Payer |
| encounter_key | BigInt | encounter_key | FK -> Encounter |
| medication_key | BigInt | medication_key | FK -> Medication |
| facility_key | BigInt | facility_key | |
| fill_number | BigInt | fill_number | |
| days_supply | BigInt | days_supply | |
| quantity_dispensed | BigInt | quantity_dispensed | |
| refills_authorized | BigInt | refills_authorized | |
| is_generic | BigInt | is_generic | |
| is_chronic_medication | BigInt | is_chronic_medication | |
| pharmacy_type | String | pharmacy_type | |
| total_cost | Double | total_cost | |
| payer_paid | Double | payer_paid | |
| patient_copay | Double | patient_copay | |
| prescribing_reason_code | String | prescribing_reason_code | |
| load_timestamp | DateTime | _load_timestamp | |

**Relationships from Prescription:** serves -> Patient, prescribedBy -> Provider, PrescriptionHasPayer -> Payer, dispenses -> Medication, originatesFrom -> Encounter

---

### Medication (`dim_medication`)

| Property | Type | Column | Key / Display |
|----------|------|--------|---------------|
| medication_key | BigInt | medication_key | **Source Key** |
| medication_name | String | medication_name | **Display Name** |
| rxnorm_code | String | rxnorm_code | |
| generic_name | String | generic_name | |
| drug_class | String | drug_class | |
| therapeutic_area | String | therapeutic_area | |
| route | String | route | |
| form | String | form | |
| strength | String | strength | |
| is_chronic | BigInt | is_chronic | |
| is_active | BigInt | is_active | |
| load_timestamp | DateTime | _load_timestamp | |

**Relationships to Medication:** dispenses (Prescription)

---

### Payer (`dim_payer`)

| Property | Type | Column | Key / Display |
|----------|------|--------|---------------|
| payer_key | BigInt | payer_key | **Source Key** |
| payer_name | String | payer_name | **Display Name** |
| payer_id | String | payer_id | |
| payer_type | String | payer_type | |
| is_active | BigInt | is_active | |
| load_timestamp | DateTime | _load_timestamp | |

**Relationships to Payer:** ClaimHasPayer (Claim), PrescriptionHasPayer (Prescription)

---

### CommunityHealth (`dim_sdoh`)

| Property | Type | Column | Key / Display |
|----------|------|--------|---------------|
| zip_code | String | zip_code | **Source Key + Display Name** |
| sdoh_key | BigInt | sdoh_key | |
| state | String | state | |
| poverty_rate | Double | poverty_rate | |
| food_desert_flag | BigInt | food_desert_flag | |
| transportation_score | Double | transportation_score | |
| housing_instability_rate | Double | housing_instability_rate | |
| uninsured_rate | Double | uninsured_rate | |
| broadband_access_pct | Double | broadband_access_pct | |
| median_household_income | BigInt | median_household_income | |
| population | BigInt | population | |
| social_vulnerability_index | Double | social_vulnerability_index | |
| risk_tier | String | risk_tier | |
| is_active | BigInt | is_active | |
| load_timestamp | DateTime | _load_timestamp | |

**Relationships to CommunityHealth:** livesIn (Patient)

---

## Alternative - API Deployment (Unlinked)

If you prefer automated deployment (CI/CD, repeatable environments), the API scripts deploy ontology and graph as **separate, unlinked items**:

```bash
python 05_deploy_ontology.py        # Schema-only ontology (10 entities, 15 relationships)
python 05b_deploy_graph_model.py     # Standalone graph model (loads data independently)
```

> **Limitation:** The Fabric Preview API (as of March 2026) has no endpoint to link an ontology to a graph model. The ontology's Graph tab remains empty, and graph traversal through the ontology does not activate. Use the UI approach (Steps 1-6 above) for full linked functionality. See `KNOWN_LIMITATIONS.md` section 1.7.

---

## Data Model Reference - Entity Relationship Diagram

```
                    +------------------+
                    |  CommunityHealth  |
                    |  (dim_sdoh)       |
                    |  PK: zip_code     |
                    +--------^---------+
                             | livesIn
                    +--------+----------+
                    |     Patient       |
                    |  (dim_patient)    |
                    |  PK: patient_key  |
                    +--^--^--^--^-------+
                       |  |  |  |
          +------------+  |  |  +----------------+
          | involves      |  | covers             | serves
          |               |  |                    |
   +------+------+  +----+--+----+       +------+---------+
   |  Encounter  |  |   Claim    |       |  Prescription  |
   |(fact_enc.)  |  |(fact_claim)|       |(fact_presc.)   |
   |PK:enc_key   |  |PK:claim_key|       |PK:presc_key    |
   +--+------+---+  +-+---+--+--+       ++--+--+--+------+
      |      |         |   |  |           |  |  |  |
      |  treatedBy     |   |  |submittedBy|  |  |  |prescribedBy
      |      |         |   |  |           |  |  |  |
      |      +----+    |   |  +------+    |  |  |  +------+
      |           v    |   |         v    |  |  |         v
      |    +----------+|   |  +----------+|  |  |  +----------+
      |    | Provider  ||   |  | Provider ||  |  |  | Provider |
      |    +----------+|   |  +----------+|  |  |  +----------+
      |                |   |              |  |  |
      |  billsFor------+   |ClaimHasPayer |  |  |PrescHasPayer
      |                    |              |  |  |
      |              +-----+              |  |  +---+
      |              v                    |  |      v
      |       +----------+               |  | +----------+
      |       |   Payer  |               |  | |   Payer  |
      |       |(dim_payer)|               |  | |(dim_payer)|
      |       |PK:payer_k|               |  | |PK:payer_k|
      |       +----------+               |  | +----------+
      |                                  |  |
      |                    dispenses-----+  |originatesFrom
      |                                     |
      |       +--------------+              |
      |       |  Medication   |              |
      |       |(dim_medication)|             |
      |       |PK:medication_k|             |
      |       +--------------+           connects to
      |                                  Encounter
      |
      |  +---------------------+
      +--|  PatientDiagnosis   |
      |  |  (fact_diagnosis)   |
      |  |  PK:fact_diag_key   |
      |  +--+-----+-----------+
      |     |     |
      |     |     | references
      |     |     v
      |     |  +----------+
      |     |  | Diagnosis |
      |     |  |(dim_diag) |
      |     |  |PK:diag_key|
      |     |  +----------+
      |     |
      |     | occursIn
      +-----+ (-> Encounter)
```

---

## Source Table Reference

| Lakehouse Table | Entity Type | Relationships (as Source) | Relationships (as Target) |
|---|---|---|---|
| `dim_patient` | Patient | livesIn -> CommunityHealth | involves, covers, serves, affects |
| `dim_diagnosis` | Diagnosis | - | references |
| `dim_payer` | Payer | - | ClaimHasPayer, PrescriptionHasPayer |
| `dim_medication` | Medication | - | dispenses |
| `dim_provider` | Provider | - | treatedBy, submittedBy, prescribedBy |
| `dim_sdoh` | CommunityHealth | - | livesIn |
| `fact_encounter` | Encounter | involves, treatedBy | billsFor, originatesFrom, occursIn |
| `fact_claim` | Claim | covers, submittedBy, ClaimHasPayer, billsFor | - |
| `fact_prescription` | Prescription | serves, prescribedBy, PrescriptionHasPayer, dispenses, originatesFrom | - |
| `fact_diagnosis` | PatientDiagnosis | affects, references, occursIn | - |

All tables are in **lh_gold_curated** (Gold layer of the Medallion architecture).
