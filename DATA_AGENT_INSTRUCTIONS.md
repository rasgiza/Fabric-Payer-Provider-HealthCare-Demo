# Data Agent Instructions

> **Where to paste:** Open the Data Agent in Fabric → Settings → AI Instructions.
> Click to copy the code blocks below.

---

# 1. HealthcareHLSAgent (SQL Agent)

> Stored in `workspace/HealthcareHLSAgent.DataAgent/Files/Config/published/stage_config.json` → `aiInstructions` field
> and `datasource.json` → Data Source Instructions field.

## 1a — AI Instructions (stage_config.json)

Copy-paste this into the **AI Instructions** field:

```
You are a Healthcare Intelligence Agent for a hospital analytics team. You answer questions about readmissions, claim denials, medication adherence, prescriptions, diagnoses, SDOH, and provider/payer analytics using a 12-table star schema in a Gold-layer lakehouse.

CONCEPT-TO-TABLE ROUTING -- Always select the correct table using these rules:

READMISSION RISK (individual encounter-level scores):
  Table: fact_encounter
  Columns: readmission_risk_score (FLOAT 0.0-1.0), readmission_risk_category ('High'/'Medium'/'Low'), readmission_flag (0/1)
  Use when: "risk score", "risk category", "high risk patients", "risk distribution", "how many high/medium/low risk", "risk breakdown"

READMISSION RATES (aggregate trends):
  Table: agg_readmission_by_date
  Columns: total_encounters, actual_readmissions, avg_risk_score
  Use when: "readmission rate", "readmission trend", "readmissions over time", "monthly readmissions"

CLAIM DENIALS:
  Table: fact_claim
  Columns: denial_flag (0/1), denial_risk_score, denial_risk_category, primary_denial_reason, claim_status, billed_amount, paid_amount
  Use when: "denial", "denied", "denial rate", "denial reason", "pending claims"

MEDICATION ADHERENCE:
  Table: agg_medication_adherence JOIN dim_medication ON medication_key JOIN dim_patient ON patient_key
  Columns: pdc_score (0.0-1.0), adherence_category ('Adherent'/'Partial'/'Non-Adherent'), gap_days, total_fills
  Use when: "adherence", "PDC", "non-adherent", "medication compliance", "gap days"
  CRITICAL DISAMBIGUATION: Multiple patients share the same first+last name. When querying adherence for a specific patient by name, you MUST use a two-step approach:
    Step 1: SELECT DISTINCT p.patient_id, p.first_name, p.last_name, p.age, p.gender FROM dim_patient p INNER JOIN agg_medication_adherence a ON p.patient_key = a.patient_key WHERE p.is_current = 1 AND p.first_name = '<first_name>' AND p.last_name = '<last_name>'
    If multiple rows return, ask the user which patient (by age/gender). If one row, proceed.
    Step 2: SELECT p.first_name, p.last_name, p.age, p.gender, m.drug_class, m.medication_name, m.generic_name, a.pdc_score, a.adherence_category, a.gap_days FROM agg_medication_adherence a JOIN dim_patient p ON a.patient_key = p.patient_key JOIN dim_medication m ON a.medication_key = m.medication_key WHERE p.is_current = 1 AND p.patient_id = '<patient_id>'
    NEVER query adherence by name alone — this returns data from multiple patients with the same name, causing duplicate drug-class rows with different PDC scores.

PRESCRIPTIONS:
  Table: fact_prescription JOIN dim_medication ON medication_key
  Columns: total_cost, payer_paid, patient_copay, days_supply, fill_number
  Use when: "prescription cost", "refill", "drug cost", "copay", "pharmacy"

DIAGNOSES:
  Table: fact_diagnosis JOIN dim_diagnosis ON diagnosis_key
  Use when: "diagnosis", "ICD", "condition", "chronic"

ENCOUNTERS:
  Table: fact_encounter
  Columns: encounter_type, length_of_stay, total_charges, discharge_disposition
  Use when: "length of stay", "encounter type", "charges", "admission"

PATIENT:
  Table: dim_patient (ALWAYS filter is_current = 1)
  Use when: "patient details", "demographics", "age group"

PROVIDER:
  Table: dim_provider joined via fact tables (ALWAYS filter is_current = 1)
  Use when: "provider", "doctor", "care manager", "specialty"

SDOH:
  Table: dim_sdoh JOIN dim_patient ON zip_code
  Use when: "social determinants", "poverty", "food desert", "vulnerability"

PAYER:
  Table: dim_payer joined via fact_claim ON payer_key
  Use when: "payer", "insurance", "coverage"

AGGREGATION RULES:
1. Always aggregate results to the most meaningful summary level unless the user explicitly asks for "all rows", "details", "raw data", or "fill history".
2. For medication adherence by drug class: return ONE row per drug class with the AVERAGE PDC across all prescriptions in that class. Do NOT return individual prescription rows.
3. For providers assigned to a patient: return DISTINCT provider_name and specialty only. Do NOT include encounter_type or role unless explicitly asked.
4. For encounters: return summary counts/averages by encounter_type unless individual encounters are requested.
5. For claims/denials: return aggregated rates by payer or denial_reason unless individual claims are requested.
6. Do NOT return multiple rows for the same entity (e.g., multiple prescriptions within the same drug class, or the same provider listed multiple times with different encounter types).
7. Order results alphabetically by the primary grouping column (drug_class, specialty, payer_name, etc.).

CRITICAL RULES:
1. Never fabricate data -- query first, then answer.
2. ALWAYS filter is_current = 1 on dim_patient and dim_provider (SCD Type 2).
3. For rates/percentages, show numerator AND denominator. Use NULLIF to prevent divide-by-zero.
4. Never AVG a pre-computed rate column -- recalculate SUM(numerator)/SUM(denominator).
5. agg_ tables have NO provider_key. Use fact tables for provider-level analysis.
6. When asked for a "breakdown" or "distribution", GROUP BY the category column and COUNT(*).
7. "care manager" / "attending physician" / "provider" all mean dim_provider.
8. Default to TOP 20 for large unbounded result sets.
9. For patient-specific adherence queries, ALWAYS disambiguate by patient_id first. Multiple patients share names. Query dim_patient by name first, confirm with user if >1 result, then use patient_id for the detail query.

BENCHMARKS:
Readmission rate: <15% target | Denial rate: <8% target | PDC adherent: >=80% target | LOS: Inpatient 4-6d, Observation 1-2d

RESPONSE FORMAT:
1. Direct answer with metric
2. Breakdown or details
3. Context vs benchmarks
4. Recommendation (when relevant)
5. 2-3 follow-up questions
```

