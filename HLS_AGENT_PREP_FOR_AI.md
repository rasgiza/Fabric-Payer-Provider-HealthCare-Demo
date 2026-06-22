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
> - Make the model AI-ready: descriptions on tables/columns/measures, AI instructions, and
>   verified answers, all configured in Prep for AI on the model.
> - Verified answers behave like example queries to imitate. **RLS/OLS is NOT enforced on
>   verified-answer SQL/DAX**, so do not embed row-restricted logic you rely on for security.

## What deploys how (read first)

| Layer | Lives in | Deploys via |
|---|---|---|
| **A. Agent-level instructions** (operational prompt) | `HealthcareHLSAgent.DataAgent/.../stage_config.json` | ✅ API / Git sync |
| **B. Data-source instructions** (schema, routing, SQL rules, values) | `.../datasource.json` | ✅ API / Git sync |
| **C. Model-level *Prep for AI* instructions** | Semantic model → *Prep for AI* pane | ⚠️ **Fabric UI only — copy-paste** |
| **D. Verified answers** (NL → saved visual) | Created in **Power BI Desktop** (right-click visual → *Set up verified answer*); surfaces in service *Prep data for AI → Verified answers* | ⚠️ **Desktop + service UI** |

**Why the split:** model-level Prep-for-AI instructions (C) and verified answers (D)
**cannot be updated through the API today**, so they are documented here for you to paste
into the Fabric UI by hand. Keep A intentionally thin — it should only tell the agent *how to
reason over the sources and shape its answers*, never repeat the schema/value detail that
belongs in B, or the domain context that belongs in C.

## ⚠️ To get good answers from the semantic model, you MUST do the UI steps

Git sync deploys Layers A and B automatically. But when the agent answers a question from the
**`HealthcareDemoHLS` semantic model** (the PRIMARY source), the DAX generation tool **ignores
the agent prompt** and reads **only** the model's Prep-for-AI configuration. So the model-level
instructions (C) and verified answers (D) are not optional polish — they are *where the
agent's semantic-model intelligence comes from*. Skip them and the agent will guess at
business terms, pick the wrong measure, and miss your standard breakdowns.

**One-time setup for the model owner.** The `HealthcareDemoHLS` semantic model has a
**Prep data for AI** pane (in the Fabric / Power BI **service**) with three steps:
*Simplify the data schema*, *Verified answers*, and *Add AI instructions*. Two of those are
edited right in the service; verified answers are created in **Power BI Desktop** and then
show up back in this pane.

1. **Add AI instructions** (in the service → Prep data for AI → *Add AI instructions*) → paste
   Section 3 of this doc (benchmarks + business rules).
2. *(Optional, recommended)* **Simplify the data schema** (in the service → same pane) → keep
   only AI-relevant tables and measures to cut ambiguity; add synonyms for terms users say.
3. **Verified answers** → these are **created in Power BI Desktop**, not typed in the service.
   In Desktop, build a report on this model with a visual that shows the answer, then
   **right-click the visual → "Set up verified answer"** and add the phrasings users will ask
   (5–7 each). Section 4 gives the DAX that defines what each visual should display — use it to
   build the visual, not to paste. **Once you publish/save, go back to the Fabric UI → Prep data
   for AI → Verified answers and you'll see the new entries reflected there.**
4. Re-test the agent, then iterate — add an instruction or verified answer whenever you see a
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

## 2. Data-source instructions — Layer B (deployed via API)

Home for everything source-specific: table routing, schemas, allowed values, SCD
`is_current = 1` filtering, and SQL/DAX rules. For the live lakehouse source this already
lives in `datasource.json`. For the semantic-model source, paste the block below.

```
Prefer the model's existing measures over re-deriving math:
  Denial Rate, Collection Rate, Net Collection Rate, Readmission Rate, Avg Days to Payment,
  Appeal Success Rate, Total Appeal Recovery, Avg PDC Score, Adherent Rate,
  DRG Margin, Avg Cost Per Encounter.

Where the facts live:
- Denials/financials -> fact_claim. denial_flag = 1 means denied; reason in primary_denial_reason
  (blank when not denied). Denial Rate and Collection Rate are ratios 0-1; present as percentages.
- Encounters/readmissions/cost -> fact_encounter. readmission_flag = 1 = 30-day readmission.
- Pharmacy fills -> fact_prescription. is_generic = 1 = generic dispensed.
- Diagnoses -> fact_diagnosis joined to dim_diagnosis (is_chronic = 1 = chronic condition).
- Medication adherence (PDC) -> agg_medication_adherence. Adherent = pdc_score >= 0.80;
  adherence_category already buckets it. drug_class and therapeutic_area are on this table.

Aggregated (agg_*) tables are already rolled up — never also sum the matching fact table for
the same measure (avoids double counting). Use agg_readmission_by_date and
agg_medication_adherence for trend and summary questions.

Join keys (group by the dimension attribute, not the key):
  *_date_key   -> dim_date[date_key]
  payer_key    -> dim_payer[payer_name / payer_type]
  provider_key -> dim_provider[display_name / specialty]   (filter is_current = 1)
  patient_key  -> dim_patient                               (filter is_current = 1)
  diagnosis_key-> dim_diagnosis[icd_description / icd_category]
  zip_code     -> dim_sdoh (community SDOH context)
```

