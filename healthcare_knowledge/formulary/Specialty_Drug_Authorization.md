# Lakeside Health System — Specialty Drug Prior Authorization Guide

**Effective Date:** January 1, 2025  
**Pharmacy & Therapeutics Committee Approval:** December 15, 2024  
**Purpose:** Navigator guide for specialty medications requiring prior authorization  
**Applicable:** All outpatient and specialty clinic prescriptions

---

## 1. Overview

Specialty drugs represent approximately **2% of prescriptions but 50% of pharmacy spend**. Proper prior authorization workflow is critical to avoid claim denials ("Prior Auth Required" being the #1 denial reason at Lakeside) and ensure patient access to timely treatment.

### 1.1 Impact on Denial Rates
- **Prior Auth Required** is the most common denial reason across all payers
- Specialty drugs without proper PA: **>60% denial rate**
- Specialty drugs with complete PA: **<8% denial rate**
- Average PA processing time: 5-15 business days (plan accordingly)

## 2. Insulin Prior Authorization

### Insulin Glargine 100 UNT/ML (RxNorm 1373463) — Tier 3/4

**Step Therapy Prerequisite:** Patient must have failed Step 1 (Metformin 860974) + Step 2 (Glipizide 311040) per DM-STEP-001 protocol.

#### 2.1 Required Documentation by Payer

| Payer | Required Documentation | Turnaround |
|-------|----------------------|-----------|
| **BCBS MI (PAY001)** | (1) Two HbA1c values >8% at least 3 months apart on dual oral therapy, (2) Metformin + Glipizide fill history ≥ 90 days each, (3) Diagnosis code E11.9 | 5 business days |
| **Aetna (PAY002)** | (1) Three HbA1c values showing progression, (2) Documentation of oral failure AND intolerance, (3) Endocrinology consult recommended | 7-10 business days |
| **United Healthcare (PAY003)** | (1) HbA1c >8% on max oral therapy × 3 months, (2) Prescriber attestation of medical necessity | 3-5 business days |
| **Cigna (PAY004)** | (1) Dual oral therapy failure × 90 days, (2) HbA1c >7.5% (lower threshold), (3) Patient education documentation | 5 business days |
| **Humana (PAY005)** | (1) HbA1c >8% on dual therapy, (2) Medication adherence verification (PDC ≥ 60%) | 5 business days |
| **Medicare Part D (PAY006/007)** | Coverage determination request, varies by Part D plan | 72 hours standard, 24 hours expedited |
| **Medicaid MI (PAY008)** | (1) Failed TWO oral agents × 90 days each, (2) HbA1c >8%, (3) Prescriber must be MD/DO (not NP/PA for initial) | 7-10 business days |
| **Priority Health (PAY009)** | (1) Dual oral failure, (2) Diabetes education completion, (3) Self-monitoring glucose log | 5 business days |

#### 2.2 Fast-Track Exceptions (bypass step therapy)
- HbA1c ≥ 10% at diagnosis → Submit with "medical emergency" flag
- DKA hospitalization → Submit inpatient records showing insulin initiation
- Pregnancy-related diabetes → Automatic approval at most payers
- Type 1 diabetes (misclassified) → Submit C-peptide or antibody results

#### 2.3 PA Submission Template — Insulin Glargine
```
PATIENT: [Name, DOB, Insurance ID]
DIAGNOSIS: E11.9 — Type 2 Diabetes Mellitus
PRESCRIBER: [Name, NPI]
FACILITY: [Lakeside facility, e.g., FAC001]

CLINICAL JUSTIFICATION:
1. Current HbA1c: [value] (Date: [date])
2. Prior HbA1c: [value] (Date: [date])
3. Metformin therapy history: [dose], [start date], [duration], [reason for failure/intolerance]
4. Glipizide therapy history: [dose], [start date], [duration], [reason for failure/intolerance]
5. Current complications: [list relevant: CKD N18.3, neuropathy, retinopathy]
6. Anticipated duration: Chronic/indefinite
7. Requested: Insulin Glargine 100 UNT/ML, [dose] units daily, 90-day supply
```

## 3. Specialty Inhaler Prior Authorization

### Combination Inhalers (LABA/ICS, LABA/LAMA, Triple Therapy)

**Step Therapy Prerequisite:** Patient must have documented use of:
- Albuterol 895994 (rescue) AND
- Fluticasone 896188 (for COPD with eosinophilia) or LAMA (for COPD without)

| Payer | Required for Combo Inhaler PA |
|-------|------------------------------|
| **BCBS MI (PAY001)** | Spirometry results, 90 days monotherapy trial, pulmonology note |
| **Aetna (PAY002)** | Brand inhaler PA mandatory, generic alternatives tried |
| **United Healthcare (PAY003)** | Step therapy bypass for GOLD 3-4 with specialist letter |
| **Medicaid MI (PAY008)** | Most restrictive — requires formulary exception + specialist |

## 4. Specialty Drug Monitoring Requirements

### 4.1 Post-Authorization Monitoring
Once specialty drugs are authorized, continued approval requires:

| Medication | Monitoring | Frequency | Required for Reauth |
|-----------|-----------|-----------|-------------------|
| Insulin Glargine (1373463) | HbA1c | Every 3 months | HbA1c improvement or < 8% maintenance |
| GLP-1 agonists (if approved) | HbA1c + weight | Every 3 months | ≥ 0.5% HbA1c improvement at 6 months |
| SGLT2 inhibitors (if approved) | HbA1c + eGFR | Every 3 months | Document kidney/cardiac benefit |
| Biologic inhalers | FEV1, exacerbation count | Every 6 months | Reduced exacerbation rate |

### 4.2 Reauthorization Timeline
| Payer | Initial Auth Period | Reauth Required |
|-------|-------------------|----------------|
| BCBS MI (PAY001) | 12 months | Submit updated labs 30 days before expiration |
| Aetna (PAY002) | 6 months initially, then 12 | More frequent initial monitoring |
| United Healthcare (PAY003) | 12 months | Simplified reauth if HbA1c improved |
| Medicaid MI (PAY008) | 6 months | Strict reauth with all documentation |

## 5. Denial and Appeal Process for Specialty Drugs

### 5.1 Common Denial Reasons and Solutions

| Denial Reason | Frequency | Root Cause | Solution |
|--------------|-----------|-----------|---------|
| Prior Auth Required | 40% | PA not submitted before claim | Implement PA check at prescribing |
| Not Medically Necessary | 25% | Insufficient clinical documentation | Include all labs, specialist notes |
| Missing Documentation | 20% | Incomplete PA submission | Use PA template above, checklist |
| Step Therapy Not Met | 10% | Oral agents not tried long enough | Document 90+ days of each step |
| Coverage Expired | 5% | Patient eligibility lapsed | Verify eligibility before submission |

### 5.2 Appeal Success Rates
| Level | Timeframe | Success Rate | Key Factor |
|-------|-----------|-------------|-----------|
| Peer-to-peer review | 24-48 hours | 45% | Specialist-to-specialist conversation |
| Written appeal (Level 1) | 30 days | 35% | Comprehensive clinical narrative |
| External review (Level 2) | 45-60 days | 55% | Independent medical review |

### 5.3 Cost Assistance for Denied Specialty Drugs
| Resource | For Whom | Coverage |
|----------|---------|---------|
| Manufacturer PAP (Patient Assistance) | Income-eligible, uninsured | Free or reduced-cost drug |
| 340B drug pricing | Eligible Lakeside facilities | Significant discount |
| Foundation grants | Disease-specific (diabetes, COPD) | Copay assistance |
| Self-Pay discount (PAY012) | Cash-pay patients | Lakeside negotiated pricing |

## 6. Prior Authorization Workflow — All Specialty Drugs

### 6.1 Standard PA Process
```
Prescriber Order → Pharmacy Flag (PA needed) → PA Coordinator Assembles Documentation →
Submit to Payer (electronically preferred) → Payer Review (5-15 business days) →
APPROVED: Fill prescription → DENIED: Appeal within 60 days
```

### 6.2 Urgent/Expedited PA Process
```
Prescriber marks URGENT → PA Coordinator submits within 24 hours →
Payer expedited review (24-72 hours) → If denied: Peer-to-peer within 24 hours
```

### 6.3 Triggers for Urgent PA
- Hospitalization with discharge pending on specialty drug
- Symptomatic hyperglycemia (glucose > 400) requiring insulin start
- COPD exacerbation requiring combination inhaler
- New cancer diagnosis (C50.911) requiring oncology drug
- Sepsis (A41.9) recovery requiring specialty antibiotic continuation

## 7. Specialty Drug Inventory

### 7.1 340B Eligible Facilities
| Facility | 340B Status | Impact |
|----------|------------|--------|
| FAC001 — Lakeside Main Hospital | Eligible | 25-50% drug cost reduction |
| FAC005 — Lakeside Community Clinic | Eligible | Serves low-income population |
| FAC006 — Lakeside Children's Hospital | Eligible | Pediatric specialty drugs |
| FAC002 — Lakeside Heart Center | Not eligible | Standard pricing |
| FAC003 — Lakeside Urgent Care North | Not eligible | Acute care, no specialty dispensing |

---

*Last Updated: 2025-01-15 | Next Review: 2025-04-01 (Quarterly)*  
*Guide ID: SPEC-PA-001 | Version: 2025.1*

---

## References & Sources

1. AMCP Format for Formulary Submissions, Version 4.1. Academy of Managed Care Pharmacy. https://www.amcp.org/resource-center/format-formulary-submissions
2. URAC Specialty Pharmacy Accreditation Standards. https://www.urac.org/accreditation-programs/specialty-pharmacy/
3. CMS Medicare Part B and Part D Specialty Drug Coverage Rules. https://www.cms.gov/Medicare/Prescription-Drug-Coverage/PrescriptionDrugCovGenIn
4. REMS (Risk Evaluation and Mitigation Strategies) Programs. FDA. https://www.fda.gov/drugs/drug-safety-and-availability/risk-evaluation-and-mitigation-strategies-rems
5. NCQA Health Plan Accreditation — Pharmacy Management Standards. https://www.ncqa.org/programs/health-plans/