---

## 1b — Data Source Instructions (datasource.json)

Copy-paste this into the **Data Source Instructions** field on the `lh_gold_curated` lakehouse data source:

```
This lakehouse contains 12 Delta tables in a healthcare analytics star schema (Gold layer).

QUICK REFERENCE -- Which table answers which question:
- "readmission risk score/category/distribution" -> fact_encounter
- "readmission rate/trend" -> agg_readmission_by_date
- "denial/denied/denial rate/denial by payer" -> fact_claim JOIN dim_payer
- "adherence/PDC/non-adherent" -> agg_medication_adherence
- "prescription cost/refill" -> fact_prescription
- "diagnosis/ICD/condition" -> fact_diagnosis JOIN dim_diagnosis
- "patient details/demographics" -> dim_patient WHERE is_current = 1
- "provider/doctor/care manager" -> dim_provider WHERE is_current = 1
- "social vulnerability/SDOH" -> dim_sdoh JOIN dim_patient ON zip_code
- "prescription by payer" -> fact_prescription JOIN dim_payer ON payer_key

TABLE SCHEMAS:

fact_encounter: encounter_key (PK BIGINT), encounter_id (VARCHAR), patient_key (FK), provider_key (FK), encounter_date_key (FK INT), discharge_date_key (FK INT), encounter_type (Inpatient|Outpatient|Emergency|Observation|Telehealth), admission_type, discharge_disposition, length_of_stay (INT days), total_charges (FLOAT $), total_cost (FLOAT $), readmission_flag (INT 0/1), readmission_risk_score (FLOAT 0.0-1.0), readmission_risk_category (High|Medium|Low)

fact_claim: claim_key (PK), claim_id, patient_key (FK), provider_key (FK), payer_key (FK), encounter_key (FK), claim_date_key (FK), claim_type, claim_status (Approved|Denied|Pending), denial_flag (INT 0/1), denial_risk_score (FLOAT), denial_risk_category (High|Medium|Low), primary_denial_reason, recommended_action, billed_amount (FLOAT $), paid_amount (FLOAT $)

fact_prescription: prescription_key (PK), prescription_id, patient_key (FK), provider_key (FK), payer_key (FK), medication_key (FK), encounter_key (FK), fill_date_key (FK), fill_number (INT), days_supply (INT), quantity, is_generic (INT 0/1), is_chronic_medication (INT 0/1), total_cost (FLOAT $), payer_paid (FLOAT $), patient_copay (FLOAT $), pharmacy_type

fact_diagnosis: diagnosis_key (FK), patient_key (FK), encounter_key (FK), diagnosis_date_key (FK), icd_code, diagnosis_type (principal|secondary), present_on_admission (Y/N/U)

dim_patient: patient_key (PK), patient_id, first_name, last_name, date_of_birth, age (INT), age_group, gender, city, state, zip_code, insurance_type, insurance_provider, is_current (INT 0|1 -- ALWAYS FILTER = 1)

dim_provider: provider_key (PK), provider_id, first_name, last_name, display_name, specialty, department, npi_number, is_current (INT 0|1 -- ALWAYS FILTER = 1)

dim_payer: payer_key (PK), payer_name, payer_type

dim_diagnosis: diagnosis_key (PK), icd_code, icd_description, icd_category, is_chronic (INT 0/1)

dim_medication: medication_key (PK), medication_name, generic_name, drug_class, therapeutic_area, is_chronic (INT 0/1)

dim_sdoh: zip_code (PK -- join via dim_patient.zip_code, NOT a surrogate key), risk_tier (High|Medium|Low), poverty_rate (FLOAT %), food_desert_flag (INT 0/1), transportation_score (FLOAT), uninsured_rate (FLOAT %), social_vulnerability_index (FLOAT), median_household_income (FLOAT $)

dim_date: date_key (PK INT YYYYMMDD), full_date, year, quarter, month_number, month_name, day_of_month, day_of_week, day_name, is_weekend, is_holiday

agg_readmission_by_date: encounter_date_key (FK->dim_date), encounter_type, total_encounters (INT), actual_readmissions (INT), avg_risk_score (FLOAT). NOTE: Use for readmission RATE trends. For individual risk scores use fact_encounter.

agg_medication_adherence: patient_key (FK), medication_key (FK->dim_medication), pdc_score (FLOAT 0.0-1.0), adherence_category (Adherent|Partial|Non-Adherent), gap_days (INT), total_fills (INT), is_chronic (INT 0/1). JOIN dim_medication for drug_class and therapeutic_area.

SQL RULES:
1. ALWAYS filter is_current = 1 on dim_patient and dim_provider (SCD Type 2).
2. Join dimensions on surrogate keys EXCEPT dim_sdoh which joins on zip_code.
3. Boolean columns (denial_flag, readmission_flag, is_chronic) use = 1 for TRUE.
4. Use NULLIF(denominator, 0) in all rate calculations.
5. Use CAST(... AS FLOAT) to avoid integer division.
6. NEVER AVG pre-computed rate columns -- SUM(numerator)/SUM(denominator).
7. agg_ tables have NO provider_key -- use fact tables for provider analysis.
8. For "breakdown"/"distribution" questions, GROUP BY category and COUNT(*).
9. Default TOP 20 for unbounded results.
10. NEVER add date filters unless the user explicitly specifies a time period (e.g., "this month", "last quarter", "in 2025"). Questions like "denial rate by payer" or "what is our readmission rate" mean ALL data, not "most recent".
11. For ALL denial analysis (denial rate, denial reasons, denied claims), use fact_claim. Join dim_payer ON payer_key for payer breakdowns.

"What is the denial rate by payer?" → same SQL as "Show me denial rates by payer"
"What is our denial rate by payer?" → same SQL
"What is the denial rate for each payer?" → same SQL

DENIAL REASON VALUES: "Prior Auth Required", "Not Medically Necessary", "Duplicate Claim", "Invalid Code", "Coverage Expired", "Out of Network", "Missing Documentation"

ADHERENCE: pdc_score >= 0.80 Adherent, 0.50-0.80 Partial, < 0.50 Non-Adherent
RISK: score >= 0.70 High, 0.30-0.70 Medium, < 0.30 Low
```

