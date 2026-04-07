# Power BI Dashboard Guide

Step-by-step instructions for building Power BI reports on the **HealthcareDemoHLS** semantic model deployed by this demo. The semantic model uses **Direct Lake** mode -- no data import or refresh scheduling needed.

---

## Prerequisites

- Demo deployment completed (pipeline has run, Gold tables populated)
- Semantic model `HealthcareDemoHLS` visible in your Fabric workspace
- Power BI Desktop (optional -- you can build entirely in the web)

---

## Quick Start: Auto-Create Report in Fabric

1. Open your Fabric workspace
2. Find **HealthcareDemoHLS** (type: Semantic model)
3. Click the **...** menu -> **Auto-create a report**
4. Fabric generates a starting report with key visuals
5. Click **Edit** to customize

Or: **+ New item** -> **Report** -> **Pick a semantic model** -> select `HealthcareDemoHLS`

---

## Semantic Model Overview

### Tables (13)

| Table | Type | Row Count (Default) | Description |
|-------|------|---------------------|-------------|
| `dim_patient` | SCD2 Dimension | ~10,000 | Patient demographics, insurance, zip code |
| `dim_provider` | SCD2 Dimension | ~500 | Provider name, specialty, department, NPI |
| `dim_payer` | Dimension | 12 | Insurance payer names and types |
| `dim_diagnosis` | Dimension | ~1,500 | ICD-10 codes, descriptions, categories |
| `dim_medication` | Dimension | ~200 | Drug names, classes, therapeutic areas |
| `dim_sdoh` | Dimension | ~560 | Social determinants by zip code |
| `dim_date` | Date Dimension | ~1,460 | Calendar table (4 years) |
| `fact_encounter` | Fact | ~100,000 | Encounters with readmission risk scores |
| `fact_claim` | Fact | ~100,000 | Claims with denial flags and risk scores |
| `fact_prescription` | Fact | ~250,000 | Prescription fills with costs |
| `fact_diagnosis` | Fact | ~200,000 | Patient-encounter diagnosis assignments |
| `agg_medication_adherence` | Aggregate | varies | PDC scores by patient and medication |
| `agg_readmission_by_date` | Aggregate | varies | Daily readmission rate aggregates |

### Relationships (21)

The model has 17 active relationships and 4 inactive date relationships. Key relationship patterns:

```
dim_date ----< fact_encounter (discharge_date_key)
dim_date ----< fact_claim (claim_date_key)
dim_date ----< fact_prescription (fill_date_key)
dim_date ----> agg_readmission_by_date (encounter_date_key)

dim_patient ----< fact_encounter (patient_key)
dim_patient ----< fact_claim (patient_key)
dim_patient ----< fact_prescription (patient_key)
dim_patient ----< fact_diagnosis (patient_key)
dim_patient ----< agg_medication_adherence (patient_key)
dim_patient ----> dim_sdoh (zip_code)

dim_provider ----< fact_encounter (provider_key)
dim_provider ----< fact_claim (provider_key)
dim_provider ----< fact_prescription (provider_key)

dim_payer ----< fact_claim (payer_key)
dim_payer ----< fact_prescription (payer_key)

dim_medication ----< fact_prescription (medication_key)
dim_medication ----< agg_medication_adherence (medication_key)

dim_diagnosis ----< fact_diagnosis (diagnosis_key)
```

**Inactive relationships** (use `USERELATIONSHIP` in DAX):
- `fact_encounter.encounter_date_key` -> `dim_date.date_key`
- `fact_claim.payment_date_key` -> `dim_date.date_key`
- `fact_diagnosis.diagnosis_date_key` -> `dim_date.date_key`

### Pre-Built DAX Measures (26)

The model includes 26 measures ready for use in visuals:

#### Encounter Measures
| Measure | DAX | Description |
|---------|-----|-------------|
| `Total Encounters` | `COUNTROWS(fact_encounter)` | Total encounter count |
| `Readmission Rate` | `DIVIDE(CALCULATE(COUNTROWS, readmission_flag=TRUE), COUNTROWS)` | % encounters that are readmissions |
| `High Risk Readmissions` | `CALCULATE(COUNTROWS, risk_category="High")` | Count of high-risk encounters |
| `Medium Risk Readmissions` | `CALCULATE(COUNTROWS, risk_category="Medium")` | Count of medium-risk encounters |
| `Low Risk Readmissions` | `CALCULATE(COUNTROWS, risk_category="Low")` | Count of low-risk encounters |
| `Avg Length of Stay` | `AVERAGE(fact_encounter[length_of_stay])` | Mean LOS in days |
| `Avg Readmission Risk` | `AVERAGE(fact_encounter[readmission_risk_score])` | Mean risk score (0-1) |
| `Total Charges` | `SUM(fact_encounter[total_charges])` | Total encounter charges |
| `PY Charges` | `SAMEPERIODLASTYEAR` on Total Charges | Prior year charges |
| `YoY Charge Growth` | `DIVIDE(CY - PY, PY)` | Year-over-year charge growth % |
| `YTD Charges` | `TOTALYTD` on charges | Year-to-date charges |

