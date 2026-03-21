# Lakeside Health System — Sepsis Recognition and Management Protocol

**ICD-10:** A41.9 — Sepsis, unspecified organism  
**Related Codes:** J18.9 (Pneumonia), N39.0 (UTI), K92.0 (GI Bleeding), N17.9 (Acute Kidney Failure)  
**Effective Date:** January 1, 2025  
**CMS Program:** SEP-1 (Severe Sepsis and Septic Shock: Management Bundle)  
**Approved By:** Chief Medical Officer, Emergency Medicine Chair, Critical Care Director  
**Applicable Facilities:** FAC001 (Lakeside Main Hospital), FAC006 (Lakeside Children's Hospital), FAC008 (Lakeside South Campus)

---

## 1. Overview

Sepsis remains a leading cause of in-hospital mortality and a significant driver of ICU utilization and extended length of stay. CMS SEP-1 bundle compliance directly impacts quality scores and mortality rates.

### 1.1 Financial Impact
- Average sepsis admission cost: **$32,000-$48,000**
- ICU transfer adds: **$15,000-$25,000**
- Every **1-hour delay** in antibiotic administration increases mortality by **7.6%**
- SEP-1 non-compliance impacts CMS quality reporting for Medicare (PAY006/PAY007)

## 2. Early Recognition — SIRS Criteria + qSOFA

### 2.1 SIRS Criteria (≥ 2 of the following + suspected infection = sepsis screening positive)
| Criteria | Threshold |
|----------|-----------|
| Temperature | > 38.3°C (100.9°F) or < 36°C (96.8°F) |
| Heart Rate | > 90 bpm |
| Respiratory Rate | > 20 breaths/min |
| WBC | > 12,000 or < 4,000 or > 10% bands |

### 2.2 qSOFA (Quick Sequential Organ Failure Assessment)
| Criteria | Points |
|----------|--------|
| Altered mental status (GCS < 15) | 1 |
| Systolic BP ≤ 100 mmHg | 1 |
| Respiratory rate ≥ 22 | 1 |

**qSOFA ≥ 2 = High mortality risk → Escalate immediately**

### 2.3 Common Infection Sources at Lakeside
| Source | ICD-10 | Typical Organisms | Frequency |
|--------|--------|-------------------|-----------|
| Pneumonia | J18.9 | S. pneumo, H. influenzae | 35% |
| Urinary | N39.0 | E. coli, Klebsiella | 25% |
| Abdominal | K92.0, K80.20 | Polymicrobial, E. coli | 15% |
| Skin/Soft tissue | Various | Staph aureus, Strep | 12% |
| Line-related | Various | Staph epidermidis | 8% |
| Unknown | A41.9 | Various | 5% |

## 3. The Sepsis Bundle — Hour-1 Protocol

### 3.1 MUST Complete Within 1 Hour of Recognition

| Action | Details | CPT/Order |
|--------|---------|-----------|
| **Blood Cultures** | 2 sets (4 bottles) before antibiotics | Microbiology |
| **Lactate Level** | Initial serum lactate | 83605 |
| **Broad-Spectrum Antibiotics** | Per source-specific protocol below | Pharmacy |
| **Fluid Resuscitation** | 30 mL/kg crystalloid if hypotensive or lactate ≥ 4 | IV fluids |
| **Vasopressors** | If MAP < 65 after fluids | Norepinephrine first-line |

### 3.2 Labs Within 1 Hour
- **Complete Blood Count (CPT 85025)** — WBC with differential
- **Comprehensive Metabolic Panel (CPT 80053)** — Creatinine (AKI detection), liver function
- **Lactate** — If initial ≥ 2 mmol/L, repeat in 2-4 hours
- **Blood cultures** — Before antibiotics (NEVER delay antibiotics to get cultures)
- **Urinalysis + culture** — If urinary source suspected
- **Chest X-ray (CPT 71046)** — If respiratory source suspected

### 3.3 Antibiotic Selection by Source
| Suspected Source | Empiric Regimen | Duration |
|-----------------|-----------------|----------|
| Pneumonia (J18.9) | Ceftriaxone + Azithromycin (197511) | 5-7 days |
| UTI (N39.0) | Ceftriaxone or Piperacillin-Tazobactam | 7-10 days |
| Abdominal | Piperacillin-Tazobactam or Meropenem | 5-7 days |
| Skin | Vancomycin + Piperacillin-Tazobactam | 7-14 days |
| Unknown source | Vancomycin + Piperacillin-Tazobactam | Narrow when cultures result |

**Note:** Azithromycin 250 MG (RxNorm 197511) from our formulary covers atypical pneumonia organisms.

## 4. Organ Dysfunction Monitoring

### 4.1 SOFA Score Components
| System | Score 0 | Score 1 | Score 2 | Score 3 | Score 4 |
|--------|---------|---------|---------|---------|---------|
| Respiratory (PaO2/FiO2) | ≥ 400 | < 400 | < 300 | < 200 | < 100 |
| Coagulation (Platelets) | ≥ 150 | < 150 | < 100 | < 50 | < 20 |
| Liver (Bilirubin) | < 1.2 | 1.2-1.9 | 2.0-5.9 | 6.0-11.9 | > 12 |
| Cardiovascular | MAP ≥ 70 | MAP < 70 | Low-dose vasopressor | Moderate vasopressor | High-dose vasopressor |
| CNS (GCS) | 15 | 13-14 | 10-12 | 6-9 | < 6 |
| Renal (Creatinine) | < 1.2 | 1.2-1.9 | 2.0-3.4 | 3.5-4.9 | > 5.0 |

**SOFA increase ≥ 2 from baseline = organ dysfunction = sepsis confirmed**

### 4.2 Acute Kidney Injury (N17.9) in Sepsis
- Monitor urine output hourly (target ≥ 0.5 mL/kg/hr)
- Track creatinine every 6-8 hours
- Hold or adjust renally-cleared medications (Metformin 860974, Lisinopril 314076)
- Consider nephrology consult if KDIGO Stage 2+
- **Do NOT hold fluids** for rising creatinine in early sepsis — under-resuscitation is worse

## 5. Escalation Criteria

### 5.1 ICU Transfer Criteria (from ED or floor)
| Criteria | Threshold |
|----------|-----------|
| Persistent hypotension after 30 mL/kg fluids | MAP < 65 |
| Vasopressor requirement | Any vasopressor |
| Respiratory failure | O2 requirement > 6L NC or BiPAP/intubation |
| Lactate | > 4 mmol/L or rising despite treatment |
| Altered mental status | New confusion, lethargy |
| Multi-organ dysfunction | SOFA ≥ 4 |

### 5.2 Rapid Response / Code Sepsis
- Any nurse or provider can activate "Code Sepsis"
- Response team: ICU physician, ICU nurse, pharmacist, respiratory therapy
- Target: Team at bedside within **15 minutes**

## 6. Special Populations

### 6.1 Elderly (Age ≥ 75)
- Atypical presentation common (confusion without fever)
- Lower threshold for imaging: CT abdomen/pelvis (CPT 74177) for abdominal source
- More aggressive monitoring — sepsis mortality > 40% in age 75+
- Be alert for UTI (N39.0) as common occult source

### 6.2 Diabetic Patients (E11.9)
- Higher infection risk, atypical presentations
- **Hold Metformin (860974)** during sepsis (lactic acidosis risk)
- **Hold Glipizide (311040)** during NPO periods
- **Insulin Glargine (1373463)** may need adjustment — may reduce or hold during acute illness
- Monitor glucose Q4-6 hours, target 140-180 mg/dL

### 6.3 Heart Failure Patients (I50.9)
- Careful fluid resuscitation — may need smaller boluses (10-15 mL/kg) with reassessment
- Early vasopressors if inadequate response to initial fluid
- **Hold Metoprolol (866924)** if hemodynamically unstable
- Monitor for fluid overload: lung auscultation, SpO2, JVD after each bolus

### 6.4 Immunocompromised / Cancer (C50.911)
- Broader empiric coverage needed
- Lower threshold for blood cultures and imaging
- Oncology consult within 4 hours if applicable

## 7. De-escalation and Recovery

### 7.1 Antibiotic Stewardship
- Review cultures at **48 hours** — narrow antibiotics to targeted therapy
- Daily assessment of antibiotic necessity
- Target shortest effective course (procalcitonin-guided when available)
- Document reason for continued broad-spectrum if cultures negative

### 7.2 Transition to Oral Antibiotics
- Criteria: Afebrile > 24 hours, tolerating oral, WBC normalizing
- **Amoxicillin 500 MG (308182)** — oral step-down for susceptible organisms
- **Azithromycin 250 MG (197511)** — oral step-down for atypical pneumonia

### 7.3 Discharge Criteria
- Hemodynamically stable off vasopressors ≥ 24 hours
- Oral antibiotics tolerated
- Lactate normalized
- Follow-up plan in place (7-day outpatient visit)
- Medication reconciliation complete — resume chronic medications appropriately

## 8. Quality Metrics and Reporting

| Metric | Target | CMS Measure |
|--------|--------|------------|
| Blood cultures before antibiotics | ≥ 95% | SEP-1 |
| Antibiotics within 1 hour | ≥ 90% | SEP-1 |
| Initial lactate drawn | ≥ 95% | SEP-1 |
| 30 mL/kg fluids if hypotensive | ≥ 85% | SEP-1 |
| Repeat lactate if initial ≥ 2 | ≥ 90% | SEP-1 |
| Sepsis mortality rate | < 20% | Internal |
| Average ICU length of stay | < 5 days | Internal |
| 30-day readmission (sepsis) | < 18% | Internal |

## 9. Facility-Specific Considerations

| Facility | Capabilities | Transfer Protocol |
|----------|-------------|-------------------|
| FAC001 — Lakeside Main Hospital (450 beds) | Full ICU, all capabilities | Receiving facility for transfers |
| FAC003 — Lakeside Urgent Care North | No inpatient, no ICU | **Must transfer** suspected sepsis to FAC001 or FAC008 |
| FAC005 — Lakeside Community Clinic | No inpatient, no ICU | **Must transfer** — start antibiotics before transport |
| FAC006 — Lakeside Children's Hospital (200 beds) | Pediatric ICU | Pediatric sepsis protocol (separate guideline) |
| FAC008 — Lakeside South Campus (350 beds) | Full ICU | Secondary receiving facility |

---

*Last Updated: 2025-01-15 | Next Review: 2025-07-15 (biannual for sepsis)*  
*Protocol ID: CG-SEP-004 | Version: 6.0*

---

## References & Sources

1. Evans L, Rhodes A, Alhazzani W, et al. Surviving Sepsis Campaign: International Guidelines for Management of Sepsis and Septic Shock 2021. *Intensive Care Med*. 2021;47(11):1181-1247. https://doi.org/10.1007/s00134-021-06506-y
2. Singer M, Deutschman CS, Seymour CW, et al. The Third International Consensus Definitions for Sepsis and Septic Shock (Sepsis-3). *JAMA*. 2016;315(8):801-810.
3. CMS SEP-1: Severe Sepsis and Septic Shock Management Bundle. CMS Inpatient Quality Reporting Program. https://qualitynet.cms.gov/inpatient/measures/sep
4. Seymour CW, Liu VX, Iwashyna TJ, et al. Assessment of Clinical Criteria for Sepsis: For the Third International Consensus Definitions (qSOFA). *JAMA*. 2016;315(8):762-774.
5. Levy MM, Evans LE, Rhodes A. The Surviving Sepsis Campaign Bundle: 2018 Update. *Intensive Care Med*. 2018;44(6):925-928.
