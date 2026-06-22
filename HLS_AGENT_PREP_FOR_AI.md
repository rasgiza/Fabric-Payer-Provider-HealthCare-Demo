# HealthcareHLSAgent — Prep for AI

Companion to the AI-readiness work on `HealthcareDemoHLS.SemanticModel`. The model now
carries `///` table, column, and measure descriptions (DirectLake on `lh_gold_curated`).

> Design principles (Microsoft best practices —
> [Semantic model best practices for data agent](https://learn.microsoft.com/en-us/fabric/data-science/semantic-model-best-practices#prep-for-ai-make-semantic-model-ai-ready),
> [Prepare your data for AI](https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-prepare-data-ai)):
> - **Agent-level instructions are cross-source only.** The DAX generation tool *ignores*
>   data-agent instructions (and data-source descriptions) when querying a semantic model, so
>   keep model-specific guidance in **Prep for AI**, not in the agent prompt.
> - Keep the agent prompt high-level: response formatting, cross-source routing, tone. Start
>   lean, test, add context incrementally — avoid context bloat.
> - Make the model AI-ready with the three **Prep for AI** features: an **AI data schema**
>   (the field subset Copilot may use), **AI instructions** (business context + rules), and
>   **verified answers** (trigger phrases mapped to an approved report visual).
> - A **verified answer is a saved report visual**, not a query and not a text answer. Copilot
>   returns that visual when a user prompt matches one of its trigger phrases. **RLS/OLS is not
>   fully enforced on verified answers**, so don't rely on them to hide row-restricted data.

## What deploys how (read first)

| Layer | Lives in | Deploys via |
|---|---|---|
| **A. Agent-level instructions** (operational prompt) | `HealthcareHLSAgent.DataAgent/.../stage_config.json` | ✅ API / Git sync |
| **B. Lakehouse data-source instructions** (SQL schema, rules, values) | `.../datasource.json` | ✅ API / Git sync |
| **C. Prep for AI — AI data schema** (field subset Copilot may use) — *Section 3* | Semantic model → *Prep data for AI → Simplify the data schema* | ⚠️ **Service UI only** |
| **D. Prep for AI — AI instructions** (business context + rules) — *Section 4* | Semantic model → *Prep data for AI → Add AI instructions* | ⚠️ **Service UI only** |
| **E. Prep for AI — Verified answers** (trigger phrases → approved visual) — *Section 5* | Built in **Power BI Desktop** (right-click visual → *Set up a verified answer*); surfaces in service *Prep data for AI → Verified answers* | ⚠️ **Desktop + service UI** |
| **F. Q&A linguistic schema** (synonyms — e.g. "bounce-backs"→readmissions, "compliance"→PDC) | `HealthcareDemoHLS.SemanticModel/definition/cultures/en-US.tmdl` | ✅ **Git sync** |

**Why the split:** the three Prep for AI features (C, D, E) **cannot be set through the API
today**, so they're documented here to configure in the UI by hand. Layer **F** (synonyms) is
the one model-intelligence artifact that *is* Git-deployable — it ships in TMDL and helps both
the agent and plain Copilot/Q&A map everyday phrasing to the right measure. Keep A intentionally thin —
it should only tell the agent *how to reason over the sources and shape its answers*, never
repeat the lakehouse SQL detail that belongs in B, or the model context that belongs in C–E.

## ⚠️ To get good answers from the semantic model, you MUST do the UI steps

Git sync deploys Layers A and B automatically. But when the agent answers from the
**`HealthcareDemoHLS` semantic model** (the PRIMARY source), the DAX generation tool **ignores
the agent prompt and `datasource.json`** and reads **only** the model's **Prep data for AI**
configuration. So these UI steps are not optional polish — they are *where the agent's
semantic-model intelligence comes from*. Skip them and the agent guesses at business terms,
picks the wrong measure, and misses your standard breakdowns.

**One-time setup for the model owner.** Open `HealthcareDemoHLS` in the Fabric / Power BI
**service** → **Prep data for AI**. (If the tabs are greyed out, click **Turn on Q&A** first.)
There are three features — do them in this order:

1. **Simplify the data schema** (service UI) → tick only the analytic fields Copilot should use;
   hide keys, timestamps, and PII. Use the KEEP/EXCLUDE lists in **Section 3**.
2. **Add AI instructions** (service UI) → paste the block in **Section 4** (business context,
   terminology, measure-first rules, join rules, benchmarks).
3. **Verified answers** (built in **Power BI Desktop**) → for each entry in **Section 5**, build
   the described visual, right-click it → **Set up a verified answer**, add the trigger phrases,
   **Apply**, then publish. They then appear under Prep data for AI → Verified answers.
4. Re-test the agent and iterate — add an instruction or verified answer whenever you see a
   wrong answer. Start lean; don't do everything at once.

Until these UI steps are done, only the lakehouse (SQL) path is fully tuned.

---

## 1. Agent-level instructions — Layer A (deployed via API; high-level only)

This is the exact text in `stage_config.json` (`aiInstructions`). It stays cross-source:
source selection, response structure, and a pointer to where source-specific detail lives.

```
You are the Healthcare Intelligence Agent for a hospital analytics team, answering questions about readmissions, claim denials, medication adherence, prescriptions, diagnoses, social determinants, providers, and payers over a Gold-layer star schema.

TWO DATA SOURCES - PICK EXACTLY ONE PER QUESTION
1. semantic_model 'HealthcareDemoHLS' (PRIMARY, default) - pre-built DAX measures for any question about rates, percentages, totals, counts, averages, trends, or KPI breakdowns.
2. lakehouse_tables 'lh_gold_curated' (FALLBACK) - raw SQL for row-level detail a measure cannot provide: patient names, claim IDs, prescription rows, or filters on columns not exposed as measures.

ROUTING
- Default to the semantic model; switch to the lakehouse only when row-level detail is required.
- Rates, counts, trends, breakdowns, 'how many / how much', 'top N by [measure]' -> semantic model.
- 'show me / list / who is' patients, claims, prescriptions, individual records -> lakehouse.
- Never combine both sources in one answer. If a question needs KPIs and detail, answer the KPI part and offer to drill in as a follow-up. When ambiguous, prefer the semantic model.

RESPONSE
- Query first; never fabricate values. Lead with the direct answer and headline metric, then a short breakdown, then context vs benchmark when useful, then 2-3 follow-ups.
- State the period and grain. Format units explicitly: rates as %, money as $, durations in days.
- Aggregate by default; surface individual patient identifiers only when explicitly requested.
- If a metric returns 0 or blank, say it may be filtered or unavailable rather than asserting a true zero, and suggest a refinement.

SOURCE-SPECIFIC DETAIL
- Semantic model: schema, measure choice, business terminology, and benchmark targets live in the model's Prep for AI (AI instructions, AI data schema, verified answers) - the DAX tool reads those, not this prompt.
- Lakehouse: table schemas, SQL rules, and allowed values live in the lakehouse data-source instructions.
```

## 2. Lakehouse data-source instructions — Layer B (deployed via API)

This layer tunes only the **lakehouse (SQL) fallback** source and already lives in
`datasource.json`. It holds table schemas, allowed column values, SCD `is_current = 1`
filtering, and SQL rules for the row-level questions the model can't answer (patient lists,
claim IDs, individual fills).

