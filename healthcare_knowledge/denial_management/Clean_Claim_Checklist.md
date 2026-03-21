# Lakeside Health System — Clean Claim Submission Checklist

**Effective Date:** January 1, 2025  
**Revenue Cycle Department**  
**Purpose:** Ensure every claim meets "clean claim" standards before submission to minimize denials  
**Target:** 95% clean claim rate (claims accepted on first submission without rework)

---

## 1. What is a Clean Claim?

A clean claim is a properly completed claim that:
- Contains all required data elements
- Has correct patient, provider, and payer information
- Uses valid, specific CPT and ICD-10 codes
- Includes required prior authorization numbers
- Has no duplicate submission conflicts
- Is submitted within the payer's timely filing deadline

**Current clean claim rate:** ~82%  
**Target clean claim rate:** ≥ 95%  
**Revenue impact of each 1% improvement:** ~$180,000/year

## 2. Pre-Submission Checklist — All Claims

### 2.1 Patient Information
- [ ] Patient full legal name matches insurance card
- [ ] Date of birth verified (cross-reference with ID)
- [ ] Gender matches medical record (relevant for gender-specific diagnosis codes like C50.911)
- [ ] Current address on file
- [ ] Insurance member ID verified and active
- [ ] Group number current
- [ ] Coordination of benefits verified (primary vs secondary payer)

### 2.2 Insurance/Payer Verification
- [ ] **Real-time eligibility check completed** (date and time documented)
- [ ] Coverage active on date of service
- [ ] Correct payer selected from Lakeside payer list:
  - PAY001: Blue Cross Blue Shield of Michigan
  - PAY002: Aetna
  - PAY003: United Healthcare
  - PAY004: Cigna
  - PAY005: Humana
  - PAY006: Medicare Part A
  - PAY007: Medicare Part B
  - PAY008: Medicaid Michigan
  - PAY009: Priority Health
  - PAY010: Tricare
  - PAY011: Workers Compensation
  - PAY012: Self-Pay
- [ ] Payer-specific submission format confirmed (837P for Professional, 837I for Institutional)
- [ ] Network status verified (in-network for payer + facility combination)

### 2.3 Provider Information
- [ ] Rendering provider NPI is valid and active
- [ ] Provider is credentialed with the payer
- [ ] Provider taxonomy code matches service type
- [ ] Referring provider NPI included (if referral-based)
- [ ] Ordering provider NPI included (for labs, imaging)

### 2.4 Facility Information
- [ ] Correct facility selected (FAC001-FAC008)
- [ ] Facility NPI matches service location
- [ ] Place of service code correct:
  - 11 = Office (outpatient clinics — FAC005)
  - 21 = Inpatient Hospital (FAC001, FAC006, FAC008)
  - 22 = Outpatient Hospital
  - 23 = Emergency Room (FAC001, FAC006, FAC008)
  - 31 = Skilled Nursing Facility
  - 34 = Hospice
  - 61 = Comprehensive Inpatient Rehab (FAC007)
  - 02 = Telehealth (encounters marked as Telehealth type)

### 2.5 Diagnosis Codes (ICD-10)
- [ ] Primary diagnosis code is specific to highest level (no truncated codes)
- [ ] Primary diagnosis supports the procedure/service rendered
- [ ] All relevant secondary diagnoses included (comorbidity capture)
- [ ] Chronic condition codes included for ongoing management:
  - I10 (Hypertension)
  - E11.9 (Type 2 Diabetes)
  - I50.9 (Heart Failure)
  - J44.9 (COPD)
  - E78.5 (Hyperlipidemia)
  - N18.3 (CKD Stage 3)
  - F32.9 (Depression)
- [ ] Gender-specific codes match patient gender
- [ ] No assumption codes — documented in medical record