#### Claim Measures
| Measure | DAX | Description |
|---------|-----|-------------|
| `Total Claims` | `COUNTROWS(fact_claim)` | Total claim count |
| `Denial Rate` | `DIVIDE(denied count, total count)` | % claims denied |
| `Total Billed` | `SUM(fact_claim[billed_amount])` | Sum of all billed amounts |
| `Total Paid` | `SUM(fact_claim[paid_amount])` | Sum of all paid amounts |
| `Collection Rate` | `DIVIDE(Total Paid, Total Billed)` | Paid / Billed ratio |
| `At Risk Revenue` | High + Medium denial risk billed amount | Revenue at risk of denial |
| `Avg Denial Risk` | `AVERAGE(fact_claim[denial_risk_score])` | Mean denial risk score |
| `MTD Claims` | `TOTALMTD` on claim count | Month-to-date claim count |
| `Paid by Payment Date` | Uses inactive relationship | Paid amount by payment date |

#### Adherence Measures
| Measure | DAX | Description |
|---------|-----|-------------|
| `Adherent Rate` | `DIVIDE(Adherent count, total count)` | % members with PDC >= 0.8 |
| `Avg PDC Score` | `AVERAGE(pdc_score)` | Mean proportion of days covered |
| `High Risk Denials` | Count of High denial risk claims | Cross-table measure |

#### Other Measures
| Measure | DAX | Description |
|---------|-----|-------------|
| `Total Patients` | `CALCULATE(COUNTROWS, is_current=TRUE)` | Active patient count |
| `Total Fills` | `COUNTROWS(fact_prescription)` | Total prescription fills |
| `Total Rx Cost` | `SUM(fact_prescription[total_cost])` | Total prescription spend |

---

## Recommended Report Pages

### Page 1: Executive Summary

**Purpose:** High-level KPIs for leadership

| Visual | Type | Fields |
|--------|------|--------|
| KPI Card | Card | `Total Patients` |
| KPI Card | Card | `Readmission Rate` (target: 15%) |
| KPI Card | Card | `Denial Rate` (target: 8%) |
| KPI Card | Card | `Adherent Rate` (target: 80%) |
| KPI Card | Card | `Total Charges` |
| KPI Card | Card | `Collection Rate` |
| Encounters by Month | Line chart | X: `dim_date[month_name]`, Y: `Total Encounters` |
| Denial Rate by Payer | Bar chart | X: `dim_payer[payer_name]`, Y: `Denial Rate` |
| Risk Distribution | Donut chart | Legend: `fact_encounter[readmission_risk_category]`, Values: count |

**Slicers:** `dim_date[year]`, `dim_date[quarter]`, `dim_patient[insurance_type]`

---

### Page 2: Claim Denials & Revenue Cycle

**Purpose:** Denial root cause analysis and revenue impact

| Visual | Type | Fields |
|--------|------|--------|
| KPI Cards | Cards | `Total Claims`, `Denial Rate`, `At Risk Revenue`, `Total Billed`, `Total Paid` |
| Denial Rate by Payer | Stacked bar | X: `dim_payer[payer_name]`, Y: `Denial Rate` |
| Top Denial Reasons | Horizontal bar | Y: `fact_claim[primary_denial_reason]`, X: count of denied claims |
| Denial Trend | Line chart | X: `dim_date[month_name]`, Y: `Denial Rate` |
| Provider Denial Rates | Table | `dim_provider[display_name]`, `dim_provider[specialty]`, `Total Claims`, `Denial Rate` |
| Claims by Status | Donut | `fact_claim[claim_status]` (Approved/Denied/Pending) |
| Collection Rate by Payer | Clustered bar | X: `dim_payer[payer_name]`, Y: `Collection Rate` |

**Slicers:** `dim_payer[payer_name]`, `fact_claim[claim_status]`, `dim_date[year]`

---

### Page 3: Readmission Risk

**Purpose:** Identify high-risk patients and readmission trends