> The semantic-model source is **not** tuned here. When the agent queries `HealthcareDemoHLS`,
> the DAX tool reads the model's **Prep data for AI** config (Sections 3–5), **not**
> `datasource.json`. So all measure, terminology, schema, and benchmark guidance for the model
> lives in **Sections 3–4** below — that is the correct home for it, per Microsoft's guidance.

---

## 3. AI data schema — *Simplify the data schema* (⚠️ Fabric / Power BI service UI)

**Prep data for AI → Simplify the data schema.** Here you tick **only the fields Copilot may
use**. Narrowing the schema is the single biggest accuracy win — Copilot stops guessing between
a surrogate key and a name, or a raw timestamp and a date. Hidden model fields are auto-excluded
on first setup; the lists below are the explicit target state.

Rule of thumb: **keep descriptive attributes and the measures; hide plumbing and PII you don't
analyze.**

**Always EXCLUDE (every table):**
- All surrogate keys: `*_key` (patient_key, provider_key, payer_key, claim_key, encounter_key,
  diagnosis_key, medication_key, date_key, …). Copilot still uses relationships without them.
- ETL/SCD plumbing: `_load_timestamp`, `effective_start_date`, `effective_end_date`.
- Natural-ID columns that duplicate a name: `patient_id`, `provider_id`, `payer_id`, `claim_id`,
  `prescription_id`, `encounter_id`, `diagnosis_id`, and `icd_code` (keep `icd_description`).

