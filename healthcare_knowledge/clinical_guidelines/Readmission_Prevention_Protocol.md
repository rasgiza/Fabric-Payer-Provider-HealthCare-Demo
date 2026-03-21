# Lakeside Health System — Hospital Readmission Prevention Protocol

**Applicable Conditions:** I50.9 (CHF), J18.9 (Pneumonia), J44.9/J44.1 (COPD), E11.9 (Diabetes), I25.10 (ASHD)  
**Effective Date:** January 1, 2025  
**CMS Program:** Hospital Readmission Reduction Program (HRRP)  
**Approved By:** Chief Medical Officer & Chief Quality Officer  
**Applicable Facilities:** FAC001 (Lakeside Main Hospital), FAC006 (Lakeside Children's Hospital), FAC008 (Lakeside South Campus)

---

## 1. Overview

Lakeside Health System targets **< 15% all-cause 30-day readmission rate**, aligned with CMS HRRP benchmarks (42 CFR 412.150-154; Affordable Care Act Section 3025). Current performance and financial penalties are tracked through our Gold analytics layer (agg_readmission_by_date, fact_encounter).

### 1.1 CMS Penalty Conditions
Under the Hospital Readmission Reduction Program (HRRP), established by ACA Section 3025 and codified in 42 CFR 412.150-154, the following conditions incur CMS readmission penalties:
- **Heart Failure (I50.9)** — highest volume at Lakeside, highest penalty risk
- **Pneumonia (J18.9)** — seasonal variation, winter peaks
- **COPD (J44.9, J44.1)** — high 30-day return rate
- **AMI (I25.10)** — includes post-CABG (CPT 33533) patients
- **TKA/THA (CPT 27447, 27130)** — surgical readmissions

### 1.2 Financial Impact
Per CMS HRRP (42 CFR 412.152), the maximum penalty is **3% of total Medicare base operating DRG payments**:
- CMS penalty: Up to **3% of total Medicare (PAY006, PAY007) reimbursement**
- For Lakeside system (~$450M Medicare revenue): Maximum exposure **$13.5M/year**
- Each avoided readmission saves approximately **$15,000-$25,000** in direct costs
- Per Jencks et al. (*NEJM* 2009;360:1418-1428), approximately 20% of Medicare patients are readmitted within 30 days, costing Medicare over $17 billion annually

## 2. Risk Stratification at Admission

### 2.1 High-Risk Criteria (ANY of the following)
| Risk Factor | Details | Data Source |
|------------|---------|-------------|
| Prior readmission within 90 days | Check encounter history | fact_encounter |
| CHF with EF < 30% | NYHA Class III-IV | dim_diagnosis (I50.9) |
| ≥ 5 active medications | Polypharmacy risk | fact_prescription |
| Social determinants | Low income zip, no transportation | dim_sdoh |
| Medication non-adherence | PDC < 60% on any critical med | fact_prescription + dim_medication |
| Behavioral health diagnosis | F32.9, F41.9 co-occurring | dim_diagnosis |
| Uninsured/Medicaid | PAY008, PAY012 | dim_payer |
| Age ≥ 75 with ≥ 3 chronic conditions | Frailty risk | dim_patient |

### 2.2 Risk Score Calculation

Lakeside Health System uses a composite risk scoring model informed by the **LACE Index** and the **HOSPITAL Score** — both validated 30-day readmission risk tools published in peer-reviewed literature.

**LACE Index** (van Walraven C, Dhalla IA, Bell C, et al. *CMAJ*. 2010;182(5):551-557. doi:10.1503/cmaj.091117) — validated across 4,812 medical and surgical patients with C-statistic 0.684:
- **L** = Length of stay (0-7 points)
- **A** = Acuity of admission (0 or 3 points)
- **C** = Charlson Comorbidity Index (0-5 points)
- **E** = ED visits in prior 6 months (0-4 points)
- **LACE ≥ 10 = High risk** for 30-day readmission or death

**HOSPITAL Score** (Donze JD, Williams MV, et al. *JAMA Intern Med*. 2016;176(4):496-502) — validated internationally across 117,065 patients:
- Hemoglobin at discharge, Oncology, Sodium at discharge, Procedure during stay, Index admission Type, number of Admissions in prior year, Length of stay
- Score ≥ 5 = High risk

**Lakeside Composite Score** (extends LACE with SDOH and adherence data):
```
Risk Score = (Prior Admits x 3) + (Active Meds x 0.5) + (SDOH Risk x 2) + 
             (Non-Adherence x 2) + (BH Diagnosis x 1.5) + (Age Factor x 1)
```
- **Low Risk (0-3):** Standard discharge protocol
- **Medium Risk (4-7):** Enhanced transition bundle
- **High Risk (8+):** Intensive care coordination

## 3. Discharge Planning Bundle

Discharge interventions are based on Project RED (Re-Engineered Discharge) — a randomized controlled trial demonstrating 30% reduction in readmissions (Jack BW et al., *Ann Intern Med*. 2009;150(3):178-187) and the Care Transitions Intervention (Coleman EA et al., *Arch Intern Med*. 2006;166(17):1822-1828), which showed significant reduction in 30-day readmissions through patient-centered transition coaching.

### 3.1 ALL Patients (Standard) — Based on Project RED Principles

| Intervention | Timing | Owner | Documentation |
|-------------|--------|-------|---------------|
| Medication reconciliation | ≥ 24 hours before discharge | Pharmacy | Med rec completed in EHR |
| Discharge summary | Day of discharge | Attending physician | Must include: diagnosis, meds, follow-up plan |
| Patient education — Teach Back | Before discharge | Bedside RN | Document patient verbalization |
| Follow-up appointment scheduled | Before discharge | Care Coordinator | Within 7 days for CHF/COPD, 14 days for others |
| Prescription verification | Before discharge | Pharmacy | Confirm all Rxs sent/filled |

### 3.2 ENHANCED Bundle (Medium + High Risk)

| Intervention | Timing | Owner |
|-------------|--------|-------|
| Pharmacist bedside med review | Day before discharge | Clinical Pharmacist |
| Social work assessment | Within 24 hours of admission | Social Worker |
| Home health referral | Day of discharge | Care Coordinator |
| PCP notification | Day of discharge | Discharge nurse |
| Language-appropriate materials | Before discharge | Patient Education |

### 3.3 INTENSIVE Bundle (High Risk Only) — Based on Naylor Transitional Care Model (*J Am Geriatr Soc*. 2004;52(5):675-684)

| Intervention | Timing | Owner |
|-------------|--------|-------|
| Multidisciplinary rounds inclusion | Daily during stay | Care Management |
| Transition coach assignment | 48 hours before discharge | Transition Coach |
| 48-hour post-discharge phone call | 48 hours after discharge | RN Care Manager |
| Home visit (if Home Health) | Within 72 hours | Home Health Agency |
| Remote patient monitoring enrollment | Day of discharge | Telehealth Team |
| 7-day follow-up visit confirmed | Day of discharge | Scheduling + Care Coordinator |

## 4. Condition-Specific Protocols

### 4.1 Heart Failure (I50.9) — Highest Priority
- **Medication check:** Confirm on GDMT — Lisinopril (314076) OR Losartan (310798), Metoprolol (866924), Furosemide (310429)
- **Daily weight education:** Teach patient to weigh daily, report gain > 3 lbs in 1 day or > 5 lbs in 1 week
- **Dietary education:** Sodium restriction < 2000 mg/day, fluid restriction if NYHA III-IV
- **Follow-up:** Cardiology within **7 days** (non-negotiable)
- **Readmission target:** < 20% (CMS HF-specific benchmark)

### 4.2 COPD (J44.9, J44.1)
- **Medication check:** Albuterol (895994) rescue inhaler, Fluticasone (896188) maintenance
- **Inhaler technique verification:** Demonstrate before discharge
- **Pulmonary rehab referral:** All patients with ≥ 2 exacerbations per year
- **Smoking cessation:** Assess and document, refer to program
- **Action plan:** Written COPD action plan (green/yellow/red zones)
- **Follow-up:** Pulmonology within **7 days** of discharge

### 4.3 Pneumonia (J18.9)
- **Antibiotic completion plan:** Document remaining days and drug
  - Amoxicillin 500 MG (308182) — community acquired, mild
  - Azithromycin 250 MG (197511) — atypical coverage
- **Clinical stability criteria document** before discharge (afebrile 24 hrs, improving O2, eating)
- **Follow-up chest X-ray** if not cleared at discharge — schedule within 6 weeks
- **Vaccination check:** Pneumococcal, influenza (if seasonally appropriate)

### 4.4 Post-Surgical (CPT 27447/27130/33533)
- **Pain management transition:** Reduce Hydrocodone/APAP (856987) per opioid weaning protocol
  - Transition to Ibuprofen (310965) or Acetaminophen (313782) by POD 5-7
- **VTE prophylaxis:** Warfarin (836585) if indicated, with INR monitoring plan
- **Rehab plan:** Direct admit to Lakeside Rehabilitation Center (FAC007) if criteria met
- **Wound care instructions:** Document and teach back
- **Surgeon follow-up:** Within 10-14 days

## 5. Post-Discharge Monitoring

Post-discharge monitoring protocols align with CMS Transitional Care Management (TCM) requirements (CPT 99495/99496) and evidence from the Care Transitions Intervention (Coleman et al., *Arch Intern Med*. 2006;166:1822-1828).

### 5.1 Phone Call Protocol (48-72 hours) — Required per CMS TCM (CPT 99495/99496)
**Script for RN Care Manager:**
1. "How are you feeling since you got home?"
2. "Have you been able to take your medications as prescribed?"
3. "Do you have any questions about your medications?"
4. "Have you experienced any new symptoms?" (specific to condition)
5. "Do you have your follow-up appointment scheduled?"
6. "Do you need help with transportation, food, or prescriptions?"

**Escalation triggers:** New chest pain, weight gain > 3 lbs, fever, worsening shortness of breath, inability to take medications, missed follow-up appointment.

### 5.2 Telehealth Follow-up (7 days — for enrolled patients)
- Available at all facilities via existing telehealth encounter type
- Covers: symptom check, medication review, vitals review (if remote monitoring)
- Lower barrier for patients with transportation issues (SDOH factor)

### 5.3 Pharmacy Follow-up (14 days)
- Automated prescription refill check
- Adherence outreach for patients who haven't filled discharge medications
- PDC tracking initiated (target ≥ 80% at 30 days)

## 6. Social Determinants Integration

### 6.1 SDOH Risk Factors (from dim_sdoh)
High readmission risk SDOH factors tracked across our 8-state, 510 zip code coverage area:

| Factor | Intervention |
|--------|-------------|
| Low median income (< $35,000) | Financial assistance application, generic medication preference |
| Food desert zip code | Medically-tailored meal delivery referral |
| No transportation access | Arrange rides, offer telehealth alternative |
| Low health literacy | Pictorial medication guides, interpreter services |
| Lives alone, age > 70 | Home health mandatory, daily check-in call |
| High uninsured rate area | Connect to Medicaid (PAY008) enrollment |

### 6.2 Payer-Specific Discharge Resources
| Payer | Available Resources |
|-------|-------------------|
| Blue Cross Blue Shield of Michigan (PAY001) | Care management program, 24/7 nurse line |
| Medicare (PAY006/PAY007) | Transitional Care Management (TCM), Home Health benefit |
| Medicaid Michigan (PAY008) | Community Health Worker program, transportation benefit |
| Self-Pay (PAY012) | Financial counselor before discharge, charity care application |

## 7. Analytics and Reporting

### 7.1 Key Performance Indicators
| Metric | Target | Tracked In |
|--------|--------|-----------|
| All-cause 30-day readmission rate | < 15% | agg_readmission_by_date |
| CHF-specific readmission rate | < 20% | fact_encounter + dim_diagnosis |
| 7-day follow-up completion rate | ≥ 85% | fact_encounter |
| Discharge medication fill rate (48 hrs) | ≥ 90% | fact_prescription |
| Patient education completion | 100% | Documentation audit |
| Post-discharge phone call completion | ≥ 95% | Care management log |

### 7.2 Executive Dashboard Queries
The Data Agent can answer:
- "What is our 30-day readmission rate by condition and facility?"
- "Which facilities have the highest readmission rates?"
- "What is the correlation between medication adherence and readmission?"
- "How do readmission rates vary by payer?"
- "What SDOH factors are most associated with readmission?"

## 8. Roles and Responsibilities

| Role | Key Responsibility |
|------|-------------------|
| Attending Physician | Risk assessment, discharge orders, follow-up plan |
| Bedside Nurse | Teach back education, discharge checklist |
| Pharmacist | Medication reconciliation, adherence counseling |
| Care Coordinator | Follow-up scheduling, home health, transitions |
| Social Worker | SDOH assessment, payer navigation, community resources |
| Transition Coach | High-risk patients: 30-day engagement |
| Data Analytics | Monthly readmission reports, predictive modeling |

---

*Last Updated: 2025-01-20 | Next Review: 2026-01-20*  
*Protocol ID: QI-READMIT-003 | Version: 5.0*

---

## References & Sources

1. van Walraven C, Dhalla IA, Bell C, et al. Derivation and Validation of an Index to Predict Early Death or Unplanned Readmission After Discharge from Hospital to the Community (LACE Index). *CMAJ*. 2010;182(5):551-557. https://doi.org/10.1503/cmaj.091117
2. Donze JD, Williams MV, Robinson EJ, et al. International Validity of the HOSPITAL Score to Predict 30-Day Potentially Avoidable Hospital Readmissions. *JAMA Intern Med*. 2016;176(4):496-502.
3. CMS Hospital Readmission Reduction Program (HRRP). 42 CFR 412.150-154; Affordable Care Act Section 3025. https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/AcuteInpatientPPS/Readmissions-Reduction-Program
4. Jack BW, Chetty VK, Anthony D, et al. A Reengineered Hospital Discharge Program to Decrease Rehospitalization (Project RED). *Ann Intern Med*. 2009;150(3):178-187.
5. Coleman EA, Parry C, Chalmers S, Min SJ. The Care Transitions Intervention: Results of a Randomized Controlled Trial. *Arch Intern Med*. 2006;166(17):1822-1828.
6. Naylor MD, Brooten DA, Campbell RL, et al. Transitional Care of Older Adults Hospitalized with Heart Failure. *J Am Geriatr Soc*. 2004;52(5):675-684.
