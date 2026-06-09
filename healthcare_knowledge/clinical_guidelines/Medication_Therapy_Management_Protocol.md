# Lakeside Health System — Medication Therapy Management (MTM) Protocol

**Effective Date:** January 1, 2025
**Review Cycle:** Annual
**Approved By:** Chief Pharmacy Officer & Chief Medical Officer, Lakeside Health System
**Applicable Settings:** Ambulatory clinics, post-discharge follow-up, CCM/PCM enrollment

---

## 1. Scope and Statutory Basis

This protocol governs Lakeside's Medication Therapy Management program. MTM is a Medicare Part D required service under **Section 1860D-4(c) of the Social Security Act** (42 USC 1395w-104(c)) and is also a covered benefit under most Medicare Advantage and commercial value-based contracts. CMS minimum standards for Part D MTM programs are published annually (see *2025 Medicare Part D MTM Program Standards*, CMS-4205-F).

Lakeside extends MTM beyond Part D mandates to **all patients with PDC < 0.80 on any chronic medication class**, regardless of payer.

## 2. Eligibility Triggers

A patient enters Lakeside MTM when **any** of the following is true:

| Trigger | Source Field | Threshold |
|---------|-------------|----------|
| Non-adherent to a chronic medication | `agg_medication_adherence.adherence_category` | = 'Non-Adherent' (PDC < 0.50) |
| Partially adherent to a chronic medication | `agg_medication_adherence.adherence_category` | = 'Partial' (PDC 0.50-0.79) AND ≥ 2 chronic conditions |
| Discharged from inpatient/ED with high readmission risk | `fact_encounter.readmission_risk_category` | = 'High' |
| Polypharmacy | Distinct active medications | ≥ 8 chronic medications |
| Targeted condition + non-adherence | `dim_medication.therapeutic_area` ∈ {Cardiovascular, Diabetes, Mental Health, Respiratory} | PDC < 0.80 |

## 3. Comprehensive Medication Review (CMR)

A CMR is the core MTM intervention, billable under **CPT 99605** (initial, 15 min), **CPT 99606** (follow-up, 15 min), and **CPT 99607** (each additional 15 min). The CMR follows the structure recommended by the *PCMA / APhA MTM Core Elements v3.0*:

1. **Medication review** — every prescription, OTC, supplement, and PRN
2. **Personal medication record (PMR)** — patient-held list updated at the visit
3. **Medication-related action plan (MAP)** — patient-facing, plain-language steps
4. **Intervention** — provider contact, dose change, regimen simplification, deprescribing
5. **Documentation and follow-up** — within 30 days

### 3.1 Required Discussion Points
- Reason for non-adherence: cost, side effects, complexity, forgetfulness, beliefs (per Brown MT & Bussell JK, *Mayo Clin Proc*. 2011;86(4):304-314)
- Pharmacy access — flag pharmacy deserts via SDOH index (`dim_sdoh.risk_tier`)
- Single-pill combinations to reduce burden (especially HTN — see `Hypertension_Management_Guidelines.md` §3.4)
- Generic substitution opportunities (`dim_medication.is_generic`)
- Coordination with prescribing provider — review `agg_medication_adherence` results before the visit

## 4. Drug-Class-Specific Action Templates

### 4.1 Cardiovascular (HF, post-MI)
Per AHA/ACC HF Guideline (Heidenreich et al. 2022) — see `CHF_Management_Guidelines.md`:
- If non-adherent to ACE/ARB/ARNI → assess cough, hyperkalemia, cost; consider ARB substitution
- If non-adherent to beta blocker → assess fatigue, bradycardia, asthma; consider Metoprolol succinate ER
- If non-adherent to SGLT2i (dapagliflozin/empagliflozin) → assess GU symptoms, cost; **do not deprescribe** without cardiology input

### 4.2 Antihypertensives
Per 2017 ACC/AHA HTN Guideline — see `Hypertension_Management_Guidelines.md`:
- Verify home BP monitoring is in use
- Consolidate to single-pill combination if ≥ 2 agents
- If PDC < 0.50 across all antihypertensives → escalate to CCM enrollment

### 4.3 Diabetes
Per ADA *Standards of Care 2025* (*Diabetes Care* 2025;48(Suppl 1)) — see `Diabetes_Type2_Management.md`:
- Verify glucose monitoring frequency
- For Metformin non-adherence → assess GI tolerance, switch to ER formulation
- For insulin non-adherence → assess injection technique, cost, hypoglycemia fear

### 4.4 Mental Health
Per APA *Practice Guidelines for the Treatment of Patients With Major Depressive Disorder, 3rd Edition*:
- Antidepressant non-adherence in first 90 days drives HEDIS AMM failure
- Assess perceived efficacy, side effects (sexual, weight, sedation), stigma
- Coordinate with behavioral health provider — do not adjust dose without psychiatry input for bipolar/psychotic patients

## 5. Hand-Off to CCM / PCM / TCM

After CMR:

| Patient Profile | Next Program |
|-----------------|-------------|
| ≥ 2 chronic conditions, ongoing complexity | **CCM** — see `Chronic_Care_Management_Program.md` |
| 1 complex chronic condition | **PCM** — see `Chronic_Care_Management_Program.md` §5 |
| Recent inpatient/SNF discharge (< 30 days) | **TCM** — see `Transitional_Care_Management_Program.md` |
| Stable, education-only | Annual MTM follow-up |

## 6. Quality Measure Tie-In

- HEDIS *Medication Adherence for Hypertension / Cholesterol / Diabetes* (MAH-A, MAC-A, MAD-A) — PDC ≥ 0.80
- HEDIS *Annual Monitoring for Patients on Persistent Medications (MPM)*
- CMS Star Rating *Medication Adherence* triple-weighted measures (D08, D09, D10)
- PQA *Proportion of Days Covered* family

A successful MTM episode that lifts a Non-Adherent patient to PDC ≥ 0.80 directly improves all four measure families.

## 7. References

1. Centers for Medicare & Medicaid Services. *2025 Medicare Part D Medication Therapy Management Program Standards*. CMS, 2024.
2. American Pharmacists Association, National Association of Chain Drug Stores Foundation. *Medication Therapy Management in Pharmacy Practice: Core Elements of an MTM Service Model, Version 3.0*. APhA/NACDS Foundation, 2008.
3. Brown MT, Bussell JK. Medication adherence: WHO cares? *Mayo Clin Proc*. 2011;86(4):304-314.
4. Heidenreich PA, Bozkurt B, Aguilar D, et al. 2022 AHA/ACC/HFSA Guideline for the Management of Heart Failure. *Circulation*. 2022;145(18):e895-e1032.