**KEEP per table (the analytic surface):**

| Table | Keep these fields | Plus these measures |
|---|---|---|
| `fact_claim` | claim_type, claim_status, billed_amount, allowed_amount, paid_amount, denial_flag, denial_risk_category, primary_denial_reason, recommended_action | Total Claims, Denial Rate, Collection Rate, Total Billed, Total Paid, At Risk Revenue, Avg Denial Risk |
| `fact_encounter` | encounter_type, admission_type, discharge_disposition, length_of_stay, total_charges, total_cost, readmission_flag, readmission_risk_category | Total Encounters, Readmission Rate, Avg Length of Stay, Avg Cost Per Encounter, PMPM, Inpatient/Emergency Encounters |
| `fact_prescription` | days_supply, quantity_dispensed, is_generic, is_chronic_medication, pharmacy_type, total_cost, payer_paid, patient_copay | Total Fills, Generic Fill Rate, Avg Rx Cost Per Fill, Payer Rx Cost, Patient Copay Total |
| `agg_medication_adherence` | drug_class, therapeutic_area, pdc_score, adherence_category, gap_days, is_chronic | Avg PDC Score, Adherent Rate |
| `fact_diagnosis` | diagnosis_type, present_on_admission | Unique Diagnoses, Chronic Diagnoses, Patients with Chronic Conditions |
| `dim_payer` | payer_name, payer_type | — |
| `dim_provider` | display_name, specialty, department *(filter is_current = 1)* | — |
| `dim_patient` | gender, age, age_group, insurance_type, city, state *(filter is_current = 1)* | Total Patients, Chronic Rate, Avg Patient Age |
| `dim_diagnosis` | icd_description, icd_category, is_chronic | — |
| `dim_medication` | medication_name, generic_name, drug_class, therapeutic_area, is_chronic | — |
| `dim_date` | full_date, month_name, quarter, year, fiscal_year, fiscal_quarter | — |
| `dim_sdoh` | risk_tier, social_vulnerability_index, poverty_rate, food_desert_flag, median_household_income | — |

**PII caution (`dim_patient`):** leave `first_name`, `last_name`, `address`, `phone`, `email`,
`insurance_policy_number`, and `date_of_birth` **out** of the AI data schema. Row-level patient
lookups should go through the lakehouse SQL path with explicit intent, not Copilot aggregates.

---

## 4. AI instructions — *Add AI instructions* (⚠️ Fabric / Power BI service UI)

**Prep data for AI → Add AI instructions.** This is the model's prompt: business context,
terminology, measure preferences, analysis rules, and benchmarks. The DAX tool reads this (not
the agent prompt, not `datasource.json`) when answering from the model. Paste the block below.
(10,000-character limit; keep it grouped by theme as shown — order and grouping affect output.)

