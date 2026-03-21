# Lakeside Health System — Clinical Documentation Standards

**Effective Date:** January 1, 2025  
**Clinical Documentation Improvement (CDI) Program**  
**Regulatory Basis:** CMS Documentation Guidelines, Joint Commission, AHIMA Standards  
**Applicable:** All clinicians, all encounter types, all facilities (FAC001-FAC008)

---

## 1. Overview

Clinical documentation drives **everything downstream**: coding accuracy, reimbursement, quality metrics, denial prevention, and AI analytics. Poor documentation is the root cause of **34% of all Lakeside claim denials** (Not Medically Necessary + Invalid Code).

### 1.1 Financial Impact of Documentation Quality
| Impact Area | Good Documentation | Poor Documentation |
|------------|-------------------|-------------------|
| Coding accuracy | > 95% | < 80% |
| Denial rate | < 5% | > 15% |
| Average DRG weight (inpatient) | Appropriate | Under-coded by 0.3-0.5 |
| Revenue per encounter | Maximized (appropriate code) | Under-reimbursed by 15-25% |
| Quality measure compliance | Gap closures documented | Gaps missed |
| Legal defensibility | Strong | Vulnerable |

## 2. Documentation Standards by Encounter Type

### 2.1 Outpatient Office Visits (CPT 99213-99215)

#### Required Elements for Each Visit Level
| Element | 99213 (Low) | 99214 (Moderate) | 99215 (High) |
|---------|-------------|------------------|--------------|
| Medical Decision Making | Straightforward or Low | Moderate | High |
| Problems addressed | 1-2 stable chronic | 2-3 chronic or 1 acute | 3+ acute/chronic with complexity |
| Data reviewed | Review prior results | Order/review labs/imaging | Complex test interpretation |
| Risk of complications | Low risk | Moderate risk (Rx management) | High risk (drug therapy escalation) |
| **Time-based alternative** | 20-29 min total | 30-39 min total | 40-54 min total |

#### Diagnosis-Specific Documentation Requirements
| Diagnosis | ICD-10 | Must Document |
|-----------|--------|--------------|
| Hypertension (I10) | I10 | Current BP reading, medication adherence, medication changes, target BP |
| Type 2 Diabetes (E11.9) | E11.9 | Latest HbA1c (value + date), medication regimen, complications screen, foot exam |
| Heart Failure (I50.9) | I50.9 | NYHA class, EF (value + date), weight, volume status, GDMT status |
| COPD (J44.9) | J44.9 | GOLD stage, spirometry date, current inhaler regimen, exacerbation count |
| Depression (F32.9) | F32.9 | PHQ-9 score, medication response, suicidal ideation screen |
| Hyperlipidemia (E78.5) | E78.5 | Latest lipid panel, LDL value, statin therapy status |
| CKD Stage 3 (N18.3) | N18.3 | Latest eGFR value + date, proteinuria status, medication adjustments |
| Asthma (J45.909) | J45.909 | Asthma control level, rescue inhaler use frequency, controller compliance |

### 2.2 Emergency Department (CPT 99281-99285)

#### Required Elements
| Element | All ED Visits |
|---------|--------------|
| Chief complaint | Patient's own words |
| History of present illness | Onset, location, duration, severity, quality, context, modifying factors |
| Pertinent review of systems | Relevant systems reviewed (~2-4 for 99283, full for 99285) |
| Physical examination | Focused or comprehensive based on presentation |
| Medical decision making | Document complexity, data reviewed, risk assessment |
| Differential diagnosis | At least 2-3 alternatives considered for complex presentations |
| Results interpretation | Personally reviewed labs (85025, 80053), imaging (71046, 74177), ECG (93000) |
| Disposition rationale | Why admit/observe/discharge — document clearly |

#### Admission vs Observation Decision Documentation
| Criteria | Document for ADMISSION | Document for OBSERVATION |
|----------|----------------------|------------------------|
| Expected LOS | ≥ 2 midnights | < 2 midnights |
| Inpatient criteria | InterQual/Milliman criteria met — document which | Doesn't fully meet inpatient criteria |
| Clinical justification | "Patient requires inpatient level care due to..." | "Patient requires observation for..." |
| **Critical for Medicare (PAY006):** | Admission order with documented criteria | Observation order, patient notice (MOON form) |