| Visual | Type | Fields |
|--------|------|--------|
| KPI Cards | Cards | `Readmission Rate`, `High Risk Readmissions`, `Avg Length of Stay`, `Avg Readmission Risk` |
| Readmission Trend | Line chart | X: `dim_date[month_name]`, Y: Readmission Rate from `agg_readmission_by_date` |
| Risk Distribution | Stacked bar | X: `fact_encounter[readmission_risk_category]`, Y: count |
| Risk by Encounter Type | Clustered bar | X: `fact_encounter[encounter_type]`, Y: `Avg Readmission Risk` |
| Top High-Risk Patients | Table | `dim_patient[first_name]`, `dim_patient[last_name]`, `dim_patient[age]`, `fact_encounter[readmission_risk_score]` |
| LOS by Risk Category | Clustered bar | X: `fact_encounter[readmission_risk_category]`, Y: `Avg Length of Stay` |

**Slicers:** `fact_encounter[encounter_type]`, `fact_encounter[readmission_risk_category]`, `dim_date[year]`

---

### Page 4: Medication Adherence

**Purpose:** PDC monitoring and HEDIS Star Rating alignment

| Visual | Type | Fields |
|--------|------|--------|
| KPI Cards | Cards | `Adherent Rate`, `Avg PDC Score`, `Total Fills`, `Total Rx Cost` |
| Adherence by Drug Class | Bar chart | X: `dim_medication[drug_class]`, Y: `Avg PDC Score` |
| Adherence Category Distribution | Donut | `agg_medication_adherence[adherence_category]` (Adherent/Partial/Non-Adherent) |
| Non-Adherent Patients | Table | `dim_patient[first_name]`, `dim_patient[last_name]`, `dim_medication[drug_class]`, PDC score, gap_days |
| Cost by Therapeutic Area | Treemap | `dim_medication[therapeutic_area]`, size: `Total Rx Cost` |
| Adherence Trend | Line | X: `dim_date[month_name]`, Y: `Adherent Rate` |

**Slicers:** `dim_medication[drug_class]`, `dim_medication[therapeutic_area]`, `agg_medication_adherence[adherence_category]`

---

### Page 5: Social Determinants of Health (SDOH)

**Purpose:** Population health stratification by social risk factors

| Visual | Type | Fields |
|--------|------|--------|
| KPI Cards | Cards | Patient count in high SDOH risk, avg SVI, food desert patient count |
| Risk Tier Distribution | Donut | `dim_sdoh[risk_tier]` (High/Medium/Low), patient count |
| Readmission Risk by SDOH Tier | Clustered bar | X: `dim_sdoh[risk_tier]`, Y: `Avg Readmission Risk` |
| Denial Rate by Poverty Level | Scatter | X: `dim_sdoh[poverty_rate]`, Y: `Denial Rate`, size: patient count |
| Food Desert Impact | KPI | Compare readmission rate in food desert vs non-food-desert zip codes |
| SDOH by Zip Code | Table | `dim_sdoh[zip_code]`, `dim_sdoh[poverty_rate]`, `dim_sdoh[social_vulnerability_index]`, `dim_sdoh[food_desert_flag]`, patient count |

**Slicers:** `dim_sdoh[risk_tier]`, `dim_sdoh[food_desert_flag]`, `dim_patient[state]`

---

### Page 6: Provider Performance

**Purpose:** Provider-level analytics for contract management and quality improvement

| Visual | Type | Fields |
|--------|------|--------|
| KPI Cards | Cards | Provider count, `Total Encounters`, `Total Charges` |
| Top Providers by Charges | Horizontal bar | Y: `dim_provider[display_name]`, X: `Total Charges` |
| Provider Denial Rates | Table | `dim_provider[display_name]`, `dim_provider[specialty]`, claim count, `Denial Rate` |
| Encounters by Specialty | Donut | `dim_provider[specialty]`, encounter count |
| LOS by Provider | Table | `dim_provider[display_name]`, `Avg Length of Stay`, encounter count |
| Charges YoY Growth | Line | X: `dim_date[month_name]`, Y: `Total Charges`, `PY Charges` |

**Slicers:** `dim_provider[specialty]`, `dim_provider[department]`, `dim_date[year]`

---

## Building the Dashboard: Step-by-Step

### Option A: Build in Fabric Web (Recommended)

1. Navigate to your workspace in the Fabric portal
2. Click **+ New item** -> **Report** -> **Pick a semantic model**
3. Select `HealthcareDemoHLS`
4. The field list shows all 13 tables and 26 measures
5. Drag fields onto the canvas to build visuals
6. Use the page layouts above as a guide
7. **Save** -> name the report (e.g., `Healthcare Analytics Dashboard`)

### Option B: Build in Power BI Desktop

1. Open Power BI Desktop
2. **Home** -> **OneLake data hub** -> find `HealthcareDemoHLS`
3. Click **Connect** (uses Direct Lake -- no import)
4. Build visuals using the field list
5. **File** -> **Save to OneLake** -> select your workspace