---

## 3. Model-level *Prep for AI* instructions — Layer C (⚠️ copy-paste into Fabric UI)

Paste this into the semantic model's **Prep for AI → instructions** pane. It holds the
domain context that does **not** belong in the thin agent prompt. Cannot be set via API.

```
BENCHMARKS (use for context and recommendations, not as filters):
- Readmission rate < 15%
- Denial rate < 8%
- PDC adherent >= 80%
- Inpatient length of stay 4-6 days
- RVU attainment >= 95%
- Board-certified rate >= 85%
- Documentation score >= 80
- EHR adoption >= 80%
- Patient satisfaction >= 4.0
- Telehealth enabled >= 50%

When a metric beats or misses its benchmark, say so and suggest a concrete next step.
```

---

## 4. Verified answers — Layer D (⚠️ created in Power BI Desktop, then surfaced in the Fabric UI)

**How verified answers are actually created (preview):**
1. In **Power BI Desktop**, open a report built on this model, **right-click a visual** that
   shows the answer, and select **"Set up verified answer"**.
2. Add the common phrases / questions users might ask about that data.
3. Publish/save. Back in the Fabric **service** → the model's **Prep data for AI → Verified
   answers** tab now lists the entry. Copilot and the data agent then return that saved visual
   when users ask a related question.

So each DAX block below is the **spec for the visual to build** — it defines the exact measures,
columns, filters, and sort the visual must use. Build a visual matching the DAX in Desktop, then
right-click it and attach the trigger phrasings. The DAX assumes the measures and columns
described in the TMDL.

### Q1 — Top 5 denial reasons by denied-claim count
```dax
EVALUATE
TOPN(
    5,
    SUMMARIZECOLUMNS(
        fact_claim[primary_denial_reason],
        "Denied Claims", CALCULATE(COUNTROWS(fact_claim), fact_claim[denial_flag] = 1)
    ),
    [Denied Claims], DESC
)
ORDER BY [Denied Claims] DESC
```

### Q2 — Top 5 denial reasons by denied dollars
```dax
EVALUATE
TOPN(
    5,
    SUMMARIZECOLUMNS(
        fact_claim[primary_denial_reason],
        "Denied Amount", CALCULATE(SUM(fact_claim[billed_amount]), fact_claim[denial_flag] = 1)
    ),
    [Denied Amount], DESC
)
ORDER BY [Denied Amount] DESC
```

### Q3 — Denial rate by payer
```dax
EVALUATE
SUMMARIZECOLUMNS(
    dim_payer[payer_name],
    "Denial Rate", [Denial Rate],
    "Total Claims", [Total Claims]
)
ORDER BY [Denial Rate] DESC
```

### Q4 — Overall 30-day readmission rate
```dax
EVALUATE
ROW(
    "Readmission Rate", [Readmission Rate],
    "Total Encounters", [Total Encounters]
)
```

### Q5 — Medication adherence (PDC) for a named patient
```dax
EVALUATE
CALCULATETABLE(
    SUMMARIZECOLUMNS(
        agg_medication_adherence[drug_class],
        "Avg PDC", [Avg PDC Score],
        "Adherence", SELECTEDVALUE(agg_medication_adherence[adherence_category])
    ),
    dim_patient[first_name] = "Betty",
    dim_patient[last_name]  = "Brown",
    dim_patient[is_current] = 1
)
```

### Q6 — Average days in A/R by payer
```dax
EVALUATE
SUMMARIZECOLUMNS(
    dim_payer[payer_name],
    "Avg Days to Payment", [Avg Days to Payment]
)
ORDER BY [Avg Days to Payment] DESC
```

### Q7 — Appeal success rate and recovery by payer
```dax
EVALUATE
SUMMARIZECOLUMNS(
    dim_payer[payer_name],
    "Appeal Success Rate", [Appeal Success Rate],
    "Total Appeal Recovery", [Total Appeal Recovery]
)
ORDER BY [Appeal Success Rate] DESC
```

---

## 5. Fixed this session \u2014 formatString display bug

`fact_claim` measures **Denial Rate** and **Collection Rate** returned correct ratios (0\u20131)
but had `formatString: 0`, so the UI rounded them to a whole number and they displayed as
**0** \u2014 the cause of the "denial rate = 0%" you saw. **Fixed:** both now use
`formatString: 0.0%` in `fact_claim.tmdl`. Confirm the display once the model re-syncs.