```
BUSINESS CONTEXT
You answer for a hospital analytics team over a Gold-layer star schema covering claim denials, encounters and readmissions, prescriptions and medication adherence, diagnoses, social determinants, providers, and payers. Audiences are clinical and revenue-cycle leaders. Lower denial rate, lower readmission rate, higher collection rate, and higher medication adherence are positive.

TERMINOLOGY (map how users speak to the model)
- "denials" / "denied claims" = fact_claim where denial_flag = 1; the reason is primary_denial_reason (blank when not denied).
- "denial rate" = the [Denial Rate] measure (0-1 ratio shown as %). Never recompute it.
- "collection rate" = [Collection Rate]. "at-risk revenue" = [At Risk Revenue].
- "readmission" / "bounce-back" = a 30-day readmission, fact_encounter where readmission_flag = 1; use [Readmission Rate].
- "adherence" / "PDC" / "compliance" = agg_medication_adherence; adherent means pdc_score >= 0.80; use [Avg PDC Score] and [Adherent Rate]; adherence_category is the bucket.
- "LOS" = [Avg Length of Stay] (days). "PMPM" = [PMPM]. "generic rate" = [Generic Fill Rate].
- "chronic" = is_chronic = 1 on dim_diagnosis / dim_medication / agg_medication_adherence.

MEASURE-FIRST RULE
For any rate, count, total, average, trend, or breakdown, use the model's existing measures instead of re-deriving math:
- Denials & revenue (fact_claim): Total Claims, Denial Rate, Collection Rate, Total Billed, Total Paid, At Risk Revenue, Avg Denial Risk.
- Encounters & readmissions (fact_encounter): Total Encounters, Readmission Rate, Avg Length of Stay, Avg Cost Per Encounter, PMPM, Total Charges, YoY Charge Growth, Inpatient Encounters, Emergency Encounters.
- Pharmacy (fact_prescription): Total Fills, Generic Fill Rate, Avg Rx Cost Per Fill, Payer Rx Cost, Patient Copay Total.
- Adherence (agg_medication_adherence): Avg PDC Score, Adherent Rate.
- Diagnoses (fact_diagnosis): Unique Diagnoses, Chronic Diagnoses, Patients with Chronic Conditions.
- Patients (dim_patient): Total Patients, Chronic Rate, Avg Patient Age.

WHERE THE FACTS LIVE
- Denials/financials -> fact_claim. Encounters/readmissions/cost/LOS -> fact_encounter.
- Pharmacy fills/cost -> fact_prescription. Medication adherence (PDC) -> agg_medication_adherence (already aggregated). Diagnoses -> fact_diagnosis + dim_diagnosis.

GROUP-BY / JOIN RULES
- Group by the descriptive dimension attribute, never a *_key column:
  payer -> dim_payer[payer_name] or [payer_type]; provider -> dim_provider[display_name] or [specialty];
  date/trend -> dim_date[month_name] / [year]; diagnosis -> dim_diagnosis[icd_description] / [icd_category];
  community/SDOH -> dim_sdoh[risk_tier] (join on zip_code).
- For provider and patient (Type-2 SCD), always filter is_current = 1 so each entity counts once.
- agg_* tables are pre-aggregated; never also sum the matching fact table for the same metric (avoids double counting).

ANALYSIS RULES
- State the time period and grain in every answer. Format rates as %, money as $, durations in days.
- For "top N", order by the relevant measure descending and return N rows.
- Aggregate by default; only surface individual patient identifiers when explicitly asked.
- If a measure returns 0 or blank, say it may be filtered or unavailable rather than asserting a true zero, and suggest a refinement.

BENCHMARKS (context and recommendations, not filters)
- Readmission rate < 15%   - Denial rate < 8%   - Collection rate > 95%
- PDC adherent >= 80%      - Generic fill rate >= 85%   - Inpatient length of stay 4-6 days
When a metric beats or misses its benchmark, say so and suggest a concrete next step.
```

---

## 5. Verified answers — *Verified answers* (⚠️ built in Power BI Desktop)

A **verified answer = trigger phrases + one approved report visual + optional filters.** It is
**not** a query and **not** a text answer. You build the visual once; Copilot returns that exact
human-approved visual whenever a user's prompt matches a trigger phrase.

