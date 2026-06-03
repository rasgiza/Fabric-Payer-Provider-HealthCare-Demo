# Lakeside Health System — Transitional Care Management (TCM) Program

**Program:** Medicare Transitional Care Management
**Effective:** CY 2025
**Authority:** 42 CFR 414.66; CMS *Transitional Care Management Services* MLN Booklet MLN908628
**Applicable Facilities:** All Lakeside ambulatory clinics receiving post-discharge patients

---

## 1. Program Overview

Transitional Care Management (TCM) reimburses ambulatory practices for the **30-day care coordination period following discharge** from an inpatient hospital, observation stay, partial hospitalization, SNF, or community mental health center. TCM was established under the *Calendar Year 2013 Medicare Physician Fee Schedule Final Rule* (77 FR 68892) and is one of the highest-leverage interventions for reducing 30-day readmissions — see `Readmission_Penalty_Program.md`.

## 2. Eligibility

A patient is eligible for TCM when:

1. They are **discharged from an inpatient setting** (acute hospital, IRF, LTACH, SNF, observation status ≥ 8 hours, or community mental health center)
2. The discharge requires **moderate or high-complexity medical decision making** during the 30-day post-discharge period
3. Care is provided to a **community-dwelling patient** (not still admitted)
4. The 30-day period begins on the **date of discharge** and continues for the next 29 days

## 3. Required TCM Service Elements

### 3.1 Interactive Contact (≤ 2 business days post-discharge)
- **Direct contact** with patient or caregiver — phone, secure messaging, or in person
- Must address: medications, follow-up appointments, signs/symptoms requiring re-contact
- Document attempt(s) in the EHR; two unsuccessful documented attempts within 2 business days satisfy the requirement
- Per Coleman EA et al., *J Am Geriatr Soc*. 2004;52(11):1817-1825 — early structured contact reduces 30-day readmission risk by ~30%

### 3.2 Face-to-Face Visit
| Complexity | CPT | Visit Window |
|-----------|-----|--------------|
| **Moderate** medical decision making | **99495** | Within **14 calendar days** of discharge |
| **High** medical decision making | **99496** | Within **7 calendar days** of discharge |

The face-to-face visit cannot be the same day as the discharge.

### 3.3 Non-Face-to-Face Services During the 30-Day Period
Performed by clinical staff under provider direction:
- Medication reconciliation and management — **must be completed by the date of the face-to-face visit** (per CMS MLN908628)
- Communication with home health, community providers, hospital staff
- Patient/family education on self-management and red flags
- Establishing or re-establishing referrals
- Identification of community/health resources
- Assistance with scheduling required follow-up

## 4. Billing

| CPT | Description | 2025 National Avg Allowable |
|-----|-------------|-----------------------------|
| **99495** | TCM, moderate complexity, F2F within 14 days | ~$209 |
| **99496** | TCM, high complexity, F2F within 7 days | ~$281 |

Key rules per MLN908628:
- One TCM service is billable per patient per 30-day period
- The same practitioner cannot bill TCM and CCM (CPT 99490) for the same calendar month
- Date of service for the TCM code is the date of the face-to-face visit, but the bill is submitted **at the end of the 30-day period**
- TCM does not have a separate place-of-service requirement — eligible regardless of where the post-discharge care occurs

## 5. Lakeside TCM Workflow

| Day | Activity | Owner |
|-----|---------|-------|
| **0** (discharge) | Discharge summary received; patient flagged in TCM worklist | Care coordinator |
| **1–2** | Interactive contact attempt(s); medication reconciliation begins | RN |
| **3–7** | Face-to-face visit if 99496 (high complexity, e.g., HF, sepsis, COPD-AE) | Provider |
| **3–14** | Face-to-face visit if 99495 (moderate complexity) | Provider |
| **8–30** | Non-face-to-face follow-up, referral coordination, MTM | RN + Pharmacist |
| **30** | TCM claim submitted | Revenue cycle |
| **31** | If still indicated, transition to **CCM** (`Chronic_Care_Management_Program.md`) | Care coordinator |

## 6. Priority Population at Lakeside

TCM is **mandatory** for all discharges in HRRP-targeted conditions (see `Readmission_Penalty_Program.md` §2):
- Acute MI (I21.x)
- Heart failure (I50.x)
- Pneumonia (J18.x)
- COPD exacerbation (J44.0, J44.1)
- Elective primary THA/TKA
- CABG

Additional high-priority triggers:
- `fact_encounter.readmission_risk_category = 'High'`
- Discharge to home self-care with ≥ 5 chronic medications
- Any new diagnosis requiring patient to begin a chronic medication during the index admission

## 7. Quality Measure Tie-In

| Measure | Owner | Lakeside Target |
|---------|-------|----------------|
| HRRP 30-day readmission (HF, COPD, AMI, PNA) | CMS | < 18% (HF), < 17% (COPD), < 14% (PNA) |
| HEDIS *Transitions of Care (TRC)* | NCQA | ≥ 75% completion of all four indicators |
| CMS Star *Plan All-Cause Readmissions (PCR)* | CMS | 4-star threshold |

The HEDIS TRC measure has four indicators — Notification of Inpatient Admission, Receipt of Discharge Information, Patient Engagement (≤ 30 days), Medication Reconciliation Post-Discharge — all of which Lakeside satisfies through the TCM workflow.

## 8. Evidence Base

- Coleman EA, Parry C, Chalmers S, Min S-J. *Arch Intern Med*. 2006;166(17):1822-1828 — the Care Transitions Intervention reduced 30-day rehospitalization by ~30%.
- Naylor MD et al., *J Am Geriatr Soc*. 2004;52(5):675-684 — APN-led transitional care for elderly HF patients reduced readmissions and total cost.
- Jencks SF, Williams MV, Coleman EA. *N Engl J Med*. 2009;360(14):1418-1428 — established the foundational data: 19.6% of Medicare beneficiaries rehospitalized within 30 days; half had no follow-up visit.

## 9. References

1. Centers for Medicare & Medicaid Services. *Transitional Care Management Services* (MLN Booklet MLN908628). CMS, 2024.
2. 42 CFR 414.66 — Incentive payments for services provided in physician scarcity areas (general PFS framework).
3. *Medicare Program; Revisions to Payment Policies under the Physician Fee Schedule, DME Face-to-Face Encounters... Calendar Year 2013*. 77 FR 68892.
4. Coleman EA, Parry C, Chalmers S, Min S-J. The Care Transitions Intervention: Results of a Randomized Controlled Trial. *Arch Intern Med*. 2006;166(17):1822-1828.
5. Jencks SF, Williams MV, Coleman EA. Rehospitalizations among Patients in the Medicare Fee-for-Service Program. *N Engl J Med*. 2009;360(14):1418-1428.
