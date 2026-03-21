# Lakeside Health System — Step Therapy Protocols

**Effective Date:** January 1, 2025  
**Pharmacy & Therapeutics Committee Approval:** December 15, 2024  
**Purpose:** Ensure cost-effective prescribing while maintaining clinical quality  
**Applicable:** All outpatient prescriptions across all Lakeside facilities

---

## 1. Overview

Step therapy requires patients to try preferred, evidence-based medications before more costly alternatives are authorized. This protocol aligns with payer requirements and clinical evidence to minimize prior authorization denials.

**Key Principle:** Step therapy is about clinical sequencing, not denial of care. Each step has clear failure criteria triggering automatic progression.

## 2. Diabetes Step Therapy Protocol

### Protocol: DM-STEP-001

```
STEP 1 → STEP 2 → STEP 3 → STEP 4
```

| Step | Medication | Criteria to Advance | Timeframe |
|------|-----------|-------------------|-----------|
| **Step 1** | Metformin 500 MG (RxNorm 860974) | HbA1c remains > 7% at max tolerated dose (up to 2000 mg/day) | 3 months |
| **Step 2a** | Add SGLT2 Inhibitor or GLP-1 RA | **Preferred** if patient has HF (I50.9), CKD (eGFR < 60), ASCVD (I25.10), or obesity (BMI >= 30). Per ADA 2024+ Standards of Care. | 3 months |
| **Step 2b** | Add Glipizide 5 MG (RxNorm 311040) | Alternative for cost-sensitive patients WITHOUT HF, CKD, or ASCVD | 3 months |
| **Step 3** | Add/switch Insulin Glargine (RxNorm 1373463) | HbA1c remains > 8% on dual therapy, or symptomatic hyperglycemia | 3 months |
| **Step 4** | Combination or intensification (GLP-1 + SGLT2 + Insulin) | HbA1c remains > 8% on triple therapy | Specialist referral |

### Step 1 → Step 2 Failure Criteria
- HbA1c ≥ 7.0% after 3 months at maximum tolerated Metformin dose
- Documented intolerance (GI side effects after 4-week titration)
- Contraindication: eGFR < 30, active liver disease
- **Documentation required:** Two HbA1c values ≥ 7.0% at least 3 months apart on Metformin

### Step 2 → Step 3 Failure Criteria
- HbA1c ≥ 8.0% after 3 months on Metformin + Glipizide
- Recurrent hypoglycemia on Glipizide (documented)
- HbA1c ≥ 9.0% at any time (fast-track to insulin)
- **Documentation required:** Claim history showing ≥ 90 days of dual oral therapy + HbA1c result

### Fast-Track Exceptions (bypass step therapy)
| Scenario | Go Directly To |
|----------|---------------|
| HbA1c ≥ 10% at diagnosis | Insulin Glargine (Step 3) |
| Type 1 diabetes | Insulin (not subject to T2DM step therapy) |
| Pregnancy with diabetes | Insulin (oral agents contraindicated) |
| eGFR < 30 | Skip Metformin → Glipizide or Insulin |
| Heart failure (I50.9) | SGLT2 at Step 2a — no specialist letter needed per ADA 2024+ |
| CKD (N18.3) with eGFR >= 20 | SGLT2 at Step 2a — no specialist letter needed per ADA 2024+ |

### Payer-Specific Step Therapy Requirements

| Payer | Steps Required | Notes |
|-------|---------------|-------|
| Blue Cross Blue Shield (PAY001) | Steps 1-2 before insulin (Tier 3) | Insulin Glargine on their preferred insulin list |
| Aetna (PAY002) | Strict Steps 1-3 before GLP-1/SGLT2 | Most restrictive step therapy |
| United Healthcare (PAY003) | Steps 1-2 | More lenient on insulin timing |
| Cigna (PAY004) | Steps 1-2, then insulin | 90-day supply incentive at each step |
| Medicaid Michigan (PAY008) | Steps 1-3, strict documentation | Must fail 2 oral agents before insulin |
| Medicare Part D (PAY006/007) | Varies by plan | CMS protected class — less restrictive |

## 3. Hypertension Step Therapy Protocol

### Protocol: HTN-STEP-001

