# Healthcare Data Agent Guide

Complete reference for the **HealthcareHLSAgent** Fabric Data Agent -- setup, configuration, AI instructions, data sources, and customization.

---

## Overview

The HealthcareHLSAgent is a Copilot-powered Data Agent deployed into your Fabric workspace. It answers natural-language questions about healthcare analytics by querying a 13-table Gold-layer star schema via SQL and a companion semantic model via DAX.

**Two data sources are configured:**

| Source | Type | Use Case |
|--------|------|----------|
| `lh_gold_curated` | Lakehouse tables (SQL) | Patient-level detail, multi-table JOINs, row-level filtering |
| `HealthcareDemoHLS` | Semantic model (DAX) | Pre-built measures, aggregations, time intelligence |

---

## Deployment

The agent is deployed automatically by the launcher notebook (Stage 5). It includes:

1. **Agent definition** -- `workspace/HealthcareHLSAgent.DataAgent/`
2. **AI instructions** -- system prompt controlling agent behavior
3. **Data source configs** -- lakehouse schema + semantic model with 26 DAX measures
4. **36 few-shot examples** -- pre-built SQL queries the agent uses as reference
5. **Knowledge documents** -- 21 markdown files uploaded to `lh_gold_curated/Files/healthcare_knowledge/`

After deployment, open the agent in your Fabric workspace and start asking questions. See [SAMPLE_QUESTIONS.md](SAMPLE_QUESTIONS.md) for 60+ ready-to-use prompts.

---

## AI Instructions (System Prompt)

The agent's system prompt is stored in `workspace/HealthcareHLSAgent.DataAgent/Files/Config/draft/stage_config.json` (and `published/`). Below is the full instruction set:

```
You are a Healthcare Intelligence Agent for a hospital analytics team. You answer
questions about readmissions, claim denials, medication adherence, prescriptions,
diagnoses, SDOH, and provider/payer analytics using a 13-table star schema in a
Gold-layer lakehouse.
```

### Concept-to-Table Routing

The agent uses these rules to select the correct table for each question:

| Concept | Table | Key Columns | Trigger Phrases |
|---------|-------|-------------|-----------------|
| Readmission risk (individual) | `fact_encounter` | readmission_risk_score (0.0-1.0), readmission_risk_category (High/Medium/Low), readmission_flag (0/1) | "risk score", "risk category", "high risk patients" |
| Readmission rates (aggregate) | `agg_readmission_by_date` | total_encounters, actual_readmissions, avg_risk_score | "readmission rate", "readmission trend", "monthly readmissions" |
| Claim denials | `fact_claim` | denial_flag (0/1), denial_risk_score, denial_risk_category, primary_denial_reason, claim_status, billed_amount, paid_amount | "denial", "denied", "denial rate", "denial reason" |
| Medication adherence | `agg_medication_adherence` JOIN `dim_medication` | pdc_score (0.0-1.0), adherence_category, gap_days, total_fills | "adherence", "PDC", "non-adherent", "gap days" |
| Prescriptions | `fact_prescription` JOIN `dim_medication` | total_cost, payer_paid, patient_copay, days_supply, fill_number | "prescription cost", "refill", "drug cost", "copay" |
| Diagnoses | `fact_diagnosis` JOIN `dim_diagnosis` | icd_code, icd_description, diagnosis_type | "diagnosis", "ICD", "condition", "chronic" |
| Encounters | `fact_encounter` | encounter_type, length_of_stay, total_charges, discharge_disposition | "length of stay", "encounter type", "charges" |
| Patient | `dim_patient` (filter `is_current = 1`) | patient_id, age, age_group, gender, zip_code, insurance_type | "patient details", "demographics" |
| Provider | `dim_provider` (filter `is_current = 1`) | display_name, specialty, department, npi_number | "provider", "doctor", "care manager" |
| SDOH | `dim_sdoh` JOIN `dim_patient` ON zip_code | poverty_rate, food_desert_flag, transportation_score, social_vulnerability_index | "social determinants", "poverty", "food desert" |
| Payer | `dim_payer` JOIN `fact_claim` ON payer_key | payer_name, payer_type | "payer", "insurance", "coverage" |

