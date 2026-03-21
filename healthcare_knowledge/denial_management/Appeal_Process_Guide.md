# Lakeside Health System — Claim Denial Appeal Process Guide

**Effective Date:** January 1, 2025  
**Revenue Cycle Department**  
**Purpose:** Comprehensive appeal procedures for all 7 denial reasons across all payers  
**Regulatory Basis:** Michigan Insurance Code, CMS Appeals Process, ERISA (employer-sponsored plans)

---

## 1. Overview

Lakeside Health System processes approximately **15,000 claims per month**. Current denial rate is **8-12%**, with appeal success rates varying by denial reason and appeal level. This guide follows CMS Medicare Claims Appeals Process (42 CFR Part 405, Subpart I), ERISA requirements (29 U.S.C. §§ 1001-1461), Michigan Insurance Code (Act 218 of 1956), and HFMA/MGMA denial management best practices.

### 1.1 Denial Rate by Reason (Current Year)
| Denial Reason | % of Total Denials | Revenue Impact | Appeal Success |
|--------------|-------------------|---------------|---------------|
| Prior Auth Required | 30% | $1.26M | 45% |
| Not Medically Necessary | 22% | $924K | 55% |
| Missing Documentation | 18% | $756K | 72% |
| Invalid Code | 12% | $504K | 85% |
| Coverage Expired | 8% | $336K | 25% |
| Out of Network | 6% | $252K | 40% |
| Duplicate Claim | 4% | $168K | 90% |
| **TOTAL** | **100%** | **$4.2M** | **Avg 55%** |

## 2. Appeal Process by Denial Reason

### 2.1 Prior Auth Required

**Root Cause:** Service performed without obtaining required prior authorization.

#### Level 1 — Internal Reconsideration (30 days)
| Action | Detail |
|--------|--------|
| Timeframe to file | Within 60 days of denial |
| Submit to | Payer reconsideration department |
| Include | (1) Retroactive PA request, (2) Clinical documentation supporting medical necessity, (3) Provider attestation for emergent cases |
| Success rate | 35-40% |

#### Level 2 — Formal Written Appeal (60 days)
| Action | Detail |
|--------|--------|
| Timeframe to file | Within 180 days of initial denial |
| Submit to | Payer appeals department (certified mail or portal) |
| Include | (1) All Level 1 documentation, (2) Peer-reviewed literature supporting treatment, (3) Specialist supporting letter, (4) Timeline showing emergent/urgent nature |
| Success rate | 40-50% |

#### Payer-Specific PA Appeal Notes
| Payer | Special Considerations |
|-------|----------------------|
| BCBS MI (PAY001) | Retro authorization available within 72 hours for emergencies |
| Aetna (PAY002) | Peer-to-peer available before formal appeal |
| United Healthcare (PAY003) | Online portal appeals accepted — fastest processing |
| Medicare (PAY006/007) | Reopening request → Redetermination → QIC → ALJ hierarchy |
| Medicaid MI (PAY008) | Fair hearing right — 120 days to file |

### 2.2 Not Medically Necessary

**Root Cause:** Payer determined the service was not clinically warranted for the diagnosis.

#### Appeal Strategy
| Component | Required |
|-----------|---------|
| Clinical narrative | Detailed physician letter explaining why service was essential |
| Lab/imaging results | All supporting diagnostic data (CMP 80053, CBC 85025, imaging 71046/74177/93306) |
| Clinical guidelines | Reference to applicable Lakeside or national guidelines (this knowledge base!) |
| Peer-reviewed literature | PubMed citations supporting treatment for specific ICD-10 diagnosis |
| Specialist opinion | If primary care denial, obtain specialist supporting letter |

#### Common "Not Medically Necessary" Scenarios and Responses
| Scenario | ICD-10 | Denial Argument | Counter-Argument |
|----------|--------|----------------|-----------------|
| Second echocardiogram within 12 months | I50.9 (CHF) | "Frequency exceeds guidelines" | "NYHA class worsened, EF change suspected, guideline allows for clinical change" |
| CT abdomen for abdominal pain | R10.9 | "Insufficient workup" | "Acute onset, labs concerning (elevated WBC/lipase), ultrasound inconclusive" |
| Inpatient admission for pneumonia | J18.9 | "Could be treated outpatient" | "Hypoxia (SpO2 <92%), elderly, multiple comorbidities (CHF I50.9, DM E11.9)" |
| Insulin Glargine | E11.9 | "Oral therapy not exhausted" | "Documented 6 months Metformin + Glipizide failure, HbA1c 9.2%" |
| Total knee replacement | M54.5 / Arthritis | "Conservative tx insufficient" | "12 months PT, NSAIDs, injections documented; functional impairment scoring" |

