# Lakeside Health System — HIPAA Privacy and Security Guide

**Effective Date:** January 1, 2025  
**Privacy Officer & Compliance Department**  
**Regulatory Basis:** HIPAA Privacy Rule (45 CFR 164), HIPAA Security Rule, HITECH Act  
**Applicable:** All workforce members, all facilities (FAC001-FAC008), all systems

---

## 1. Overview

Lakeside Health System is a HIPAA Covered Entity. All protected health information (PHI) must be handled in compliance with federal and state (Michigan) privacy laws. This guide defines privacy standards across our facilities, data systems, and analytics platforms.

### 1.1 Scope of PHI at Lakeside
| Data Category | Examples | Systems |
|--------------|---------|---------|
| **Clinical data** | Diagnoses (I50.9, E11.9, etc.), lab results, imaging, medications | EHR, Lakehouse (lh_silver_ods) |
| **Demographic data** | Name, DOB, address, phone, SSN | EHR, Registration, dim_patient |
| **Financial data** | Insurance ID, payer info, claim amounts, charges | Billing, fact_claim, dim_payer |
| **SDOH data** | Zip code, income level, food access | dim_sdoh (aggregated — de-identified) |
| **Prescription data** | Medications, doses, pharmacy, adherence | Pharmacy, fact_prescription, dim_medication |

## 2. Minimum Necessary Standard

### 2.1 Access Levels by Role
| Role | Access Level | Data Available |
|------|-------------|---------------|
| Treating physician | Full patient chart | All clinical, demographic, financial |
| Nurse (bedside) | Active patient chart | Clinical data for assigned patients |
| Pharmacist | Medication-related | Medications, allergies, diagnoses (medication-relevant) |
| Billing/Coding | Financial + diagnosis | Claims, diagnosis codes, procedure codes, payer info |
| Quality/Analytics | Aggregate/de-identified preferred | Gold layer aggregations (agg_readmission_by_date, etc.) |
| Researcher | De-identified or IRB-approved | Dataset with 18 HIPAA identifiers removed |
| Data Agent (AI) | Semantic model (aggregated) | Star schema with no direct patient identifiers |
| Executive leadership | Dashboard/aggregate | KPIs, trends, no individual PHI |

### 2.2 Analytics Platform (Fabric) Privacy Controls
| Layer | PHI Level | Controls |
|-------|----------|---------|
| Bronze (lh_bronze_raw) | **Full PHI** | Restricted access, encryption at rest and in transit |
| Silver Stage (lh_silver_stage) | **Full PHI** | Row-level security, audit logging |
| Silver ODS (lh_silver_ods) | **Full PHI** | Row-level security, minimum necessary column access |
| Gold (lh_gold_curated) | **De-identified/aggregated** | Dimension tables use surrogate keys, no direct identifiers |
| Warehouse (wh_gold_analytics) | **De-identified/aggregated** | Star schema with surrogate keys |
| Data Agent | **No direct PHI** | Queries aggregated data only, no individual records |
| Semantic Model | **No direct PHI** | Measures and dimensions, not individual PHI |

### 2.3 De-identification Methods (Gold Layer)
| Identifier | De-identification Method |
|-----------|------------------------|
| Patient name | Removed — dimension key only (patient_key) |
| Date of birth | Year of birth retained, exact DOB removed at Gold |
| Address | Zip code only (first 3 digits if population < 20K) |
| Phone number | Removed at Gold layer |
| SSN | Never stored in analytics |
| MRN | Hashed or surrogate key in Gold |
| Insurance ID | Hashed or surrogate key in Gold |
| Provider name | Provider_key (surrogate) in dim_provider |

## 3. Patient Rights

### 3.1 HIPAA Patient Rights at Lakeside
| Right | Description | Process |
|-------|-----------|---------|
| Access | Patient may request copy of medical records | HIM department, 30-day response |
| Amendment | Patient may request correction of PHI | Written request, reviewed by provider |
| Accounting of disclosures | Patient may request list of who accessed PHI | Privacy office, 60-day response |
| Restriction | Patient may request limits on use/disclosure | Honored if agreed to by Lakeside |
| Confidential communications | Patient may request alternative communication | Accommodate reasonable requests |
| Breach notification | Patient must be notified of PHI breach | Within 60 days of discovery |

### 3.2 State-Specific Requirements (Michigan)
| Requirement | Michigan Law |
|------------|-------------|
| Mental health records | Extra protection under Michigan Mental Health Code |
| Substance abuse | 42 CFR Part 2 — separate consent required |
| HIV/AIDS | Specific disclosure rules under Michigan law |
| Genetic information | GINA protections apply |
| Minors | Emancipated minors have own rights |

## 4. Security Standards

### 4.1 Technical Safeguards
| Safeguard | Implementation at Lakeside |
|-----------|--------------------------|
| Access control | Role-based access (RBAC) across all systems |
| Audit logging | All PHI access logged and reviewable |
| Encryption (at rest) | AES-256 for databases, Azure encryption for Fabric |
| Encryption (in transit) | TLS 1.2+ for all data transmission |
| Unique user identification | Individual user accounts, no shared credentials |
| Automatic logoff | 15-minute inactivity timeout |
| Multi-factor authentication | Required for EHR, Fabric, remote access |
| Emergency access | Break-the-glass procedure with post-access audit |

### 4.2 Physical Safeguards
| Safeguard | Implementation |
|-----------|---------------|
| Workstation security | Screen locks, privacy screen filters in patient areas |
| Device management | Encrypted laptops, MDM for mobile devices |
| Server room access | Badge access, environmental monitoring |
| Paper records | Locked storage, supervised shredding |