### Critical SQL Rules

1. **Never fabricate data** -- query first, then answer.
2. **ALWAYS filter `is_current = 1`** on `dim_patient` and `dim_provider` (SCD Type 2).
3. For rates/percentages, show numerator AND denominator. Use `NULLIF` to prevent divide-by-zero.
4. **Never AVG a pre-computed rate column** -- recalculate `SUM(numerator)/SUM(denominator)`.
5. `agg_` tables have **NO `provider_key`**. Use fact tables for provider-level analysis.
6. When asked for a "breakdown" or "distribution", `GROUP BY` the category column and `COUNT(*)`.
7. "care manager" / "attending physician" / "provider" all mean `dim_provider`.
8. Default to `TOP 20` for large unbounded result sets.
9. **Never add date filters** unless the user explicitly specifies a time period.
10. For ALL denial analysis, use `fact_claim`. Join `dim_payer` ON `payer_key` for payer breakdowns.
11. Join dimensions on surrogate keys EXCEPT `dim_sdoh` which joins on `zip_code`.

### Industry Benchmarks

| Metric | Target | Source |
|--------|--------|--------|
| Readmission rate | < 15% | CMS HRRP |
| Denial rate | < 8% | HFMA |
| PDC adherent | >= 80% | CMS Star |
| Avg LOS (inpatient) | 4-6 days | AHA |
| Avg LOS (observation) | 1-2 days | AHA |

### Response Format

1. Direct answer with metric
2. Breakdown or details
3. Context vs benchmarks
4. Recommendation (when relevant)
5. 2-3 follow-up questions

---

## Data Source: Lakehouse Tables

The lakehouse data source (`lh_gold_curated`) is configured in:
`workspace/HealthcareHLSAgent.DataAgent/Files/Config/draft/lakehouse-tables-lh_gold_curated/datasource.json`

### Table Schemas

| Table | Type | PK | Key Columns |
|-------|------|-----|-------------|
| `fact_encounter` | Fact | encounter_key | patient_key, provider_key, encounter_date_key, discharge_date_key, encounter_type, length_of_stay, total_charges, readmission_flag, readmission_risk_score, readmission_risk_category |
| `fact_claim` | Fact | claim_key | patient_key, provider_key, payer_key, encounter_key, claim_date_key, claim_type, claim_status, denial_flag, denial_risk_score, denial_risk_category, primary_denial_reason, billed_amount, paid_amount |
| `fact_prescription` | Fact | prescription_key | patient_key, provider_key, payer_key, medication_key, encounter_key, fill_date_key, fill_number, days_supply, total_cost, payer_paid, patient_copay |
| `fact_diagnosis` | Fact | -- | diagnosis_key (FK), patient_key, encounter_key, diagnosis_date_key, icd_code, diagnosis_type, present_on_admission |
| `fact_vitals` | Fact | -- | patient_key, encounter_key, vital_date_key, systolic_bp, diastolic_bp, heart_rate, bmi, oxygen_saturation |
| `dim_patient` | SCD2 Dim | patient_key | patient_id, first_name, last_name, age, age_group, gender, zip_code, insurance_type, **is_current** |
| `dim_provider` | SCD2 Dim | provider_key | provider_id, display_name, specialty, department, npi_number, **is_current** |
| `dim_payer` | Dim | payer_key | payer_name, payer_type |
| `dim_diagnosis` | Dim | diagnosis_key | icd_code, icd_description, icd_category, is_chronic |
| `dim_medication` | Dim | medication_key | medication_name, generic_name, drug_class, therapeutic_area, is_chronic |
| `dim_sdoh` | Dim | zip_code | risk_tier, poverty_rate, food_desert_flag, transportation_score, uninsured_rate, social_vulnerability_index, median_household_income |
| `dim_date` | Date Dim | date_key (YYYYMMDD) | full_date, year, quarter, month_number, month_name, day_of_week, is_weekend |
| `agg_readmission_by_date` | Aggregate | -- | encounter_date_key, encounter_type, total_encounters, actual_readmissions, avg_risk_score |
| `agg_medication_adherence` | Aggregate | -- | patient_key, medication_key, pdc_score, adherence_category, gap_days, total_fills |