### 2.6 Procedure Codes (CPT)
- [ ] CPT code(s) accurately reflect service provided
- [ ] Modifiers applied correctly (see modifier guide below)
- [ ] Units of service correct
- [ ] CPT-to-ICD pairing validated (code makes clinical sense)
- [ ] Current-year CPT codes used (annual update applied)

**Common CPT codes at Lakeside:**
| CPT | Description | Common Pairing Issues |
|-----|-------------|---------------------|
| 99213-99215 | Office visits | Must match E&M documentation level |
| 99283-99285 | ED visits | Must match MDM complexity |
| 99221-99223 | Initial hospital care | Must match admission complexity |
| 71046 | Chest X-ray | Clinical indication required |
| 74177 | CT abdomen/pelvis | PA required by most payers |
| 93000 | ECG | Relevant cardiac diagnosis needed |
| 93306 | Echocardiogram | PA if >1/year (BCBS PAY001) |
| 85025 | CBC | Diagnosis supporting lab order |
| 80053 | CMP | Diagnosis supporting lab order |
| 27447 | Total knee replacement | PA required all commercial payers |
| 27130 | Total hip replacement | PA required all commercial payers |
| 33533 | CABG | PA required, specialist documentation |
| 43239 | Upper GI endoscopy w/biopsy | PA required by most payers |
| 45378 | Colonoscopy | PA for diagnostic (not screening) |

### 2.7 Prior Authorization
- [ ] **PA requirement checked** (reference PA Requirements Matrix)
- [ ] PA obtained and documented with:
  - Authorization number
  - Approved CPT code(s)
  - Approved date range
  - Approved units/visits
- [ ] PA number entered on claim form
- [ ] PA has not expired
- [ ] PA covers the specific CPT code on this claim

### 2.8 Charge Capture
- [ ] All services provided are captured (no missed charges)
- [ ] No unbundling (services that should be bundled are billed together)
- [ ] Charge amount matches the contracted rate schedule
- [ ] Date of service is accurate (matches medical record)

### 2.9 Timely Filing
- [ ] Claim submitted within payer's timely filing limit:

| Payer | Timely Filing Deadline |
|-------|----------------------|
| BCBS MI (PAY001) | 180 days |
| Aetna (PAY002) | 90 days |
| United Healthcare (PAY003) | 90 days |
| Cigna (PAY004) | 90 days |
| Humana (PAY005) | 365 days |
| Medicare (PAY006/007) | 365 days |
| Medicaid MI (PAY008) | 365 days |
| Priority Health (PAY009) | 180 days |
| Tricare (PAY010) | 365 days |
| Workers Comp (PAY011) | Varies by employer |

**CRITICAL:** Aetna, United Healthcare, and Cigna have **90-day** limits — prioritize these payers.

## 3. Encounter-Type Specific Checklists

### 3.1 Inpatient Admission Claims (Professional + Institutional)
- [ ] Admitting diagnosis documented
- [ ] Admission type coded correctly (Emergency, Elective, Urgent, Newborn, Trauma)
- [ ] Discharge disposition coded correctly (Home, SNF, Rehab, Home Health, Expired, AMA, Transfer)
- [ ] Length of stay matches admit/discharge dates
- [ ] H&P signed within 24 hours of admission
- [ ] Discharge summary signed
- [ ] All daily visit charges captured (99231-99233)
- [ ] Procedures during stay billed with correct dates
- [ ] If Medicare: 3-day qualifying stay for SNF transfer

### 3.2 Emergency Department Claims
- [ ] ED level matches MDM documentation (99281-99285)
- [ ] Triage time, physician evaluation time documented
- [ ] If admitted from ED: separate ED and inpatient claims
- [ ] All procedures (labs, imaging) billed with ED date of service
- [ ] If patient left AMA: document and code appropriately

### 3.3 Surgical/Procedural Claims
- [ ] Pre-operative diagnosis documented
- [ ] Operative report signed and complete
- [ ] Post-operative diagnosis documented (may differ from pre-op)
- [ ] Anesthesia charges separate (with start/stop times)
- [ ] Implant/hardware charges itemized (joint replacement)
- [ ] Pathology report linked (if biopsy 43239)
- [ ] Assistant surgeon modifier (-80, -82 as applicable)
- [ ] Bilateral modifier (-50) if applicable