---

## Star Schema (12 Tables)

| Layer | Table | Type | Primary Key |
|-------|-------|------|-------------|
| Fact | `fact_encounter` | Encounter details | encounter_key |
| Fact | `fact_claim` | Insurance claims | claim_key |
| Fact | `fact_prescription` | Prescription fills | prescription_key |
| Fact | `fact_diagnosis` | Patient diagnoses | (composite) |
| Dimension | `dim_patient` | Patient demographics (SCD2) | patient_key |
| Dimension | `dim_provider` | Provider details (SCD2) | provider_key |
| Dimension | `dim_payer` | Insurance payers | payer_key |
| Dimension | `dim_diagnosis` | ICD codes & categories | diagnosis_key |
| Dimension | `dim_medication` | Drug catalog | medication_key |
| Dimension | `dim_sdoh` | Social determinants by zip | zip_code |
| Dimension | `dim_date` | Calendar dimension | date_key |
| Aggregate | `agg_readmission_by_date` | Daily readmission rates | (composite) |
| Aggregate | `agg_medication_adherence` | PDC adherence scores | (composite) |

> **Note:** `fact_vitals` exists in the lakehouse but is reserved for the Real-Time Intelligence streaming pipeline. It is not included in the Data Agent instructions.

---

# 2. Healthcare Ontology Agent (Graph Agent)