**Level 1 — Peer-to-Peer Review** (per CMS Medicare Managed Care Manual, Chapter 13)
- **Most effective approach** for medical necessity denials — per HFMA best practices, peer-to-peer yields 50-60% overturn rate (highest of any appeal type)
- Request peer-to-peer (physician-to-physician) call with payer medical director
- Have treating physician available with chart open during call
- Prepare: diagnosis, treatment history, failed alternatives, clinical guidelines from this knowledge base
- For Medicare claims: follow the CMS hierarchy — Reopening → Redetermination → QIC → ALJ (42 CFR 405.904-405.1140)
- **Success rate: 50-60%** (highest of any appeal type)

### 2.3 Missing Documentation

**Root Cause:** Claim submitted without required supporting documentation.

#### Prevention-First Approach
| Document Type | When Required | Automated Check |
|--------------|--------------|----------------|
| Operative report | All surgical CPT codes (27447, 27130, 33533, 43239, 45378) | Post-procedure documentation audit |
| Pathology report | Biopsy procedures (43239) | Lab integration |
| Prior authorization number | See PA matrix document | Claim scrubber rule |
| Referral documentation | Specialist visits (Cardiology, Oncology, etc.) | Referral tracking system |
| Medical records | Payer audit requests | HIPAA-compliant record release |

#### Appeal Process (Highest Success Rate)
1. Identify missing document from denial EOB (Explanation of Benefits)
2. Retrieve document from EHR/medical records
3. Resubmit claim with complete documentation within **30 days**
4. **Success rate: 72-85%** (simply need to provide what was missing)

#### Common Missing Documentation by Encounter Type
| Encounter Type | Commonly Missing | Solution |
|---------------|-----------------|---------|
| Inpatient (99221-99223) | Admission orders, H&P completion time | Ensure H&P within 24 hours |
| Surgery (27447, 27130, 33533) | Operative report, anesthesia record | Sign/finalize within 48 hours |
| ED (99283-99285) | Level of service documentation | MDM documentation template |
| Outpatient (99213-99215) | Plan of care, referral authorization | Pre-visit planning |

### 2.4 Invalid Code

**Root Cause:** Submitted CPT, ICD-10, or modifier code is incorrect, doesn't exist, or is inconsistent.

#### Common Invalid Code Scenarios
| Error Type | Example | Fix |
|-----------|---------|-----|
| CPT doesn't match diagnosis | Surgery CPT with medical diagnosis | Correct CPT or add surgical diagnosis |
| Truncated ICD-10 | I50 instead of I50.9 | Add required specificity |
| Gender/age mismatch | C50.911 (female breast) on male patient | Verify diagnosis accuracy |
| Modifier missing | 59 modifier needed for separate procedures | Add appropriate modifier |
| Outdated code | Using retired CPT/ICD-10 code | Update to current year code |

#### Appeal Process
1. Review denial for specific code flagged
2. Correct the code error
3. Resubmit corrected claim (corrected claim = frequency code 7)
4. If code was correct: Send letter of medical necessity with documentation
5. **Success rate: 85-90%** (most are simple resubmission)

### 2.5 Coverage Expired

**Root Cause:** Patient's insurance coverage was not active on date of service.

#### Appeal Options
| Scenario | Action |
|----------|--------|
| Patient has new coverage | Resubmit to new payer |
| Coverage lapse, now restored | Request retroactive eligibility from payer |
| COBRA eligible but not elected | Notify patient of COBRA option |
| Medicaid eligibility gap | Submit to Medicaid (PAY008) with retroactive eligibility request |
| No coverage available | Convert to Self-Pay (PAY012), apply charity care |
| Workers Comp denied | Verify with employer, submit to primary insurance |

#### Prevention
- **Eligibility verification at every encounter** — real-time check
- **Scheduling verification** — check 48 hours before elective procedures
- **Monthly eligibility batch** — verify all active patients quarterly

### 2.6 Out of Network

**Root Cause:** Service provided at facility or by provider not in patient's network.