### 2.3 Inpatient (CPT 99221-99223)

#### Initial Inpatient Documentation
| Element | 99221 (Low) | 99222 (Moderate) | 99223 (High) |
|---------|-------------|------------------|--------------|
| MDM | Low or Moderate | Moderate | High |
| H&P completion | Within 24 hours of admission | Within 24 hours | Within 24 hours |
| Admitting diagnosis | ICD-10 specificity | ICD-10 with complications | Multi-system with complications |
| Plan of care | Documented orders and plan | Detailed multi-day plan | Complex multi-disciplinary plan |

#### Daily Progress Notes (99231-99233)
- Assessment of each active problem (by ICD-10)
- Response to treatment documented
- Plan changes explained and justified
- Any change in: medications, diet, activity, procedures
- Discussions with patient/family

#### Discharge Summary (MANDATORY)
| Element | Required |
|---------|---------|
| Principal diagnosis | Specific ICD-10 (e.g., I50.9, not just "heart failure") |
| Secondary diagnoses | All active conditions during stay |
| Procedures performed | All CPT codes with dates |
| Hospital course | Day-by-day summary of treatment |
| Discharge medications | Complete list with changes from admission |
| Follow-up plan | Specific appointments, dates, providers |
| Patient education | Topics covered, understanding verified |
| Discharge condition | Clinical status at discharge |
| **Timing** | **Must be completed within 48 hours of discharge** |

### 2.4 Surgical/Procedural Documentation

#### Operative Report (ALL Procedures)
| Element | Required Content |
|---------|----------------|
| Pre-operative diagnosis | Specific ICD-10 |
| Post-operative diagnosis | May differ from pre-op (e.g., pathology findings) |
| Procedure performed | Full CPT description |
| Surgeon and assistants | Names and roles |
| Anesthesia type | General, regional, local, MAC |
| Findings | Detailed intraoperative findings |
| Technique | Step-by-step procedure description |
| Specimens | Sent to pathology (if applicable) |
| Complications | Any intraoperative complications or "none" |
| Estimated blood loss | Documented |
| **Timing** | **Must be completed within 24 hours of procedure** |

#### Procedure-Specific Documentation
| Procedure | CPT | Additional Requirements |
|-----------|-----|----------------------|
| Total Knee Replacement | 27447 | Implant details, cemented/uncemented, laterality (RT/LT) |
| Total Hip Replacement | 27130 | Approach (anterior/posterior), implant details, laterality |
| CABG | 33533 | Number of grafts, conduit used, cardiopulmonary bypass time |
| Upper GI Endoscopy | 43239 | Scope type, biopsy locations, findings, photos |
| Colonoscopy | 45378 | Prep quality, cecal landmarks, polyp details, photo documentation |
| Echocardiogram | 93306 | EF measurement, wall motion, valve function, chamber sizes |

## 3. Medication Documentation Standards

### 3.1 Prescribing Documentation
Every medication order must include:
| Element | Example |
|---------|---------|
| Drug name | Lisinopril 10 MG Oral Tablet (RxNorm 314076) |
| Dose and frequency | 10 mg once daily |
| Route | Oral |
| Indication | Hypertension (I10), Heart Failure (I50.9) |
| Duration | Ongoing / 7 days / etc. |
| Allergies verified | "No known drug allergies" or specific allergies documented |
| Interactions checked | "Checked, no significant interactions" |

### 3.2 Medication Reconciliation Documentation
Required at: **Admission, Transfer, Discharge**

| Component | Document |
|-----------|---------|
| Home medications | Complete list with dose, frequency, compliance |
| Inpatient medications | All active orders |
| Changes during stay | New, stopped, dose changes — with rationale |
| Discharge medications | Complete list with changes highlighted |
| Patient education | Understanding of each change verified (teach-back) |
| Adherence assessment | For chronic meds: self-reported and pharmacy data (PDC) |