### Reference Values

**Denial reasons:** "Prior Auth Required", "Not Medically Necessary", "Duplicate Claim", "Invalid Code", "Coverage Expired", "Out of Network", "Missing Documentation"

**Adherence thresholds:** PDC >= 0.80 Adherent | 0.50-0.80 Partial | < 0.50 Non-Adherent

**Risk tiers:** score >= 0.70 High | 0.30-0.70 Medium | < 0.30 Low

---

## Data Source: Semantic Model

The semantic model data source (`HealthcareDemoHLS`) provides 26 pre-built DAX measures for the agent to use when answering aggregation or time-intelligence questions.

Configuration: `workspace/HealthcareHLSAgent.DataAgent/Files/Config/draft/semantic-model-HealthcareDemoHLS/datasource.json`

---

## Few-Shot Examples

36 pre-built SQL query examples are stored in:
`workspace/HealthcareHLSAgent.DataAgent/Files/Config/draft/lakehouse-tables-lh_gold_curated/fewshots.json`

These cover:

| Category | Examples |
|----------|----------|
| Readmission risk distribution | Risk category counts, top patients by score, risk by encounter type |
| Readmission rate trends | Overall rate, monthly trends, rate by encounter type |
| Claim denials | Overall denial rate, denial by payer, top denial reasons, denied claims with patient names |
| Denial analysis | Provider denial rates, denial reasons by provider, high-value denied claims with diagnoses |
| Medication adherence | PDC by drug class, non-adherent patients, adherence by therapeutic area |
| Prescriptions | Total Rx cost by drug class, top patients by prescription count |
| Cross-domain | Readmitted + non-adherent patients, SDOH + denial rates, chronic conditions + readmission |
| Demographics | Patient counts by age group, patients by insurance type |

---

## Knowledge Base (21 Documents)

The agent has access to healthcare domain knowledge uploaded to `lh_gold_curated/Files/healthcare_knowledge/`. These documents provide clinical context, regulatory references, and operational guidelines.

### Clinical Guidelines (5 docs)
| Document | Content |
|----------|---------|
| `CHF_Management_Guidelines.md` | GDMT protocol, NYHA staging, discharge planning, 30-day readmission prevention |
| `COPD_Management_Guidelines.md` | GOLD staging, exacerbation management, spirometry thresholds |
| `Diabetes_Type2_Management.md` | ADA stepwise therapy, A1C targets, medication escalation |
| `Readmission_Prevention_Protocol.md` | Risk tier interventions, transition of care, follow-up scheduling |
| `Sepsis_Recognition_Management.md` | Sepsis-3 criteria, qSOFA scoring, bundle compliance |

### Compliance (3 docs)
| Document | Content |
|----------|---------|
| `HIPAA_Privacy_Guide.md` | PHI handling, minimum necessary, breach reporting |
| `Clinical_Documentation_Standards.md` | E&M coding, CDI requirements, query protocols |
| `Audit_Readiness_Checklist.md` | CMS audit preparation, documentation requirements |

### Denial Management (4 docs)
| Document | Content |
|----------|---------|
| `Appeal_Process_Guide.md` | Level 1-3 appeal workflows, timelines, success rates |
| `Clean_Claim_Checklist.md` | Pre-submission validation, common rejection codes |
| `Prior_Authorization_Requirements.md` | PA requirements by payer and service type |
| `Root_Cause_Analysis_Framework.md` | Denial root cause categories, corrective actions |

