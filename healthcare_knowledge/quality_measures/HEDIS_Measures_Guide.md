# Lakeside Health System — HEDIS Measures Guide

**Effective Date:** Measurement Year 2025  
**Applicable Plans:** All commercial (PAY001-005, PAY009), Medicare Advantage (PAY006/007), Medicaid (PAY008)  
**NCQA HEDIS Version:** MY 2025  
**Approved By:** Chief Quality Officer, VP Population Health

---

## 1. Overview

HEDIS (Healthcare Effectiveness Data and Information Set), developed and maintained by the **National Committee for Quality Assurance (NCQA)**, is the **gold standard** for measuring quality in managed care. These specifications follow **NCQA HEDIS Technical Specifications, Measurement Year (MY) 2025**. Performance on HEDIS measures directly impacts:
- **CMS Star Ratings** (Medicare Advantage plans — PAY006/007) — per CMS Medicare Part C & D Star Ratings Technical Notes, October 2024
- **Payer contract incentive payments** (commercial plans)
- **State Medicaid quality withholds** (PAY008)
- **Public reporting and reputation**

### 1.1 Financial Impact at Lakeside
| Component | Annual Impact |
|-----------|-------------|
| Medicare Stars bonus payments (4+ star) | $2.5M - $5M |
| Commercial quality incentives | $1.2M - $2.8M |
| Medicaid quality withholds (at risk) | $800K |
| **Total quality-linked revenue** | **$4.5M - $8.6M** |

## 2. Diabetes Care Measures (CDC — Comprehensive Diabetes Care)

**Eligible Population:** Patients aged 18-75 with E11.9 (Type 2 Diabetes Mellitus)  
**Clinical Basis:** ADA Standards of Care 2024 (ElSayed NA et al., *Diabetes Care* 2024;47(Suppl 1):S1-S321) and NCQA HEDIS CDC measure specifications.

### 2.1 HbA1c Testing
| Measure | HEDIS ID | Target | Current |
|---------|----------|--------|---------|
| % with at least one HbA1c test annually | CDC-HT | ≥ 90% | Track via fact_encounter + lab results |

**Compliance Actions:**
- Outreach to patients without HbA1c in last 12 months
- Standing lab orders for all active diabetic patients
- CPT 80053 (CMP) often ordered alongside — ensure HbA1c added

### 2.2 HbA1c Poor Control (>9%)
| Measure | HEDIS ID | Target | Lower is Better |
|---------|----------|--------|----------------|
| % with HbA1c > 9% | CDC-H9 | < 15% | YES — this is an inverse measure |

**Clinical Interventions:**
- Patients on Metformin (860974) only → Consider adding Glipizide (311040) per step therapy
- Patients on dual oral therapy → Evaluate for Insulin Glargine (1373463)
- Assess adherence (fact_prescription PDC analysis)
- Referral to diabetes education program
- SDOH barrier assessment (dim_sdoh — food insecurity, inability to afford medications)

### 2.3 HbA1c Good Control (<8%)
| Measure | HEDIS ID | Target |
|---------|----------|--------|
| % with HbA1c < 8% | CDC-H8 | ≥ 65% |

### 2.4 Blood Pressure Control (<140/90)
| Measure | HEDIS ID | Target |
|---------|----------|--------|
| % of diabetics with last BP < 140/90 | CDC-BP | ≥ 70% |

**Medication Review:**
- Lisinopril (314076) or Losartan (310798) = preferred (renoprotective + BP control)
- Add Amlodipine (197361) if not at target
- If on 3+ agents and uncontrolled → resistant hypertension workup

### 2.5 Eye Exam (Retinal)
| Measure | HEDIS ID | Target |
|---------|----------|--------|
| % with dilated retinal exam in measurement year OR negative prior year | CDC-EE | ≥ 60% |

**Workflow:** Auto-referral to ophthalmology at diabetes diagnosis, annual recall letter

### 2.6 Statin Therapy
| Measure | HEDIS ID | Target |
|---------|----------|--------|
| % aged 40-75 with diabetes received statin therapy | SPC-DM | ≥ 80% |
| % with statin adherence (PDC ≥ 80%) | SPC-ADH | ≥ 75% |

**Medication:** Atorvastatin 20 MG (200031) — Tier 1 formulary, no barriers

## 3. Cardiovascular Measures

### 3.1 Controlling High Blood Pressure (CBP)
**Eligible Population:** All patients aged 18-85 with I10 (Essential Hypertension)  
**Clinical Basis:** 2017 ACC/AHA/AAPA Guideline for Prevention, Detection, Evaluation, and Management of High Blood Pressure (Whelton PK et al., *J Am Coll Cardiol*. 2018;71(19):e127-e248).

| Measure | HEDIS ID | Target |
|---------|----------|--------|
| % with adequate BP control (< 140/90) | CBP | ≥ 65% |