### Design Tips

- **Use the pre-built measures** instead of dragging raw columns into value wells. The measures handle NULLIF, SCD2 filtering, and time intelligence correctly.
- **Add conditional formatting** to highlight values above/below benchmarks (e.g., denial rate > 8% in red).
- **Use bookmarks** to create a toggleable view between summary KPIs and detailed tables.
- **Set cross-filter** to "Filter" (not highlight) for cleaner page-level interactions.
- **Add a date slicer** on every page using `dim_date[full_date]` as a date range.

---

## Formatting & Theming

### Recommended Color Palette (Healthcare)

| Color | Hex | Use |
|-------|-----|-----|
| Primary Blue | `#0078D4` | Headers, primary metrics |
| Success Green | `#107C10` | Good performance (below target) |
| Warning Amber | `#FFB900` | Approaching threshold |
| Alert Red | `#D13438` | Above threshold / critical |
| Neutral Gray | `#605E5C` | Secondary text, borders |
| Background | `#FAF9F8` | Page background |

### Benchmark Conditional Formatting Rules

| Metric | Green | Amber | Red |
|--------|-------|-------|-----|
| Readmission Rate | < 12% | 12-15% | > 15% |
| Denial Rate | < 5% | 5-8% | > 8% |
| Adherent Rate | > 85% | 80-85% | < 80% |
| Collection Rate | > 90% | 80-90% | < 80% |
| Avg LOS (Inpatient) | < 4 days | 4-6 days | > 6 days |

---

## Direct Lake Considerations

The semantic model uses **Direct Lake** mode, which reads directly from Delta tables in OneLake without data import.

**Advantages:**
- No refresh scheduling needed -- data is always current
- Near-real-time analytics after pipeline runs
- No data duplication

**Limitations:**
- Requires F64+ Fabric capacity
- Complex DAX may fall back to DirectQuery (slower)
- Column cardinality limits apply

**If visuals show "Refresh required":**
1. Open the semantic model in your workspace
2. Click **Refresh now** -- this re-reads the Delta table metadata (not data copy)
3. Alternatively, the launcher's Cell 9 triggers a refresh automatically

---

## Extending the Dashboard

### Add RTI Tables

After RTI scoring notebooks run, the `Healthcare_RTI_DB` KQL database contains additional tables. To add them to a report:

1. Create a **new semantic model** or report connecting to the KQL database
2. Available RTI tables:
   - `rti_fraud_scores` -- Provider fraud risk with lat/long
   - `rti_care_gap_alerts` -- Point-of-care gap alerts with facility lat/long
   - `rti_highcost_alerts` -- High-cost member trajectories with lat/long
3. Use **Map visuals** with lat/long fields for geographic analysis
4. Use **KQL** connector for real-time dashboards on the Eventhouse

### Add Custom Measures

In Power BI Desktop or the web editing experience, create new measures:

```dax
// Example: 30-Day Readmission Rate for Inpatient Only
Inpatient Readmission Rate =
VAR _num = CALCULATE(
    COUNTROWS(fact_encounter),
    fact_encounter[readmission_flag] = TRUE(),
    fact_encounter[encounter_type] = "Inpatient"
)
VAR _den = CALCULATE(
    COUNTROWS(fact_encounter),
    fact_encounter[encounter_type] = "Inpatient"
)
RETURN DIVIDE(_num, _den)
```

```dax
// Example: Revenue Leakage (Billed - Paid for Approved Claims)
Revenue Leakage =
CALCULATE(
    SUM(fact_claim[billed_amount]) - SUM(fact_claim[paid_amount]),
    fact_claim[claim_status] = "Approved"
)
```

```dax
// Example: SDOH-Adjusted Readmission Rate
SDOH High Risk Readmission Rate =
CALCULATE(
    [Readmission Rate],
    dim_sdoh[risk_tier] = "High"
)
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No data in visuals | Run the pipeline first to populate Gold tables |
| "Refresh required" banner | Click Refresh on the semantic model (re-reads Delta metadata) |
| Measures show blank | Ensure facts have data; check `is_current = 1` on SCD2 dims |
| Slow visuals | Direct Lake may fall back to DirectQuery for complex DAX -- simplify the measure |
| Can't find semantic model | Check workspace -- it deploys in Stage 5, after notebooks and pipelines |
| Date slicer not working | Ensure `dim_date[full_date]` is used (not date_key), and Time Intelligence is enabled |
| Inactive relationships | Use `USERELATIONSHIP` in measure DAX for encounter_date, payment_date, diagnosis_date |
