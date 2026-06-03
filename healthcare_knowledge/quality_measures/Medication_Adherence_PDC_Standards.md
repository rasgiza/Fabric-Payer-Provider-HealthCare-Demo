# Lakeside Health System — Medication Adherence Standards (PDC and HEDIS)

**Effective:** January 1, 2025
**Authority:** Pharmacy Quality Alliance (PQA) measure specifications; NCQA HEDIS MY 2025 Technical Specifications
**Applicable Programs:** All chronic medication classes; CMS Star Ratings; commercial value-based contracts

---

## 1. Why Adherence Is Measured

Medication non-adherence is the single largest reversible driver of avoidable hospitalization and total cost of care. Per Cutler RL et al. (*BMJ Open*. 2018;8(1):e016982), the U.S. cost of non-adherence is estimated at **$100–$300 billion annually**, including ~125,000 deaths and 10% of hospitalizations.

For Lakeside, adherence performance directly drives:
- **CMS Star Ratings** — three triple-weighted measures (D08, D09, D10)
- **HEDIS adherence measures** — MAH-A, MAC-A, MAD-A
- **HRRP penalty exposure** — see `Readmission_Penalty_Program.md`
- **Total medical expense in capitated/risk contracts**

## 2. Proportion of Days Covered (PDC) — The Reference Measure

PDC is the gold-standard adherence metric, endorsed by PQA, CMS, and NCQA.

### 2.1 Definition

```
PDC = (Number of days in the measurement period covered by ≥ 1 fill of the target medication)
      ÷ (Number of days in the measurement period)
```

The measurement period typically begins on the **first fill date** of the target medication within the year and ends on the **last day of the measurement year** (or end of enrollment).

Per PQA *PDC Specifications v9.0* (PQA, 2024):
- Multiple fills of the **same drug class** are counted toward a single PDC for that class
- Days of supply that overlap from an earlier fill are **truncated** (not double-counted)
- Hospitalization and SNF days (where the medication is institutionally supplied) are **excluded** from both numerator and denominator

### 2.2 Lakeside Adherence Categories

These thresholds are reflected in `agg_medication_adherence.adherence_category`:

| Category | PDC Range | Clinical Interpretation |
|----------|-----------|------------------------|
| **Adherent** | ≥ 0.80 | Meets PQA quality threshold |
| **Partial** | 0.50 – 0.79 | Below threshold; intervention recommended |
| **Non-Adherent** | < 0.50 | High clinical risk; urgent MTM required |

The 0.80 threshold is empirically derived: Karve S et al. (*Curr Med Res Opin*. 2009;25(9):2303-2310) demonstrated that PDC ≥ 0.80 corresponds to clinically meaningful drug effect across cardiovascular, diabetes, and antihypertensive therapies.

## 3. PQA Adherence Measures Tracked at Lakeside

| Measure | Drug Class | Codes (RxNorm class examples) | Threshold |
|---------|-----------|-------------------------------|-----------|
| **PDC-RASA** | Renin-angiotensin system antagonists (ACE/ARB) | Lisinopril, Losartan | ≥ 0.80 |
| **PDC-AH** | Antihypertensives — broader bucket | + Amlodipine, HCTZ | ≥ 0.80 |
| **PDC-Statins** | HMG-CoA reductase inhibitors | Atorvastatin, Rosuvastatin | ≥ 0.80 |
| **PDC-Diabetes** | Non-insulin diabetes meds | Metformin, GLP-1 RA, SGLT2i | ≥ 0.80 |
| **PDC-Antiretrovirals** | HIV ART regimens | — | ≥ 0.90 |
| **PDC-Antipsychotics** | Atypical antipsychotics for schizophrenia | — | ≥ 0.80 |

## 4. NCQA HEDIS Adherence Measures (MY 2025)

NCQA's Medication Adherence measures align with PQA PDC for the most common chronic classes:

| HEDIS Measure | Description | Denominator | Threshold |
|---------------|-------------|-------------|-----------|
| **MAH-A** | Medication Adherence for Hypertension (RAS antagonists) | Members 18+ with ≥ 2 fills of an ACE/ARB/direct renin inhibitor | PDC ≥ 0.80 |
| **MAC-A** | Medication Adherence for Cholesterol (Statins) | Members 18+ with ≥ 2 statin fills | PDC ≥ 0.80 |
| **MAD-A** | Medication Adherence for Diabetes Medications | Members 18+ with ≥ 2 fills of non-insulin diabetes medications | PDC ≥ 0.80 |
| **MPM** | Annual Monitoring for Patients on Persistent Medications | Members on ACE/ARB or diuretics with annual lab monitoring | NA — process measure |
| **PCE** | Pharmacotherapy Management of COPD Exacerbation | COPD-AE patients receiving systemic corticosteroid + bronchodilator | ≥ 70% (steroid), ≥ 80% (bronchodilator) |

## 5. CMS Star Rating Adherence Measures (Triple-Weighted)

For Medicare Advantage and Part D plans, three of the most heavily weighted Star measures are adherence-based:

| Star Measure | PQA Source | CY 2025 Weight |
|-------------|-----------|---------------|
| **D08** Medication Adherence for Diabetes Medications | PQA PDC-Diabetes | 3× |
| **D09** Medication Adherence for Hypertension (RAS antagonists) | PQA PDC-RASA | 3× |
| **D10** Medication Adherence for Cholesterol (Statins) | PQA PDC-Statins | 3× |

A 5-percentage-point swing in any one of these can move a contract by half a Star, which translates directly into Quality Bonus Payments (QBP) under 42 CFR 422.260.

## 6. Intervention Mapping by Adherence Category

| Category | First-Line Intervention | Owner | Doc Reference |
|----------|-------------------------|-------|---------------|
| Adherent (≥ 0.80) | Reinforce; annual review | Provider | — |
| Partial (0.50–0.79) | Pharmacist outreach + MTM CMR | Pharmacist | `Medication_Therapy_Management_Protocol.md` |
| Non-Adherent (< 0.50) on ≥ 2 chronic meds | Enroll in **CCM** (CPT 99490) + MTM | Care coordinator | `Chronic_Care_Management_Program.md` |
| Non-Adherent post-discharge (< 30 days) | **TCM** (CPT 99495/99496) + MTM | Provider + Pharmacist | `Transitional_Care_Management_Program.md` |
| Non-Adherent on a HRRP-condition medication | High-priority CCM/TCM combo | Care coordinator | `Readmission_Penalty_Program.md` |

## 7. Common Causes of Non-Adherence (and Where to Look)

Per Brown MT & Bussell JK (*Mayo Clin Proc*. 2011;86(4):304-314) and Kvarnström K et al. (*Pharmaceutics*. 2021;13(7):1100):

1. **Cost** — check `fact_prescription.patient_copay` vs. payer/plan
2. **Pharmacy access** — check `dim_sdoh.risk_tier` and `dim_sdoh.transportation_score`
3. **Complexity / pill burden** — check medication count per patient
4. **Side effects** — check whether class has been switched repeatedly
5. **Health literacy / belief** — qualitative; assessed at MTM
6. **Forgetfulness** — addressed via 90-day fills, mail order, blister packs

## 8. References

1. Pharmacy Quality Alliance. *PQA Measure Specifications, Version 9.0*. PQA, 2024.
2. National Committee for Quality Assurance. *HEDIS Measurement Year 2025 Technical Specifications for Health Plans, Volume 2*. NCQA, 2024.
3. Centers for Medicare & Medicaid Services. *Medicare 2025 Part C and D Star Ratings Technical Notes*. CMS, October 2024.
4. Karve S, Cleves MA, Helm M, Hudson TJ, West DS, Martin BC. Good and poor adherence: optimal cut-point for adherence measures using administrative claims data. *Curr Med Res Opin*. 2009;25(9):2303-2310.
5. Cutler RL, Fernandez-Llimos F, Frommer M, Benrimoj C, Garcia-Cardenas V. Economic impact of medication non-adherence by disease groups: a systematic review. *BMJ Open*. 2018;8(1):e016982.
6. Brown MT, Bussell JK. Medication adherence: WHO cares? *Mayo Clin Proc*. 2011;86(4):304-314.