### 4.3 Administrative Safeguards
| Safeguard | Implementation |
|-----------|---------------|
| Risk assessment | Annual security risk analysis |
| Training | Annual HIPAA training for all workforce (mandatory) |
| Sanctions | Progressive discipline for HIPAA violations |
| Incident response | 24-hour breach reporting to Privacy Officer |
| Business associate agreements | BAA required for all vendors handling PHI |
| Contingency plan | Disaster recovery for all PHI systems |

## 5. Breach Response Protocol

### 5.1 Breach Classification
| Category | Definition | Example | Notification Required |
|----------|-----------|---------|---------------------|
| Minor (< 500 individuals) | Unauthorized access/disclosure affecting < 500 people | Misdirected fax, email to wrong recipient | Individual notification + HHS annual log |
| Major (≥ 500 individuals) | Unauthorized access/disclosure affecting ≥ 500 people | Database breach, ransomware with data exposure | Individual + HHS + Media notification |
| Near-miss | Potential breach prevented | Phishing email clicked but no PHI accessed | Internal documentation, training reinforcement |

### 5.2 Response Timeline
| Step | Action | Timeline |
|------|--------|---------|
| Discovery | Identify potential breach | Immediate |
| Containment | Stop ongoing unauthorized access | Within 1 hour |
| Investigation | Determine scope, affected individuals | Within 7 days |
| Risk assessment | Evaluate harm probability | Within 14 days |
| Notification to Privacy Officer | Internal escalation | Within 24 hours of discovery |
| Individual notification | Written notice to affected patients | Within 60 days of discovery |
| HHS notification | Report to Office for Civil Rights | Within 60 days (≥ 500: immediate) |
| Media notification | If ≥ 500 individuals in a state | Within 60 days |
| Remediation | Corrective actions, policy updates | Ongoing |

### 5.3 Penalties for Non-Compliance
| Violation Level | Penalty Range | Example |
|----------------|-------------|---------|
| Unknowing | $100-$50,000 per violation | Employee access without authorization |
| Reasonable cause | $1,000-$50,000 per violation | Failure to provide patient records |
| Willful neglect (corrected) | $10,000-$50,000 per violation | Policy not followed, but corrected |
| Willful neglect (not corrected) | $50,000 per violation | Ongoing non-compliance |
| **Annual cap** | **$1.5M per violation type** | |

## 6. Business Associate Requirements

### 6.1 Entities Requiring BAAs at Lakeside
| Vendor Type | Examples | PHI Shared |
|------------|---------|-----------|
| Cloud platform | Microsoft Azure / Fabric | All lakehouse data |
| EHR vendor | Epic/Cerner | Clinical records |
| Clearinghouse | Claims submission intermediary | Claims data |
| Analytics vendor | BI tools, AI services | Aggregated/de-identified preferred |
| Pharmacy benefit manager | Prescription processing | Medication data |
| Home health agency | Post-discharge care | Clinical + demographic |
| Lab services | Reference laboratory | Lab orders and results |
| Transcription | Medical transcription services | Clinical dictation |

### 6.2 BAA Key Terms
- Vendor must implement equivalent security safeguards
- Vendor must report breaches within 24 hours
- PHI use limited to contracted services only
- Return or destroy PHI at contract termination
- Annual compliance attestation

## 7. AI and Analytics-Specific Privacy

### 7.1 Data Agent (Fabric AI) Privacy Controls
| Control | Implementation |
|---------|---------------|
| No direct PHI in responses | Agent queries semantic model (aggregated data) |
| Audit logging | All agent queries logged |
| Row-level security | Semantic model enforces role-based access |
| PII detection | Pre-response filter for inadvertent PHI |
| User authentication | Entra ID SSO required |

### 7.2 Knowledge Base (Foundry IQ) Privacy
| Control | Implementation |
|---------|---------------|
| Documents contain NO real PHI | All synthetic/policy documents |
| RAG grounding | Retrieves knowledge, not patient records |
| Access control | Foundry workspace RBAC |
| Output filtering | AI safety filters prevent PHI generation |

---

*Last Updated: 2025-01-15 | Next Review: 2025-07-15*  
*Document ID: COMP-HIPAA-001 | Version: 4.0*

---

## References & Sources

1. HIPAA Privacy Rule. 45 CFR Part 160 and Subparts A, E of Part 164. https://www.hhs.gov/hipaa/for-professionals/privacy/index.html
2. HIPAA Security Rule. 45 CFR Part 160 and Subparts A, C of Part 164. https://www.hhs.gov/hipaa/for-professionals/security/index.html
3. HITECH Act of 2009. Title XIII of the American Recovery and Reinvestment Act (ARRA). Public Law 111-5.
4. 42 CFR Part 2 — Confidentiality of Substance Use Disorder Patient Records. https://www.ecfr.gov/current/title-42/chapter-I/subchapter-A/part-2
5. Genetic Information Nondiscrimination Act (GINA). Public Law 110-233. https://www.eeoc.gov/genetic-information-discrimination
6. HHS Breach Notification Rule. 45 CFR §§ 164.400-414. https://www.hhs.gov/hipaa/for-professionals/breach-notification/index.html
7. NIST SP 800-66 Rev. 2. Implementing the HIPAA Security Rule: A Cybersecurity Resource Guide. https://csrc.nist.gov/publications/detail/sp/800-66/rev-2/final