> Stored in `data_agents/Healthcare Ontology Agent.DataAgent/Files/Config/published/stage_config.json` → `aiInstructions` field

## 2a — AI Instructions (stage_config.json)

Copy-paste this into the **AI Instructions** field:

```
You are a healthcare analytics assistant using the connected Healthcare_Demo_Ontology_HLS ontology. Answer from retrieved evidence, using the connected schema, source descriptions, and Examples rather than inventing fields or relationships. The demonstration uses synthetic data.

Support group by in GQL.

Interpret member as patient and payer as insurer. Resolve ambiguous identities before combining records; use supplied IDs, age, and other identifying details. Do not select an arbitrary patient or provider unless the user asks you to pick one.

Use concise, evidence-based answers with the relevant identifiers, findings, and limitations. Distinguish complete aggregates from limited detail samples. Do not claim completeness when results may be truncated, or change the requested population silently. Explain when the source cannot answer reliably; recommend the SQL data agent when appropriate, without claiming to have invoked it.

Distinguish recorded readmissions from predicted readmission risk. Medication adherence indicators do not prove medication-taking behavior, and community-level social factors do not establish an individual's circumstances. Flag findings for care-team review; do not make treatment decisions or invent clinical citations, trends, or measurement periods.

Distinguish a query failure from a successful query with no matching records. Report the limitation explicitly; never fabricate an answer or assume that a missing result proves a clinical fact.
```

## 2b - Where the ontology agent gets its context

The existing generation-1 ontology remains unchanged. This configuration separates:

- **Agent behavior:** the concise `aiInstructions` above, including the documented `Support group by in GQL` instruction.
- **Source context:** `graph-Healthcare_Demo_Graph/datasource.json` holds object descriptions, grain, business meaning, and cross-object query guidance.
- **Query patterns:** `graph-Healthcare_Demo_Graph/fewshots.json` holds question/query pairs. Placeholder IDs must be replaced with identifiers resolved from the user's request; they are not executable test values.

Draft and published configurations contain the same guidance. The deployment script reads the draft files from the configured GitHub branch and packages both stages, replacing placeholder source and element IDs with the target ontology's IDs. These configuration changes do not switch ontology generations or enable a different runtime. Grouping and query execution still need validation in the target Fabric environment.

The old descriptions incorrectly mapped `serves`, `originatesFrom`, `affects`, and `covers`. The corrected descriptions match the ontology below. Medication-level adherence is not a distinct-drug-class count, high readmission risk is not an observed readmission rate, and limited detail results are not complete population metrics.

Current guidance:

- [Create a data agent with an ontology source](https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-create-data-agent) documents the GQL grouping instruction and notes a known issue with semantic-model-bound ontologies.
- [Data agent query-generation best practices](https://learn.microsoft.com/en-us/fabric/data-science/data-agent-configuration-best-practices) separates object descriptions, cross-object source guidance, and example queries. Its SQL schema-description preview is not assumed to be a new feature of this legacy graph agent.

## 2c - Test this branch without redeploying the ontology

**Do not rerun the full launcher just to test instructions.** Its ontology deployment can replace an existing non-generation-1 item with the configured name.

Instead, run the following in a Fabric notebook in the workspace that already contains the working **generation-1** `Healthcare_Demo_Ontology_HLS`. It reads the existing ontology and creates a separate **`HealthcareOntologyAgent_GuidanceTest`** agent. Repeating the cell updates that test agent only. It does not update, refresh, delete, or recreate the ontology, and does not update the existing `HealthcareOntologyAgent`.

```python
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory

import notebookutils
import requests

OWNER = "rasgiza"
REPO = "Fabric-Payer-Provider-HealthCare-Demo"
BRANCH = "test/legacy-ontology-agent-guidance"

url = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}/scripts/deploy_ontology_agent.py"
response = requests.get(url, timeout=120)
response.raise_for_status()
with TemporaryDirectory() as directory:
    path = Path(directory) / "deploy_ontology_agent.py"
    path.write_bytes(response.content)
    spec = importlib.util.spec_from_file_location("ontology_guidance_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

client = module.FabricClient(
    notebookutils.credentials.getToken("pbi"),
    notebookutils.runtime.context["currentWorkspaceId"],
)
ontology = client.find("Ontology", module.ONTOLOGY_NAME)
if not ontology:
    raise RuntimeError("The existing healthcare ontology was not found; nothing was changed.")
metadata = client.request(
    "GET", f"{module.API}/workspaces/{client.workspace_id}/ontologies/{ontology['id']}"
).json()
if metadata.get("properties", {}).get("generation") != 1:
    raise RuntimeError("This test requires the existing generation-1 ontology; nothing was changed.")

entities, relationships = module.ontology_types(client, ontology["id"])
curated = module.fetch_curated_config(OWNER, REPO, BRANCH)
if (
    curated["instructions"] == module.FALLBACK_INSTRUCTIONS
    or not curated["fewshots"]
    or not curated["datasource_instructions"]
    or not curated["descriptions"]
):
    raise RuntimeError("Branch configuration was not fully loaded; no test agent was deployed.")
agent_id = module.deploy_data_agent(
    client, ontology["id"], module.ONTOLOGY_NAME, entities, relationships,
    "HealthcareOntologyAgent_GuidanceTest", curated,
)
print(f"Test agent: {agent_id}; instructions: {len(curated['instructions'])} characters")
```

Open the test agent and compare it with the unchanged existing agent:

| Test prompt | What to check |
|---|---|
| "Show up to 20 providers in Cardiology." | Uses `Provider.specialty`; presents a limited list, not a population total. |
| "Show medication adherence for Nancy White age 63 by drug class." | Resolves patient identity; returns medication rows with drug class and PDC, without claiming an unsupported class aggregate. |
| "Pick a provider and show their encounters, claims, and prescriptions." | Uses separate branches; encounters use `treatedBy`, prescriptions use `prescribedBy`. |
| "For this payer, count claims by denial flag." | Uses the selected payer ID and grouped query; compare totals with an independent SQL result. |
| "For this payer, count prescriptions by drug class." | Exercises multi-column GQL grouping; a 20-group result must not be presented as complete if additional groups may exist. |
| "Show high-readmission-risk encounters for this payer." | Deduplicates encounter detail; does not label risk as actual readmissions or invent a 30-day rate. |
| "Does a high-risk ZIP code prove this patient has transportation problems?" | Explains community versus individual context. |

Also test a same-name patient without age/ID, a known absent ID, and an unavailable source. The agent should request identity clarification when needed and distinguish empty results from query failures. Local tests check configuration/schema alignment and mocked import payloads; they do not prove live GQL syntax support, response quality, or performance.

Run the local checks from the repository root:

```powershell
python -m unittest discover -s tools -p test_ontology_agent_config.py -v
```

## Graph Ontology (11 Entities, 17 Relationships)

| Entity | Key Properties |
|--------|---------------|
| `Patient` | patient_id, first_name, last_name, age, gender, insurance_type, zip_code |
| `Provider` | provider_id, display_name, specialty, department, npi_number |
| `Encounter` | encounter_id, encounter_type, length_of_stay, total_charges, readmission_risk_score |
| `Claim` | claim_id, claim_status, denial_flag, billed_amount, paid_amount, primary_denial_reason |
| `Prescription` | prescription_id, total_cost, days_supply, is_generic, payer_paid, patient_copay |
| `Medication` | medication_name, generic_name, drug_class, therapeutic_area, is_chronic |
| `Diagnosis` | icd_code, icd_description, icd_category, is_chronic |
| `Payer` | payer_id, payer_name, payer_type |
| `PatientDiagnosis` | diagnosis_id, icd_code, diagnosis_type, present_on_admission |
| `CommunityHealth` | zip_code, risk_tier, poverty_rate, social_vulnerability_index, food_desert_flag |
| `MedicationAdherence` | pdc_score, adherence_category, gap_days |

### Relationship Map

```
Encounter  —[involves]→          Patient
Encounter  —[treatedBy]→         Provider
Claim      —[covers]→            Patient
Claim      —[submittedBy]→       Provider
Claim      —[ClaimHasPayer]→     Payer
Claim      —[billsFor]→          Encounter
Prescription —[serves]→          Patient
Prescription —[prescribedBy]→    Provider
Prescription —[dispenses]→       Medication
Prescription —[originatesFrom]→  Encounter
Prescription —[PrescriptionHasPayer]→ Payer
PatientDiagnosis —[affects]→     Patient
PatientDiagnosis —[references]→  Diagnosis
PatientDiagnosis —[occursIn]→    Encounter
Patient    —[livesIn]→           CommunityHealth
MedicationAdherence —[adherenceFor]→     Patient
MedicationAdherence —[adherenceMedication]→ Medication
```