**How to create each one:**
1. In **Power BI Desktop** (a report on this model), build the visual described under **Visual**.
2. Right-click the visual header → **Set up a verified answer**.
3. Add the **Trigger phrases** listed (aim for 5–7; users phrase things differently and Copilot
   also matches semantically — don't swap the measure or fields, just reword).
4. Add the **Available-to-users filter** so one verified answer covers many slices (the filter
   must already exist on the report, unlocked, set to *All*).
5. **Apply**, then publish/save. The entry then appears under **Prep data for AI → Verified
   answers**.

> The small DAX under each entry is only a **reference for what the visual must show** — build
> the visual to match it; you don't paste DAX anywhere. Every measure/column below exists in the
> model. Keep the fields used by a verified answer **visible** in the AI data schema, or it won't return.

### VA1 — Top denial reasons
- **Trigger phrases:** "Top denial reasons" · "What are the most common reasons claims are denied?" · "Why are claims being denied?" · "Leading causes of denials" · "Denial reasons by volume"
- **Visual:** Clustered bar chart. Axis = `fact_claim[primary_denial_reason]`, Value = **Total Claims**, **visual-level filter `denial_flag = 1`**, sort descending, Top 5.
- **Available-to-users filter:** `dim_payer[payer_type]`.
```dax
-- reference: what the visual displays
TOPN(5,
  SUMMARIZECOLUMNS(fact_claim[primary_denial_reason],
    "Denied Claims", CALCULATE([Total Claims], fact_claim[denial_flag] = 1)),
  [Denied Claims], DESC)
```

### VA2 — Denial rate by payer
- **Trigger phrases:** "Denial rate by payer" · "Which payers deny the most?" · "Compare denial rates across payers" · "Payer denial performance" · "Show denial rate for each payer"
- **Visual:** Bar chart (or table). Axis = `dim_payer[payer_name]`, Value = **Denial Rate** (add **Total Claims** as a tooltip), sort by Denial Rate descending.
- **Available-to-users filter:** `dim_payer[payer_type]`.
```dax
-- reference
SUMMARIZECOLUMNS(dim_payer[payer_name],
  "Denial Rate", [Denial Rate], "Total Claims", [Total Claims])
```

### VA3 — 30-day readmission rate (trend)
- **Trigger phrases:** "What's our readmission rate?" · "30-day readmission rate" · "Readmission rate over time" · "How are readmissions trending?" · "Show readmission rate by month"
- **Visual:** Line chart. Axis = `dim_date[month_name]` (in date order), Value = **Readmission Rate**; optionally a Card showing the overall **Readmission Rate**.
- **Available-to-users filter:** `fact_encounter[encounter_type]`.
```dax
-- reference (overall)
ROW("Readmission Rate", [Readmission Rate], "Total Encounters", [Total Encounters])
```

### VA4 — Medication adherence (PDC) by drug class
- **Trigger phrases:** "Medication adherence by drug class" · "PDC by drug class" · "Which drug classes have the lowest adherence?" · "Adherence by therapeutic area" · "Show PDC scores"
- **Visual:** Bar chart. Axis = `agg_medication_adherence[drug_class]`, Value = **Avg PDC Score**, add a constant line at **0.80** (adherence threshold), sort ascending to surface the worst.
- **Available-to-users filter:** `agg_medication_adherence[therapeutic_area]`.
```dax
-- reference
SUMMARIZECOLUMNS(agg_medication_adherence[drug_class], "Avg PDC", [Avg PDC Score])
```

### VA5 — Average length of stay by encounter type
- **Trigger phrases:** "Average length of stay" · "LOS by encounter type" · "How long are inpatient stays?" · "Average LOS for inpatients" · "Length of stay breakdown"
- **Visual:** Bar chart. Axis = `fact_encounter[encounter_type]`, Value = **Avg Length of Stay** (days), sort descending.
- **Available-to-users filter:** `dim_date[year]`.
```dax
-- reference
SUMMARIZECOLUMNS(fact_encounter[encounter_type], "Avg LOS", [Avg Length of Stay])
```

### VA6 — Generic fill rate by pharmacy type
- **Trigger phrases:** "Generic fill rate" · "Generic dispensing rate" · "Generic rate by pharmacy" · "How much do we fill generic?" · "GDR by pharmacy type"
- **Visual:** Bar chart. Axis = `fact_prescription[pharmacy_type]`, Value = **Generic Fill Rate** (%), add a constant line at the overall rate, sort descending.
- **Available-to-users filter:** `dim_medication[therapeutic_area]`.
```dax
-- reference
SUMMARIZECOLUMNS(fact_prescription[pharmacy_type], "Generic Fill Rate", [Generic Fill Rate])
```

### VA7 — Payer mix
- **Trigger phrases:** "What's our payer mix?" · "Payer mix" · "Claims by payer type" · "Revenue by payer" · "Breakdown by payer"
- **Visual:** Donut/stacked bar. Legend/Axis = `dim_payer[payer_type]`, Value = **Total Paid** (and optionally **Total Claims** as a second view).
- **Available-to-users filter:** `dim_date[year]`.
```dax
-- reference
SUMMARIZECOLUMNS(dim_payer[payer_type], "Total Paid", [Total Paid], "Total Claims", [Total Claims])
```

### VA8 — Chronic-condition patient counts
- **Trigger phrases:** "How many patients have chronic conditions?" · "Chronic condition counts" · "Patients with chronic conditions" · "Chronic patients by condition" · "Top chronic conditions"
- **Visual:** Bar chart. Axis = `dim_diagnosis[icd_category]`, Value = **Patients with Chronic Conditions**, sort descending (top N).
- **Available-to-users filter:** `dim_diagnosis[is_chronic]`.
```dax
-- reference
SUMMARIZECOLUMNS(dim_diagnosis[icd_category], "Patients with Chronic Conditions", [Patients with Chronic Conditions])
```

---

## 6. Evaluation question set (regression test)

Use this to sanity-check the agent (and plain Copilot/Q&A) after any change to the model,
the AI data schema, AI instructions, verified answers, or the synonym schema. Ask each
question; confirm the answer uses the **expected measure** at the **expected grain**. If a
question that should hit a verified answer instead free-forms a different visual, the trigger
phrases need tuning. Every measure/column below exists in the model.

| # | Question | Expected measure / source | Expected grain | Linked VA |
|---|----------|---------------------------|----------------|-----------|
| Q1 | "What's our overall denial rate?" | `[Denial Rate]` (fact_claim) | single value | VA2 |
| Q2 | "Show denial rate by payer" | `[Denial Rate]` × `dim_payer[payer_name]` | by payer | VA2 |
| Q3 | "What's the 30-day readmission rate?" | `[Readmission Rate]` (fact_encounter) | single value | VA3 |
| Q4 | "Readmission rate by month" | `[Readmission Rate]` × `dim_date[month_name]` | monthly trend | VA3 |
| Q5 | "Which drug classes have the lowest adherence?" | `[Avg PDC Score]` × `agg_medication_adherence[drug_class]` | by drug class, asc | VA4 |
| Q6 | "Average length of stay for inpatients" | `[Avg Length of Stay]` × `fact_encounter[encounter_type]` | by encounter type | VA5 |
| Q7 | "What's our generic fill rate?" | `[Generic Fill Rate]` (fact_prescription) | single value | VA6 |
| Q8 | "What's our payer mix?" | `[Total Paid]` × `dim_payer[payer_type]` | by payer type | VA7 |
| Q9 | "How many patients have chronic conditions?" | `[Patients with Chronic Conditions]` | single value | VA8 |
| Q10 | "Top chronic conditions by patient count" | `[Patients with Chronic Conditions]` × `dim_diagnosis[icd_category]` | top N | VA8 |
| Q11 | "What's our collection rate?" | `[Collection Rate]` (fact_claim) | single value | — |
| Q12 | "Total revenue at risk from denials" | `[At Risk Revenue]` (fact_claim) | single value | — |
| Q13 | "Average cost per encounter" | `[Avg Cost Per Encounter]` (fact_encounter) | single value | — |
| Q14 | "How many patients do we have?" | `[Total Patients]` (dim_patient) | single value | — |
| Q15 | "What share of patients are chronic?" | `[Chronic Rate]` (dim_patient) | single value | — |

**Pass criteria:** correct measure chosen (not a manual SUM/AVERAGE of a raw column),
correct grain, and ratios shown as **%** (not 0). Synonyms make Q3/Q5/Q7 resolvable even
when a user says "bounce-backs", "compliance", or "generic rate".

---

## 7. Fixed earlier — formatString display bug

`fact_claim` measures **Denial Rate** and **Collection Rate** returned correct ratios (0–1)
but had `formatString: 0`, so the UI rounded them to a whole number and they displayed as
**0** — the cause of the "denial rate = 0%" you saw. **Fixed:** both now use
`formatString: 0.0%` in `fact_claim.tmdl`. Confirm the display once the model re-syncs.