| Step | Medication | Criteria to Advance | Timeframe |
|------|-----------|-------------------|-----------|
| **Step 1** | Lisinopril 10 MG (RxNorm 314076) | BP remains ≥ 130/80 at max dose (40 mg) | 4 weeks |
| **Step 2** | Add Amlodipine 5 MG (RxNorm 197361) | BP remains ≥ 130/80 on dual therapy | 4 weeks |
| **Step 3** | Add Metoprolol 50 MG (RxNorm 866924) OR Losartan 50 MG (RxNorm 310798) | BP remains ≥ 130/80 on triple therapy | 4 weeks |
| **Step 4** | Add Furosemide 40 MG (RxNorm 310429) or specialist referral | Resistant hypertension | Specialist |

### Special Populations
| Population | First-Line Modification |
|-----------|----------------------|
| Diabetic (E11.9) | ACE/ARB mandatory first step (renoprotection) |
| Heart Failure (I50.9) | Lisinopril + Metoprolol concurrent start |
| CKD (N18.3) | ACE/ARB mandatory; Amlodipine preferred add-on |
| ACE-intolerant (cough/angioedema) | Start with Losartan (310798) instead of Lisinopril |
| Pregnancy | All agents require OB review; Lisinopril/Losartan contraindicated |

## 4. Pain Management Step Therapy Protocol

### Protocol: PAIN-STEP-001

| Step | Medication | Criteria to Advance | Timeframe |
|------|-----------|-------------------|-----------|
| **Step 1** | Acetaminophen 500 MG (RxNorm 313782) | Inadequate pain control at max dose (3000 mg/day) | 1-2 weeks |
| **Step 2** | Add/switch Ibuprofen 200 MG (RxNorm 310965) | Inadequate control; no GI/renal/cardiac contraindication | 1-2 weeks |
| **Step 3** | Hydrocodone/APAP 5-325 MG (RxNorm 856987) | Non-opioid therapy failed, acute pain only | 3 days max |
| **Step 4** | Pain management referral | Chronic pain or extended opioid need | Specialist |

### Opioid Prescribing Guardrails
- **Maximum initial opioid prescription:** 3-day supply
- **Maximum without pain consult:** 7-day supply
- **PDMP check mandatory** before each opioid prescription
- **Naloxone co-prescribe** for all patients receiving > 50 MME/day
- **Controlled substance agreement** required for ≥ 30-day opioid therapy
- Michigan MAPS (Automated Prescription System) query documented in chart

### Populations Requiring Modified Pain Pathway
| Population | Modification |
|-----------|-------------|
| COPD (J44.9) | **AVOID** opioids — respiratory depression risk. Max Step 2. |
| Elderly (age > 65) | **AVOID** Ibuprofen long-term (GI/renal). Prefer Acetaminophen. |
| CKD (N18.3) | **AVOID** NSAIDs. Acetaminophen only. |
| CHF (I50.9) | **AVOID** NSAIDs (fluid retention). Acetaminophen preferred. |
| Post-surgical (CPT 27447, 27130, 33533) | Multimodal analgesia pathway, wean to oral within 5-7 days |

## 5. Mental Health Step Therapy Protocol

### Protocol: MH-STEP-001 (Depression — F32.9)

| Step | Medication | Criteria to Advance | Timeframe |
|------|-----------|-------------------|-----------|
| **Step 1** | Sertraline 50 MG (RxNorm 312938) | Inadequate response at therapeutic dose | 6-8 weeks |
| **Step 2** | Switch to Escitalopram 10 MG (RxNorm 312036) | Inadequate response or intolerable side effects | 6-8 weeks |
| **Step 3** | Augmentation or alternative class | Failed 2 SSRIs | Psychiatry referral |

### Sertraline vs Escitalopram Selection
| Patient Profile | Preferred Agent | Rationale |
|----------------|----------------|-----------|
| Cardiac disease (I50.9, I25.10) | Sertraline (312938) | Most cardiac safety data |
| GI symptoms/IBS | Sertraline (312938) | May improve GI motility |
| Sedation desired | Escitalopram (312036) | Slightly more sedating |
| Drug interactions concern | Escitalopram (312036) | Fewer CYP interactions |

### Protocol: MH-STEP-002 (Anxiety — Benzodiazepine Access)

| Scenario | Lorazepam (835564) Approval |
|----------|---------------------------|
| Acute anxiety/panic, first episode | 7-day supply, one-time |
| Procedural anxiety | Single dose per procedure |
| Ongoing anxiety > 14 days | **Requires psychiatry consult** |
| COPD (J44.9) patient | **DENIED** — respiratory depression risk |
| Age > 65 | **DENIED** without geriatrics approval — Beers criteria |