### 3.4 Outpatient/Office Visit Claims
- [ ] E&M level matches documented complexity
- [ ] New vs established patient correctly coded (99201-99205 vs 99211-99215)
- [ ] Add-on services coded as such (not standalone)
- [ ] Referral on file (if required by payer)
- [ ] Telehealth modifier (95 or GT) if telehealth encounter

### 3.5 Pharmacy/Prescription Claims
- [ ] NDC code correct and current
- [ ] Quantity and days supply match
- [ ] Prescriber NPI included
- [ ] If specialty drug: PA number on pharmacy claim
- [ ] If 340B: correct pricing applied per facility eligibility

## 4. Modifier Quick Reference

| Modifier | Description | When to Use |
|----------|------------|-------------|
| 25 | Significant, separately identifiable E&M | Office visit + procedure same day |
| 26 | Professional component only | Provider interpretation without technical |
| 50 | Bilateral procedure | Same procedure both sides |
| 59 | Distinct procedural service | Multiple procedures, different sites |
| 76 | Repeat procedure, same physician | Same procedure repeated same day |
| 77 | Repeat procedure, different physician | Same procedure by different provider |
| 80/82 | Assistant surgeon | Surgical assist |
| 95 | Synchronous telemedicine | Real-time audio/video telehealth |
| RT/LT | Right/Left | Laterality specification |

## 5. Common Claim Rejection vs Denial

| Type | Definition | Action |
|------|-----------|--------|
| **Rejection** | Claim never entered payer system (format/data error) | Fix and resubmit immediately (doesn't start timely filing clock) |
| **Denial** | Payer processed and denied (clinical/coverage reason) | Appeal within deadlines per Appeal Process Guide |

### 5.1 Top Claim Rejections at Lakeside
| Rejection Reason | Fix |
|-----------------|-----|
| Invalid member ID | Reverify insurance card, re-enter |
| Invalid NPI | Check provider NPI registry |
| Invalid place of service | Match POS to facility type |
| Missing referring provider | Add referring NPI |
| Duplicate control number | Assign new claim number |

## 6. Quality Assurance

### 6.1 Pre-Billing Audit Triggers
Claims automatically held for audit review if:
- Total charges > $50,000
- LOS > 14 days
- Surgical procedure + age > 80
- Multiple surgical procedures same day
- Diagnosis code on payer watch list (e.g., sepsis A41.9)

### 6.2 Weekly Audit Metrics
| Metric | Target |
|--------|--------|
| Clean claim rate | ≥ 95% |
| Rejection rate | < 3% |
| Average days to claim submission | < 5 days from service |
| PA linkage rate | 100% for PA-required services |

---

*Last Updated: 2025-01-15 | Next Review: 2025-07-15*  
*Document ID: DM-CLEAN-004 | Version: 2.0*

---

## References & Sources

1. CMS-1500 Health Insurance Claim Form. National Uniform Claim Committee (NUCC). https://www.nucc.org/index.php/1500-claim-form-mainmenu
2. UB-04 (CMS-1450) Institutional Claim Form. National Uniform Billing Committee (NUBC). https://www.nubc.org/
3. ASC X12 837 Professional and Institutional Transaction Standards. https://x12.org/
4. CMS ICD-10-CM/PCS Official Guidelines for Coding and Reporting, FY 2024. https://www.cms.gov/medicare/coding-billing/icd-10-codes
5. AMA CPT Coding Guidelines. American Medical Association. https://www.ama-assn.org/practice-management/cpt
6. HIPAA Transaction and Code Sets Rule. 45 CFR Parts 160-162. https://www.cms.gov/Regulations-and-Guidance/Administrative-Simplification/TransactionCodeSetsStands