### 3.3 High-Alert Medication Documentation
| Medication | Additional Documentation Required |
|-----------|----------------------------------|
| Warfarin (836585) | INR value, target range, dose adjustment rationale |
| Insulin Glargine (1373463) | Blood glucose values, hypoglycemia assessment, dose rationale |
| Hydrocodone/APAP (856987) | Pain score, PDMP check documented, risk assessment, plan for taper |
| Lorazepam (835564) | Indication, duration plan, fall risk assessment, respiratory status |

## 4. Quality Measure Documentation

### 4.1 HEDIS Gap Closure Documentation
| Measure | What to Document | Where |
|---------|-----------------|-------|
| HbA1c Testing (CDC) | HbA1c value, date performed | Assessment note |
| HbA1c Control | Current HbA1c, intervention plan if > 7% | Assessment + Plan |
| BP Control (CBP) | BP value documented, meds reviewed | Vitals + Assessment |
| Statin Therapy (SPC) | Statin prescribed or reason not prescribed | Med list + Assessment |
| Eye Exam (CDC-EE) | Retinal exam completed or referral placed | Assessment + Referral |
| Colorectal Screening | Colonoscopy (45378) completed or ordered | Preventive section |
| Depression Screening | PHQ-9 score documented | Screening section |

### 4.2 CMS Condition-Specific Documentation
| Condition | Documentation Element | Impact |
|-----------|---------------------|--------|
| CHF (I50.9) | NYHA class + EF + weight | DRG weight, readmission tracking |
| COPD (J44.9) | GOLD stage + exacerbation count | Quality measures, treatment planning |
| Sepsis (A41.9) | SEP-1 bundle timing documented | CMS quality reporting |
| Diabetes (E11.9) | HbA1c + medication adherence | HEDIS, Stars rating |

## 5. CDI Query Process

### 5.1 When CDI Specialist Queries Physician
| Scenario | Query Type |
|----------|-----------|
| Unspecified diagnosis (e.g., I50 without .9) | Specificity query |
| Clinical indicators not linked to diagnosis | Clinical significance query |
| Documentation conflicts | Clarification query |
| Missing chronic conditions (affects DRG/HCC) | Completeness query |
| Acute condition severity not specified | Severity specification query |

### 5.2 Response Time
| Setting | Expected Response |
|---------|------------------|
| Inpatient (concurrent) | Within 24-48 hours while still admitted |
| Outpatient (retrospective) | Within 5 business days |
| Query escalation | If no response in timeframe → department chair notification |

## 6. Common Documentation Pitfalls

| Pitfall | Impact | Solution |
|---------|--------|---------|
| Copy-forward without updating | Stale data, wrong medications | Review and modify every element |
| "Patient doing well" without specifics | Insufficient for medical necessity | Document specific metrics, exam findings |
| Unspecified diagnosis codes | Lower DRG weight, quality gaps | Use highest specificity ICD-10 |
| Missing complications/comorbidities | Under-capture of HCC codes | Document all active conditions |
| No rationale for test/procedure | "Not Medically Necessary" denial | Document clinical why |
| Incomplete medication reconciliation | Safety risk + Missing Documentation denial | Full reconciliation at transitions |
| Unsigned notes | Missing Documentation denial | 48-hour signature policy |

---

*Last Updated: 2025-01-15 | Next Review: 2025-07-15*  
*Document ID: COMP-CDI-002 | Version: 3.0*

---

## References & Sources

1. CMS Documentation Guidelines for Evaluation and Management (E/M) Services. https://www.cms.gov/Outreach-and-Education/Medicare-Learning-Network-MLN/MLNEdWebGuide/EMDOC
2. CMS ICD-10-CM Official Guidelines for Coding and Reporting, FY 2024. https://www.cms.gov/medicare/coding-billing/icd-10-codes/2024-icd-10-cm
3. AHIMA. Clinical Documentation Improvement (CDI) Practice Brief. *Journal of AHIMA*. https://ahima.org/
4. The Joint Commission. Record of Care, Treatment, and Services Standards (RC). https://www.jointcommission.org/standards/
5. CMS-HCC Risk Adjustment Model. https://www.cms.gov/Medicare/Health-Plans/MedicareAdvtgSpecRateStats/Risk-Adjustors
6. AMA CPT Documentation Guidelines. American Medical Association. https://www.ama-assn.org/practice-management/cpt