## 6. Respiratory Step Therapy Protocol

### Protocol: RESP-STEP-001 (COPD — J44.9)

| Step | Medication | Criteria to Advance | Timeframe |
|------|-----------|-------------------|-----------|
| **Step 1** | Albuterol MDI (RxNorm 895994) PRN | Using rescue > 2x/week | 4 weeks |
| **Step 2** | Add LAMA (tiotropium) | Persistent symptoms despite LAMA | 4-8 weeks |
| **Step 3** | Add Fluticasone (RxNorm 896188) ICS | Per GOLD D criteria, eos ≥ 300 | 4-8 weeks |
| **Step 4** | Triple therapy (LABA/LAMA/ICS) | Multiple exacerbations despite Step 3 | Pulmonology |

### Protocol: RESP-STEP-002 (Asthma — J45.909)

| Step | Medication | Criteria to Advance |
|------|-----------|-------------------|
| **Step 1** | Albuterol MDI (895994) PRN only | Using > 2x/week or nighttime symptoms > 2x/month |
| **Step 2** | Add Fluticasone (896188) low-dose daily | Uncontrolled on low-dose ICS |
| **Step 3** | Increase Fluticasone + add LABA | Uncontrolled on medium-dose ICS/LABA |
| **Step 4** | High-dose ICS/LABA + specialist referral | Complex asthma |

## 7. Prior Authorization Impact

### 7.1 Common Denials from Step Therapy Non-Compliance

| Denial Reason | Root Cause | Prevention |
|--------------|-----------|-----------|
| **Prior Auth Required** | Prescribed Step 3 drug without documenting Step 1-2 failure | Follow step therapy protocol, document failures |
| **Not Medically Necessary** | No clinical justification for skipping steps | Include HbA1c, BP readings, pain scores in auth request |
| **Missing Documentation** | Step therapy history not submitted with auth | Submit complete medication history from EHR |

### 7.2 How Step Therapy Reduces Denials
- Claims with proper step therapy documentation: **< 5% denial rate**
- Claims without step therapy documentation: **35-45% denial rate**
- Following protocols saves providers **2-3 hours/week** in prior auth work

## 8. Override and Exception Process

### 8.1 When to Request Override
- Clinical contraindication to preferred agent
- Documented allergy (verified in allergy list, not just "intolerance")
- Significant drug-drug interaction
- Patient stabilized on non-formulary agent prior to enrollment
- Specialist recommendation with supporting literature

### 8.2 Override Request Workflow
1. Prescriber completes Step Therapy Override Form (available in EHR)
2. Include: diagnosis code, failed medications with dates/doses, clinical rationale
3. Submit to: Pharmacy & Therapeutics Committee (routine) or Medical Director (urgent)
4. Response time: Routine 5 business days, Urgent 24 hours
5. If approved: prior auth auto-submitted to payer with override documentation

---

*Last Updated: 2025-01-15 | Next Review: 2025-04-01 (Quarterly)*  
*Protocol ID: STEP-2025-Q1 | Version: 2025.1*

---

## References & Sources

1. American Diabetes Association (ADA). Standards of Care in Diabetes — 2024: Pharmacologic Approaches to Glycemic Treatment. *Diabetes Care*. 2024;47(Suppl 1):S158-S178.
2. FDA Therapeutic Equivalence Evaluations (Orange Book). https://www.fda.gov/drugs/drug-approvals-and-databases/approved-drug-products-therapeutic-equivalence-evaluations-orange-book
3. American Geriatrics Society (AGS). 2023 Updated AGS Beers Criteria for Potentially Inappropriate Medication Use in Older Adults. *J Am Geriatr Soc*. 2023;71(7):2052-2081.
4. CMS Medicare Prescription Drug Benefit Manual, Chapter 6 — Part D Drugs and Formulary Requirements. https://www.cms.gov/Medicare/Prescription-Drug-Coverage/PrescriptionDrugCovContra/PartDManuals
5. ACC/AHA/HFSA Heart Failure Guideline (2022) — SGLT2 Inhibitor Recommendations. *Circulation*. 2022;145(18):e895-e1032.
6. KDIGO 2024 Clinical Practice Guideline for Chronic Kidney Disease. https://kdigo.org/guidelines/ckd-evaluation-and-management/