**Priority Medications:**
| Tier | Medication | RxNorm | Role |
|------|-----------|--------|------|
| 1st line | Lisinopril 10 MG | 314076 | ACE Inhibitor |
| 2nd line | Amlodipine 5 MG | 197361 | Calcium Channel Blocker |
| 3rd line | Losartan 50 MG | 310798 | ARB (ACE intolerant) |
| Add-on | Metoprolol 50 MG | 866924 | Beta blocker (esp. if concurrent HF) |
| Volume mgmt | Furosemide 40 MG | 310429 | If fluid overload (HF patients) |

### 3.2 Statin Therapy for ASCVD
**Eligible Population:** Patients with I25.10 (Atherosclerotic Heart Disease)

| Measure | HEDIS ID | Target |
|---------|----------|--------|
| % received statin therapy | SPC-ASCVD | ≥ 85% |
| % with statin PDC ≥ 80% | SPC-ASCVD-ADH | ≥ 80% |

**Medication:** Atorvastatin 20 MG (200031) — high-intensity (40-80 mg) for established ASCVD

### 3.3 Persistence of Beta-Blocker Treatment After Heart Attack
**Eligible Population:** Patients with I25.10 who had acute event

| Measure | HEDIS ID | Target |
|---------|----------|--------|
| % on beta-blocker ≥ 180 days post-AMI | PBH | ≥ 85% |

**Medication:** Metoprolol Succinate 50 MG (866924)

## 4. Behavioral Health Measures

### 4.1 Antidepressant Medication Management (AMM)
**Eligible Population:** Patients with new F32.9 (Depression) diagnosis and antidepressant prescription  
**Clinical Basis:** APA Practice Guideline for the Treatment of Major Depressive Disorder, 3rd ed. (2010, reaffirmed 2015).

| Measure | HEDIS ID | Target | Definition |
|---------|----------|--------|-----------|
| Effective Acute Phase Treatment | AMM-A | ≥ 60% | Remained on antidepressant ≥ 84 days |
| Effective Continuation Phase | AMM-C | ≥ 45% | Remained on antidepressant ≥ 180 days |

**Preferred Medications:**
- Sertraline 50 MG (312938) — Tier 1, SSRI
- Escitalopram 10 MG (312036) — Tier 1, SSRI

**Key Gap:** Many patients discontinue antidepressants at 30-60 days when symptoms improve. Pharmacy outreach at day 30, 60, and 90 improves continuation rates.

### 4.2 Follow-up After Hospitalization for Mental Illness (FUH)
| Measure | HEDIS ID | Target |
|---------|----------|--------|
| 7-day follow-up | FUH-7 | ≥ 50% |
| 30-day follow-up | FUH-30 | ≥ 70% |

### 4.3 Use of Opioids at High Dosage (HDO)
| Measure | HEDIS ID | Target | Lower is Better |
|---------|----------|--------|----------------|
| % with ≥ 90 MME/day for ≥ 15 days | HDO | < 5% | YES |

**Relevant Medication:** Hydrocodone/APAP (856987) — monitor total daily MME across all providers

## 5. Respiratory Measures

### 5.1 Use of Spirometry Testing in Assessment of COPD (SPR)
**Eligible Population:** Patients with new J44.9 (COPD) diagnosis

| Measure | HEDIS ID | Target |
|---------|----------|--------|
| % with spirometry testing within 24 months of new diagnosis | SPR | ≥ 40% |

### 5.2 Pharmacotherapy Management of COPD Exacerbation (PCE)
**Eligible Population:** Patients with J44.1 (COPD exacerbation) requiring ED/inpatient

| Measure | HEDIS ID | Target |
|---------|----------|--------|
| Systemic corticosteroid within 14 days of event | PCE-CS | ≥ 75% |
| Bronchodilator within 30 days of event | PCE-BD | ≥ 85% |

**Medications:** Albuterol (895994) for bronchodilator, systemic steroids documented

### 5.3 Medication Management for People with Asthma (MMA)
**Eligible Population:** Patients aged 5-64 with J45.909 (Asthma)

| Measure | HEDIS ID | Target |
|---------|----------|--------|
| % with ≥ 75% medication compliance (controller) | MMA-75 | ≥ 45% |

**Medication:** Fluticasone Propionate 110 MCG (896188) — controller inhaler

## 6. Utilization Measures

### 6.1 Plan All-Cause Readmissions (PCR)
**Eligible Population:** All acute inpatient discharges

| Measure | HEDIS ID | Target | Lower is Better |
|---------|----------|--------|----------------|
| 30-day all-cause readmission rate (observed/expected) | PCR | O/E < 1.0 | YES |

**Tracked in:** agg_readmission_by_date, linked with fact_encounter

### 6.2 Ambulatory Care — ED Visits
| Measure | HEDIS ID | Target | Lower is Better |
|---------|----------|--------|----------------|
| ED visits per 1,000 member months | AMB-ED | < 50 | YES |

**Facilities tracked:** FAC001, FAC003, FAC006, FAC008 (facilities with ED capability)