#### Appeal Options
| Scenario | Approach | Success Rate |
|----------|----------|-------------|
| Emergency service | Federal No Surprises Act protects patient | 95% |
| No in-network option available | Document network inadequacy | 60% |
| Continuity of care | Transitional care exception request | 50% |
| Inadvertent OON (patient didn't know) | Balance billing protection, negotiate | 40% |

#### Lakeside Facility Network Status (Common Payers)
| Facility | BCBS (PAY001) | Aetna (PAY002) | UHC (PAY003) | Cigna (PAY004) | Medicaid (PAY008) |
|----------|-------------|-------------|-------------|-------------|-----------------|
| FAC001 — Main Hospital | In | In | In | In | In |
| FAC002 — Heart Center | In | In | In | Out | In |
| FAC003 — Urgent Care North | In | Out | In | In | In |
| FAC004 — Cancer Institute | In | In | In | In | In |
| FAC005 — Community Clinic | In | In | In | In | In |
| FAC006 — Children's Hospital | In | In | In | In | In |
| FAC007 — Rehab Center | In | Out | In | Out | In |
| FAC008 — South Campus (Toledo) | In | In | Out | In | Out (Ohio) |

### 2.7 Duplicate Claim

**Root Cause:** Same service submitted more than once for same patient on same date.

#### Resolution
1. **True duplicate:** Withdraw duplicate claim, keep original
2. **Not a duplicate:** Submit with modifier 59 (distinct procedure) or appropriate modifier
3. **Bilateral procedure:** Submit with modifier 50 or RT/LT
4. **Multiple encounters same day:** Append modifier 76 (repeat procedure) or 77 (repeat by another provider)
5. **Success rate: 90%** (usually simple resolution)

## 3. Appeal Timeline Requirements

| Payer | Level 1 Deadline | Level 2 Deadline | External Review |
|-------|-----------------|-----------------|----------------|
| BCBS MI (PAY001) | 180 days from denial | 60 days from L1 decision | Available |
| Aetna (PAY002) | 180 days | 60 days | Available |
| United Healthcare (PAY003) | 180 days | 60 days | Available |
| Cigna (PAY004) | 180 days | 60 days | Available |
| Humana (PAY005) | 180 days | 60 days | Available |
| Medicare (PAY006/007) | 120 days (Redetermination) | 180 days (QIC) → 60 days (ALJ) | CMS process |
| Medicaid MI (PAY008) | 120 days (Fair Hearing) | State administrative hearing | State process |
| Priority Health (PAY009) | 180 days | 60 days | Available |
| Tricare (PAY010) | 90 days | 60 days | Military appeals process |
| Workers Comp (PAY011) | Per state WC rules | WC commission hearing | State process |

## 4. Appeal Writing Template

```
[Date]
[Payer Name], Appeals Department
[Payer Address]

RE: Appeal for Claim Denial
Patient: [Name] | DOB: [Date] | Member ID: [ID]
Claim Number: [Number] | Date of Service: [Date]
Denial Reason: [Exact reason from EOB]
Treating Facility: [e.g., FAC001 — Lakeside Main Hospital]
Treating Provider: [Name, NPI, Specialty]

Dear Appeals Committee,

I am writing to appeal the denial of [procedure/service/medication] for the above-referenced 
patient. The denial reason states "[exact denial language]." I respectfully disagree with 
this determination for the following clinical reasons:

CLINICAL SUMMARY:
[Patient's diagnosis (ICD-10), relevant history, comorbidities]

MEDICAL NECESSITY:
[Why this specific service was required, what alternatives were considered/tried]

SUPPORTING EVIDENCE:
1. [Clinical guideline reference — link to relevant Lakeside protocol]
2. [Lab results, imaging findings]
3. [Specialist recommendation]
4. [Published literature — PubMed citation]

CONCLUSION:
Based on the clinical evidence provided, [service/procedure/medication] was medically 
necessary for this patient's [diagnosis]. I respectfully request reversal of this denial.

Sincerely,
[Physician name, credentials, NPI]
```

## 5. Escalation Matrix

| Situation | Escalate To | Timeframe |
|-----------|------------|-----------|
| Denial amount < $1,000 | Billing specialist | Routine (5 business days) |
| Denial amount $1,000-$10,000 | Revenue cycle supervisor | Priority (3 business days) |
| Denial amount > $10,000 | Revenue cycle director | Urgent (24 hours) |
| Systemic denial pattern (>10 same-reason denials/month) | VP Revenue Cycle + CMO | Executive review meeting |
| Medicare/Medicaid compliance concern | Compliance officer | Immediate |

---

*Last Updated: 2025-01-15 | Next Review: 2025-07-15*  
*Document ID: DM-APPEAL-002 | Version: 3.0*

---

## References & Sources

1. CMS Medicare Claims Appeals Process. 42 CFR Part 405, Subpart I. https://www.cms.gov/Medicare/Appeals-and-Grievances/MedPrescriptDrugApplGr662/Appeals
2. Employee Retirement Income Security Act (ERISA). 29 U.S.C. §§ 1001-1461. https://www.dol.gov/agencies/ebsa/laws-and-regulations/laws/erisa
3. Michigan Insurance Code. Act 218 of 1956. https://www.legislature.mi.gov/(S(qk1ykwp2glr4d34b01rpsj55))/mileg.aspx?page=getObject&objectName=mcl-Act-218-of-1956
4. CMS Medicare Managed Care Manual, Chapter 13 — Grievances, Organization Determinations, and Appeals. https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals/Downloads/mc86c13.pdf
5. MGMA. Denial Management Best Practices. Medical Group Management Association. https://www.mgma.com/
6. HFMA. Best Practices in Claims Denial Prevention and Management. Healthcare Financial Management Association. https://www.hfma.org/