### Formulary (3 docs)
| Document | Content |
|----------|---------|
| `Drug_Formulary_Guide.md` | Tier structure, generic substitution, formulary exceptions |
| `Specialty_Drug_Authorization.md` | Specialty Rx PA requirements, distribution restrictions |
| `Step_Therapy_Protocols.md` | Step therapy sequences by drug class, failure documentation |

### Provider Network (3 docs)
| Document | Content |
|----------|---------|
| `Provider_Contract_Guide.md` | Reimbursement rate structures, negotiation frameworks |
| `Network_Adequacy_Standards.md` | CMS time/distance standards, specialty coverage requirements |
| `Credentialing_Requirements.md` | Provider enrollment, re-credentialing timelines |

### Quality Measures (3 docs)
| Document | Content |
|----------|---------|
| `CMS_Star_Rating_Strategy.md` | Star rating methodology, triple-weighted measures, cut points |
| `HEDIS_Measures_Guide.md` | 8 HEDIS measure definitions (CDC, COL, BCS, SPC, CBP, SPD, OMW, PPC) |
| `Readmission_Penalty_Program.md` | HRRP penalty calculation, applicable conditions, reporting periods |

---

## Customizing the Agent

### Modify AI Instructions

Edit `stage_config.json` in both `draft/` and `published/` directories:

```
workspace/HealthcareHLSAgent.DataAgent/Files/Config/draft/stage_config.json
workspace/HealthcareHLSAgent.DataAgent/Files/Config/published/stage_config.json
```

The `aiInstructions` field contains the full system prompt. Changes take effect after redeploying the agent.

### Add Few-Shot Examples

Edit `fewshots.json` in the lakehouse data source directory. Each example needs:

```json
{
  "id": "<unique-guid>",
  "question": "Natural language question",
  "query": "SQL query that answers the question"
}
```

### Add Knowledge Documents

Place new `.md` files in the `healthcare_knowledge/` directory (organized by subdirectory). The launcher uploads them to `lh_gold_curated/Files/healthcare_knowledge/` during deployment. To add docs after deployment, upload manually via the Fabric portal to the lakehouse Files section.

### Update Data Source Instructions

Edit `datasource.json` in the lakehouse data source directory to update table schemas, SQL rules, or reference values:

```
workspace/HealthcareHLSAgent.DataAgent/Files/Config/draft/lakehouse-tables-lh_gold_curated/datasource.json
```

---

## Agent File Structure

```
workspace/HealthcareHLSAgent.DataAgent/
  .platform                              # Fabric item metadata
  manifest.json                          # Item manifest
  Files/
    Config/
      data_agent.json                    # Agent schema reference
      publish_info.json                  # Agent description
      draft/
        stage_config.json                # AI instructions (system prompt)
        lakehouse-tables-lh_gold_curated/
          datasource.json                # Lakehouse schema + SQL rules
          fewshots.json                  # 36 SQL query examples
        semantic-model-HealthcareDemoHLS/
          datasource.json                # Semantic model with 26 DAX measures
      published/
        (same structure as draft/)
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Agent returns generic/wrong answers | Check that Gold lakehouse tables are populated (run the pipeline first) |
| Agent doesn't use knowledge docs | Verify docs exist in `lh_gold_curated/Files/healthcare_knowledge/` |
| Agent queries wrong table | Review concept-to-table routing in `stage_config.json` |
| Agent fabricates data | The system prompt says "never fabricate" -- ensure it's not overridden |
| Agent can't find patients | Ensure `is_current = 1` filter is applied (SCD2 dimension) |
| Few-shot examples not working | Check `fewshots.json` -- each entry needs a unique `id`, `question`, and `query` |
| Semantic model measures unavailable | Ensure the semantic model is refreshed after pipeline run |