## 7. Medication Adherence Measures (Medicare Stars — Triple Weighted!)

These measures are **triple-weighted** in CMS Star Ratings (per CMS Medicare Part C & D Star Ratings Technical Notes, October 2024), meaning they have **3× the impact** on a plan's overall Star Rating. Improving a half-star on these measures alone can generate **millions in CMS quality bonus payments**. Adherence is measured using **Proportion of Days Covered (PDC)** per NCQA HEDIS Medication Adherence specifications.

### 7.1 Three Adherence Measures
| Measure | Drug Class | Medications at Lakeside | PDC Target |
|---------|-----------|----------------------|-----------|
| Diabetes Medication Adherence | Biguanide, SU, Insulin | Metformin (860974), Glipizide (311040), Insulin Glargine (1373463) | ≥ 80% |
| RAS Antagonist Adherence | ACE Inhibitor, ARB | Lisinopril (314076), Losartan (310798) | ≥ 80% |
| Statin Adherence | Statin | Atorvastatin (200031) | ≥ 80% |

### 7.2 Adherence Improvement Strategies
| Strategy | Implementation | Impact |
|----------|---------------|--------|
| 90-day supply | Default for chronic medications at all pharmacies | +8-12% PDC |
| Automatic refills | Opt-in program with pharmacy partners | +5-8% PDC |
| Medication synchronization | Align all chronic med refill dates | +3-5% PDC |
| Pharmacist phone outreach | PDC < 70% at day 90 → pharmacist call | +10-15% PDC |
| Home delivery | Mail-order for maintenance meds | +5-7% PDC |
| Cost reduction | Generic-first (Tier 1), 340B pricing at eligible facilities | Remove cost barrier |

### 7.3 Data Agent Queries for Adherence
- "What is the average medication adherence rate by drug class?"
- "Which medications have the lowest PDC?"
- "How does medication adherence correlate with readmission rates?"
- "Which payers have patients with the lowest adherence?"
- "What is the adherence rate trend over the last 6 months?"

## 8. HEDIS Measure Performance by Payer

| Payer | Priority Measures | Incentive Model |
|-------|------------------|----------------|
| BCBS MI (PAY001) | CBP, CDC (all), AMM | Pay-for-performance bonus pool |
| Aetna (PAY002) | CDC, PCR, Med Adherence | Shared savings |
| United Healthcare (PAY003) | CDC, CBP, PCE | Stars-based bonus |
| Medicare (PAY006/007) | **All measures — Stars rating** | CMS bonus payments at 4+ stars |
| Medicaid MI (PAY008) | CDC, CBP, AMM, FUH | Quality withhold (at-risk) |
| Priority Health (PAY009) | CBP, CDC, PCR | Value-based contract |

## 9. Reporting and Tracking

### 9.1 Quarterly Performance Review
| Quarter | Action |
|---------|--------|
| Q1 (Jan-Mar) | Baseline measurement, gap identification |
| Q2 (Apr-Jun) | Intervention deployment, mid-year check |
| Q3 (Jul-Sep) | Intensify outreach for gaps, "sprint" campaigns |
| Q4 (Oct-Dec) | Final push, ensure all services documented before year-end |

### 9.2 Analytics Integration
All HEDIS measures can be tracked through the existing Gold layer:
- **dim_patient** — demographic eligibility
- **dim_diagnosis** — condition identification
- **fact_encounter** — service utilization
- **fact_prescription** — medication fills and PDC calculation
- **fact_claim** — paid services confirmation
- **dim_payer** — plan-specific measurement
- **agg_readmission_by_date** — PCR tracking

---

*Last Updated: 2025-01-15 | Next Review: 2025-04-01 (Quarterly)*  
*Document ID: QM-HEDIS-001 | Version: 2025.1*

---

## References & Sources

1. NCQA HEDIS Measurement Year 2025: Volume 1 — Narrative. National Committee for Quality Assurance. https://www.ncqa.org/hedis/
2. NCQA HEDIS MY 2025: Volume 2 — Technical Specifications for Health Plans. https://www.ncqa.org/hedis/measures/
3. CMS Core Quality Measures Collaborative (CQMC). https://www.cms.gov/Medicare/Quality-Initiatives-Patient-Assessment-Instruments/QualityMeasures/Core-Measures
4. ADA Standards of Care in Diabetes — 2024 (for CDC, HbA1c measures). *Diabetes Care*. 2024;47(Suppl 1).
5. ACC/AHA Blood Pressure Guidelines (2017) — for Controlling Blood Pressure (CBP) measure. Whelton PK, et al. *J Am Coll Cardiol*. 2018;71(19):e127-e248.
6. USPSTF Preventive Services Recommendations (for BCS, CCS, COL screening measures). https://www.uspreventiveservicestaskforce.org/uspstf/recommendation-topics
7. CMS Electronic Clinical Quality Measures (eCQMs). https://ecqi.healthit.gov/ecqms
