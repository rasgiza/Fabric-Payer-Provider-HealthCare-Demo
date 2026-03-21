# Lakeside Health System — Hospital Readmission Reduction Program (HRRP) Guide

**CMS Program:** Hospital Readmission Reduction Program  
**Applicable Facilities:** FAC001 (Lakeside Main Hospital), FAC006 (Lakeside Children's Hospital), FAC008 (Lakeside South Campus)  
**Effective:** FY 2025 (October 2024 — September 2025)  
**Maximum Penalty:** 3% of Medicare base DRG payments

---

## 1. Program Overview

The CMS Hospital Readmission Reduction Program (HRRP), established by the Affordable Care Act Section 3025 (Public Law 111-148) and codified at **42 CFR 412.150-154**, penalizes hospitals with **excess 30-day readmission rates** for specific conditions. Penalties are calculated by comparing a hospital's readmission performance to the national average, adjusted for patient risk. Per Zuckerman RB et al. (*N Engl J Med*. 2016;374(16):1543-1551), HRRP has been associated with a national reduction in readmissions of approximately 1.2 percentage points since implementation.

### 1.1 Penalty Calculation
```
Excess Readmission Ratio (ERR) = Hospital's Predicted Readmissions / Expected Readmissions

If ERR > 1.0 → Hospital has excess readmissions → Penalty applied
Penalty = 1 - Payment Adjustment Factor (up to 3% reduction)
```

### 1.2 Financial Exposure at Lakeside
| Facility | Medicare DRG Revenue | Max Penalty (3%) | Current Estimated Penalty |
|----------|---------------------|------------------|--------------------------|
| FAC001 — Main Hospital | $280M | $8.4M | ~$2.8M (1% based on current rates) |
| FAC006 — Children's Hospital | $45M | $1.35M | ~$0 (pediatric excluded) |
| FAC008 — South Campus | $125M | $3.75M | ~$1.5M (1.2% based on current rates) |
| **TOTAL** | **$450M** | **$13.5M** | **~$4.3M** |

## 2. HRRP Condition-Specific Readmission Targets

### 2.1 Penalty Conditions and Lakeside Performance

National averages from CMS Hospital Compare (data.cms.gov). Condition-specific readmission timing patterns per Dharmarajan K et al. (*JAMA*. 2013;309(4):355-363) — majority of HF readmissions occur in first 15 days post-discharge.

| Condition | ICD-10 | National Avg | Lakeside Target | Readmission Window |
|-----------|--------|-------------|----------------|-------------------|
| **Heart Failure** | I50.9 | 21.9% | < 18% | 30 days |
| **Pneumonia** | J18.9 | 15.7% | < 14% | 30 days |
| **COPD** | J44.9, J44.1 | 19.7% | < 17% | 30 days |
| **AMI** | I25.10 | 15.3% | < 14% | 30 days |
| **TKA/THA** | CPT 27447, 27130 | 4.4% | < 4% | 30 days |
| **CABG** | CPT 33533 | 12.9% | < 12% | 30 days |

### 2.2 Condition-Specific Risk Factors

#### Heart Failure (I50.9) — Highest Volume, Highest Risk

Risk factors below are based on published literature including Krumholz HM et al. (*Circulation*. 2009;119(14):1977-2016) and Ross JS et al. (*JAMA*. 2010;303(17):1716-1722). Odds ratios from multi-center analyses.

| Risk Factor | Data Source | Odds Ratio |
|------------|-------------|-----------|
| Prior admission within 6 months | fact_encounter | 2.8x |
| Medication non-adherence (PDC < 60%) | fact_prescription + dim_medication | 2.5x |
| EF < 30% (HFrEF) | dim_diagnosis | 2.2x |
| CKD comorbidity (N18.3) | dim_diagnosis | 1.9x |
| Diabetes comorbidity (E11.9) | dim_diagnosis | 1.7x |
| Depression (F32.9) | dim_diagnosis | 1.6x |
| Low income zip code | dim_sdoh | 1.5x |
| Age > 75 | dim_patient | 1.4x |
| Discharged without follow-up within 7 days | fact_encounter | 2.1x |

**Critical Medications for HF Readmission Prevention:**
- Lisinopril 10 MG (314076) or Losartan 50 MG (310798) — GDMT
- Metoprolol Succinate 50 MG (866924) — Evidence-based beta blocker
- Furosemide 40 MG (310429) — Volume management
- Atorvastatin 20 MG (200031) — If concurrent ASCVD (I25.10)

#### Pneumonia (J18.9)
| Risk Factor | Odds Ratio |
|------------|-----------|
| Age > 65 | 1.8x |
| COPD comorbidity (J44.9) | 2.0x |
| CHF comorbidity (I50.9) | 1.9x |
| Immunocompromised | 2.3x |
| Incomplete antibiotic course | 1.7x |
| Tobacco use | 1.5x |

**Critical Medications:**
- Amoxicillin 500 MG (308182) — Oral step-down
- Azithromycin 250 MG (197511) — Atypical coverage

#### COPD (J44.9/J44.1)
| Risk Factor | Odds Ratio |
|------------|-----------|
| ≥ 2 exacerbations in prior year | 3.1x |
| Active smoking | 2.4x |
| Depression comorbidity (F32.9) | 1.8x |
| Incorrect inhaler technique | 1.6x |
| No pulmonary rehab referral | 1.5x |

**Critical Medications:**
- Albuterol MDI (895994) — Rescue bronchodilator
- Fluticasone 110 MCG (896188) — Controller (eosinophilic phenotype)

## 3. Readmission Reduction Interventions

### 3.1 Evidence-Based Interventions by Evidence Level

Evidence levels per Hansen LO et al. (*Ann Intern Med*. 2011;155(8):520-528) systematic review of readmission reduction strategies. Number Needed to Treat (NNT) estimates from RCT meta-analyses.

| Intervention | Evidence Level | NNT | Implementation Status |
|-------------|---------------|-----|---------------------|
| Structured discharge planning | Level A | 20 | Active at FAC001, FAC008 |
| Post-discharge phone call (48-72 hrs) | Level A | 25 | Active system-wide |
| Medication reconciliation at discharge | Level A | 15 | Active system-wide |
| Transition coach program (high-risk) | Level B | 12 | Pilot at FAC001 |
| Remote patient monitoring | Level B | 18 | Telehealth program expanding |
| 7-day post-discharge visit | Level A | 14 | Target: 85% completion |
| Patient education (teach-back) | Level B | 30 | Training in progress |
| Pharmacist-led discharge counseling | Level A | 16 | Active at FAC001, FAC006 |

### 3.2 Condition-Specific Bundles

#### CHF Discharge Bundle (I50.9)
1. ✅ GDMT optimization before discharge (Lisinopril/Losartan + Metoprolol + Furosemide)
2. ✅ Daily weight education with threshold parameters
3. ✅ Sodium restriction < 2000 mg education
4. ✅ Fluid restriction education (if NYHA III-IV)
5. ✅ Medication reconciliation with pharmacist
6. ✅ Cardiology follow-up within 7 days scheduled
7. ✅ 48-hour post-discharge phone call
8. ✅ Home health referral (if meets criteria)
9. ✅ Remote monitoring enrollment (if eligible)
10. ✅ SDOH barrier screen and intervention plan

#### Pneumonia Discharge Bundle (J18.9)
1. ✅ Antibiotic course with specific stop date
2. ✅ Clinical stability criteria met (afebrile 24 hrs, O2 baseline)
3. ✅ Smoking cessation referral (if applicable)
4. ✅ Pneumococcal / flu vaccination (if not current)
5. ✅ Follow-up within 7-14 days
6. ✅ Return-to-ED criteria education
7. ✅ Chest X-ray follow-up scheduled (if not cleared at discharge)

#### COPD Discharge Bundle (J44.9/J44.1)
1. ✅ Albuterol (895994) and controller inhaler verified
2. ✅ Inhaler technique demonstrated by patient
3. ✅ Written COPD action plan (green/yellow/red zones)
4. ✅ Oral steroid taper prescribed (if applicable)
5. ✅ Smoking cessation referral
6. ✅ Pulmonary rehab referral (for ≥ 2 exacerbations/year)
7. ✅ Pulmonology follow-up within 7 days

### 3.3 SDOH-Informed Readmission Prevention
| SDOH Factor | dIm_sdoh Field | Readmission Impact | Intervention |
|------------|---------------|-------------------|-------------|
| Food insecurity | food_desert_flag | +1.4x CHF readmission | Medically-tailored meal program |
| Transportation | transit_score | +1.3x missed follow-up | Medical transport arrangement |
| Low income | median_income | +1.5x medication non-adherence | 340B pricing, assistance programs |
| Low health literacy | education_pct | +1.6x medication errors | Pictorial guides, teach-back |
| Social isolation | pct_living_alone | +1.3x delayed care-seeking | Daily check-in calls for high-risk |

## 4. Analytics and Monitoring

### 4.1 Key Dashboards (Gold Layer Data)

| Dashboard | Metrics | Data Tables |
|-----------|---------|-------------|
| **Readmission Trend** | 30-day rate by month, by condition | agg_readmission_by_date |
| **Readmission by Condition** | Rates per ICD-10, benchmarked to national | fact_encounter + dim_diagnosis |
| **Readmission by Facility** | FAC001, FAC006, FAC008 comparison | fact_encounter + dim_facility |
| **Readmission by Payer** | Medicare vs commercial vs Medicaid | fact_encounter + dim_payer |
| **Discharge Bundle Compliance** | % of applicable patients receiving full bundle | Process measure tracking |
| **Medication Adherence Post-DC** | PDC at 30, 60, 90 days post-discharge | fact_prescription |

### 4.2 Real-Time Alerts
| Alert | Trigger | Action |
|-------|---------|--------|
| High-risk patient discharged | Risk score ≥ 8 at discharge | Auto-assign transition coach |
| 48-hour phone call overdue | No documented call by hour 50 | Escalate to care coordinator manager |
| Follow-up not scheduled | No appointment within 7 days of discharge | Block discharge until scheduled |
| Readmission detected | Same patient admitted within 30 days | Trigger RCA review within 48 hours |

### 4.3 Post-Readmission Root Cause Analysis
Every readmission within 30 days triggers an RCA:
1. Was the original discharge appropriate (timing, clinical stability)?
2. Was the discharge bundle complete?
3. Was the post-discharge phone call made?
4. Was the follow-up appointment kept?
5. Were medications available and taken?
6. Were there SDOH barriers?
7. Was the readmission related to the index admission?
8. What could have prevented this readmission?

## 5. CMS Reporting Timeline

| Activity | Timeline |
|----------|---------|
| Data collection period | 3-year rolling window |
| CMS calculates ERR | March-June of following year |
| Preview report available | August |
| Hospital dispute period | 30 days from preview |
| Final penalty published | October (start of fiscal year) |
| Penalty applied | All Medicare DRG payments for fiscal year |

## 6. Competitive Benchmarking

### 6.1 Peer Hospital Comparison
When benchmarking, compare against:
- National average (CMS published)
- State of Michigan average
- Similar-sized health systems (350-500 bed)
- Top decile performers (aspirational target)

### 6.2 Data Agent Queries for Benchmarking
- "What is our 30-day readmission rate by condition compared to target?"
- "Which facility has the lowest readmission rate for heart failure?"
- "What is the readmission trend over the past 12 months?"
- "How does medication adherence correlate with readmission for CHF patients?"
- "What percentage of readmitted patients had a 7-day follow-up visit?"
- "Which payer's patients have the highest readmission rate?"

---

*Last Updated: 2025-01-20 | Next Review: 2025-07-20*  
*Document ID: QM-HRRP-003 | Version: 3.0*

---

## References & Sources

1. CMS Hospital Readmission Reduction Program (HRRP). 42 CFR 412.150-154. https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/AcuteInpatientPPS/Readmissions-Reduction-Program
2. Affordable Care Act (ACA) Section 3025. Public Law 111-148. https://www.congress.gov/bill/111th-congress/house-bill/3590
3. CMS Hospital Compare — Readmission Measures Methodology. https://www.cms.gov/Medicare/Quality-Initiatives-Patient-Assessment-Instruments/HospitalQualityInits/Measure-Methodology
4. Dharmarajan K, Hsieh AF, Lin Z, et al. Diagnoses and Timing of 30-Day Readmissions After Hospitalization for Heart Failure, Acute Myocardial Infarction, or Pneumonia. *JAMA*. 2013;309(4):355-363.
5. Zuckerman RB, Sheingold SH, Orav EJ, Ruhter J, Epstein AM. Readmissions, Observation, and the Hospital Readmissions Reduction Program. *N Engl J Med*. 2016;374(16):1543-1551.
6. CMS Excess Readmission Ratio (ERR) Methodology. https://qualitynet.cms.gov/inpatient/measures/readmission/methodology
