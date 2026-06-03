# Lakeside Health System — Chronic Care Management (CCM) and Principal Care Management (PCM) Program

**Program:** Medicare CCM / PCM
**Effective:** CY 2025
**Authority:** 42 CFR 410.26; CMS *Medicare Physician Fee Schedule Final Rule CY 2025* (CMS-1807-F)
**Applicable Facilities:** All Lakeside ambulatory clinics

---

## 1. Program Overview

Chronic Care Management (CCM) and Principal Care Management (PCM) are Medicare-covered, **non-face-to-face care coordination services** for patients with chronic conditions. These services were expanded under the *Bipartisan Budget Act of 2018* (PL 115-123, §50321) and refined annually through the Medicare Physician Fee Schedule.

CCM and PCM are foundational to Lakeside's value-based contracts and directly support our HRRP (see `Readmission_Penalty_Program.md`) and HEDIS adherence performance (see `HEDIS_Measures_Guide.md`).

## 2. CCM Eligibility (CPT 99490, 99439, 99437)

A patient is eligible for **Chronic Care Management** when ALL of the following apply:

1. **Two or more chronic conditions** expected to last at least 12 months or until death
2. The conditions place the patient at **significant risk of death, acute exacerbation/decompensation, or functional decline**
3. The patient (or representative) has provided **informed consent** to enroll
4. There is a **comprehensive, electronic care plan** accessible to the care team

Common qualifying chronic-condition pairs at Lakeside (joinable to `dim_diagnosis.icd_code` where `is_chronic = 1`):
- Heart failure (I50.9) + Hypertension (I10)
- Type 2 Diabetes (E11.9) + Hypertension (I10)
- COPD (J44.9) + Heart failure (I50.9)
- Major depressive disorder (F33.x) + any cardiovascular condition

## 3. CCM Billing Codes

| CPT | Description | Time | 2025 National Avg Allowable |
|-----|-------------|------|-----------------------------|
| **99490** | CCM, first 20 min/calendar month, clinical staff | ≥ 20 min | ~$62 |
| **99439** | CCM, each additional 20 min/calendar month, clinical staff | ≥ 20 min | ~$48 |
| **99491** | CCM, ≥ 30 min/calendar month, **provider personally** | ≥ 30 min | ~$83 |
| **99437** | CCM, each additional 30 min/calendar month, provider | ≥ 30 min | ~$58 |
| **G0506** | Add-on for comprehensive assessment/care planning at initiating visit | one-time | ~$64 |

Per CMS *Chronic Care Management Services* MLN Booklet (MLN909188):
- Time **must be documented** per calendar month
- Only **one practitioner** can bill CCM for a given patient per calendar month
- Patient cost-sharing applies (Medicare 20% coinsurance) — waiver not permitted
- Cannot be billed concurrently with TCM (CPT 99495/99496) for the same month

## 4. CCM Service Elements (Required Each Month)

1. 24/7 access to care team for urgent needs
2. Continuity of care with a designated practitioner
3. Comprehensive care management — assessment of medical, functional, psychosocial needs
4. Comprehensive care plan — documented, accessible, shared with patient
5. Management of care transitions — coordination with hospitals, SNFs, home health
6. Coordination with home- and community-based clinical service providers
7. Enhanced communication — secure messaging, electronic patient access
8. Medication reconciliation — links to MTM (see `clinical_guidelines/Medication_Therapy_Management_Protocol.md`)

## 5. Principal Care Management (PCM) — CPT 99424–99427

PCM is for patients with **a single high-risk chronic condition** (not two). Eligibility:

1. **One complex chronic condition** expected to last ≥ 3 months
2. Condition places patient at significant risk and is the **focus of care plan**
3. Condition either has led to a recent hospitalization or causes ongoing functional impairment

| CPT | Description | Time |
|-----|-------------|------|
| **99424** | PCM, first 30 min/month, provider personally | ≥ 30 min |
| **99425** | PCM, each additional 30 min/month, provider | ≥ 30 min |
| **99426** | PCM, first 30 min/month, clinical staff | ≥ 30 min |
| **99427** | PCM, each additional 30 min/month, clinical staff | ≥ 30 min |

PCM is appropriate when the patient has a single dominant condition (e.g., HFrEF, post-MI, decompensated COPD) and the care team needs reimbursable time to manage that one condition aggressively. PCM and CCM cannot be billed in the same month.

## 6. Lakeside Enrollment Workflow

| Step | Owner | System |
|------|-------|--------|
| 1. Identify candidates | Population health team | `agg_medication_adherence` non-adherent + ≥ 2 `is_chronic` diagnoses |
| 2. Outreach and consent | RN care coordinator | EHR consent form |
| 3. Initiating visit (G0506 if applicable) | Provider | EHR |
| 4. Build care plan in EHR | RN + Provider | EHR care plan module |
| 5. Monthly time tracking | Clinical staff | EHR time module |
| 6. Monthly billing | Revenue cycle | Claim submission |

## 7. Expected Impact

Based on CMS evaluations of CCM (Schurrer J et al., *Mathematica Policy Research, Final Report on the Evaluation of CCM Services*, 2017):
- ~**3.5% reduction** in hospitalizations for enrolled patients
- ~**2.5% reduction** in ED visits
- Net Medicare savings of ~$74 PMPM at scale

Lakeside CCM target: **80% of eligible patients enrolled**, with priority on patients flagged Non-Adherent and High readmission risk.

## 8. References

1. Centers for Medicare & Medicaid Services. *Chronic Care Management Services* (MLN Booklet MLN909188). CMS, 2024.
2. 42 CFR 410.26 — Services and supplies incident to a physician's professional services.
3. Centers for Medicare & Medicaid Services. *Medicare Physician Fee Schedule Final Rule CY 2025* (CMS-1807-F). November 2024.
4. Schurrer J, O'Malley A, Wilson C, et al. *Evaluation of the Diffusion and Impact of the Chronic Care Management (CCM) Services: Final Report*. Mathematica Policy Research. 2017.
5. Bipartisan Budget Act of 2018, Public Law 115-123, §50321.
