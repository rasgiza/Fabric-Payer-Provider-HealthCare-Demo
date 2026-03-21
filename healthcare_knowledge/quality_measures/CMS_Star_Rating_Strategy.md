# Lakeside Health System — CMS Star Rating Methodology and Strategy

**Applicable Plans:** Medicare Advantage (PAY006/PAY007)  
**Rating Year:** 2025 (based on MY 2023-2024 data)  
**CMS Program:** Medicare Advantage Quality Rating System  
**Strategic Target:** Achieve and maintain **4+ Stars** for bonus payments

---

## 1. Overview

The CMS Star Rating system rates Medicare Advantage plans on a 1-5 star scale across ~45 measures in 5 domains. **4+ stars unlocks ~5% quality bonus payments**, worth an estimated **$2.5M-$5M annually** for Lakeside's Medicare population.

### 1.1 Star Rating Domain Weights
| Domain | Weight | Key Measures | Lakeside Focus |
|--------|--------|-------------|---------------|
| Staying Healthy (Preventive) | 15% | Screenings, immunizations | Moderate |
| Managing Chronic Conditions | 30% | Diabetes, HTN, Heart Failure care | **HIGH** |
| Member Experience (CAHPS) | 20% | Patient satisfaction surveys | Moderate |
| Member Complaints | 10% | Appeals, grievances, CTM data | Low |
| **Medication Adherence** | **25%** | **3 triple-weighted measures** | **HIGHEST** |

### 1.2 Triple-Weighted Measures (3x Impact)
These three measures have the **single largest impact** on Star Ratings:

| Measure | Drug Class | 5-Star Threshold | 4-Star Threshold |
|---------|-----------|-----------------|-----------------|
| **Diabetes Medication Adherence** | Metformin (860974), Glipizide (311040), Insulin Glargine (1373463) | PDC ≥ 83% | PDC ≥ 80% |
| **RAS Antagonist Adherence** | Lisinopril (314076), Losartan (310798) | PDC ≥ 84% | PDC ≥ 81% |
| **Statin Adherence** | Atorvastatin (200031) | PDC ≥ 84% | PDC ≥ 81% |

**Translation:** If 80%+ of Medicare patients maintain PDC ≥ 80% on these drug classes, we achieve 4+ stars on the highest-impact measures.

## 2. Star Rating Calculation

### 2.1 Measure → Star → Domain → Overall
```
Individual Measure Score → Compare to CMS cut points → Assign 1-5 stars per measure →
Weight measures within domain → Domain star → Weight domains → Overall Star Rating
```

### 2.2 CMS Cut Points (Approximate — Varies Annually)
| Stars | Performance Percentile | Quality Level |
|-------|----------------------|--------------|
| 5 Stars | ≥ 90th percentile | Excellent |
| 4 Stars | 65th-89th percentile | Above Average |
| 3 Stars | 35th-64th percentile | Average |
| 2 Stars | 10th-34th percentile | Below Average |
| 1 Star | < 10th percentile | Poor |

### 2.3 Reward Improvement Factor (RIF)
CMS rewards **improvement** even if absolute performance is below threshold:
- Plans improving ≥ 1 standard deviation on a measure get credit
- Particularly valuable for measures where Lakeside is currently underperforming
- Focus QI efforts on measures closest to next threshold

## 3. Managing Chronic Conditions Domain (30% Weight)

### 3.1 Diabetes Care (CDC Measures)
| Star Measure | What We Track | Data Source |
|-------------|--------------|-------------|
| HbA1c Testing | Annual HbA1c for all E11.9 patients | fact_encounter + labs |
| HbA1c Poor Control (>9%) | % with HbA1c >9% (LOWER is better) | Lab results |
| Blood Pressure Control | % of diabetics with BP <140/90 | Encounter vitals |
| Eye Exam | Annual retinal exam completion | Referral/claims |

### 3.2 Cardiovascular Care
| Star Measure | What We Track | Target |
|-------------|--------------|--------|
| Controlling Blood Pressure (CBP) | % of I10 patients with BP <140/90 | ≥ 65% |
| Statin Therapy (ASCVD) | % of I25.10 patients on statin | ≥ 85% |

### 3.3 Heart Failure
| Star Measure | What We Track | Notes |
|-------------|--------------|-------|
| Readmission rate (I50.9) | 30-day readmission | agg_readmission_by_date |
| Beta-blocker after MI | Metoprolol (866924) persistence | fact_prescription |

### 3.4 COPD/Respiratory
| Star Measure | What We Track |
|-------------|--------------|
| Pharmacotherapy after COPD exacerbation | Steroid + bronchodilator after J44.1 |
| Spirometry for diagnosis | Spirometry within 24 months of J44.9 |

## 4. Medication Adherence Domain (25% Weight)

### 4.1 PDC Calculation Methodology
```
PDC = (Number of days covered by medication fills in measurement period) / 
      (Number of days in measurement period from first fill to end of period)

PDC ≥ 80% = Adherent
PDC < 80% = Non-Adherent
```

### 4.2 Adherence Performance Tracking
| Class | Medications at Lakeside | Target PDC | Tracking |
|-------|----------------------|-----------|---------|
| Diabetes | Metformin (860974), Glipizide (311040), Insulin Glargine (1373463) | ≥ 80% | fact_prescription |
| RAS Antagonists | Lisinopril (314076), Losartan (310798) | ≥ 80% | fact_prescription |
| Statins | Atorvastatin (200031) | ≥ 80% | fact_prescription |

### 4.3 Improvement Strategies by Star Level Needed
| Current Performance | Actions | Expected Impact |
|-------------------|---------|----------------|
| < 3 Stars (PDC < 75%) | 90-day supply default, cost barrier removal, auto-refill | +8-12% PDC |
| 3 Stars (PDC 75-80%) | Pharmacist outreach day 30/60/90, med sync | +5-8% PDC |
| 4 Stars (PDC 80-83%) | Targeted outreach to non-adherent, motivational interviewing | +3-5% PDC |
| Chasing 5 Stars (PDC 83%+) | Home delivery, adherence packaging, comprehensive med review | +1-3% PDC |

### 4.4 High-Risk Non-Adherence Populations
| Population | Risk Factor | Intervention |
|-----------|------------|-------------|
| Low income areas (dim_sdoh) | Cost barrier | 340B pricing at FAC001/FAC005/FAC006, Medicaid enrollment |
| Multiple medications (≥5) | Complexity | Medication synchronization, pill organizer |
| Depression (F32.9) comorbidity | Motivation | Treat depression FIRST, integrated behavioral health |
| New-to-therapy patients | Education | Pharmacist consult at first fill, 14-day phone check |
| Insulin Glargine (1373463) | Injection anxiety | Diabetes educator, gradual dose titration |

## 5. Member Experience Domain (20% Weight)

### 5.1 CAHPS Survey Measures
| Measure | What Impacts Score |
|---------|-------------------|
| Getting needed care | Appointment access, referral timeliness |
| Getting appointments and care quickly | Wait times, same-day availability |
| Customer service | Phone responsiveness, issue resolution |
| Care coordination | Transition planning, follow-up after hospital |
| Rating of health care | Overall satisfaction with provider interaction |

### 5.2 Improvement Strategies
| Strategy | Measure Impact |
|----------|---------------|
| Open-access scheduling | Getting appointments quickly |
| Discharge phone calls within 48 hours | Care coordination |
| Telehealth availability | Getting needed care |
| Patient portal engagement | Getting information, overall satisfaction |

## 6. Payer-Specific Star Rating Implications

### 6.1 Medicare Advantage (PAY006/PAY007)
- **Direct financial impact:** 5% quality bonus at 4+ Stars
- All HEDIS measures contribute to Star Rating
- CAHPS and HOS surveys weighted significantly
- **Improvement bonus** available for plans improving ≥ 1 star

### 6.2 Commercial Plan Analogs (PAY001-005, PAY009)
While commercial plans don't use CMS Stars directly, many use NCQA HEDIS-based quality programs:

| Payer | Quality Program | Structure |
|-------|----------------|-----------|
| BCBS MI (PAY001) | Blue Distinction | Recognition-based, public reporting |
| Aetna (PAY002) | Aetna Quality Incentive | Shared savings based on HEDIS scores |
| United Healthcare (PAY003) | UHC Premium Designation | Provider tiering based on quality + cost |
| Cigna (PAY004) | Cigna Quality Rewards | Bonus payments for HEDIS performance |
| Priority Health (PAY009) | Value-Based Contract | Direct HEDIS measure incentives |

## 7. Star Rating Improvement Roadmap

### 7.1 Year 1 (2025) — Foundation
| Priority | Action | Target Improvement |
|----------|--------|-------------------|
| 1 | Medication adherence outreach program | +5% PDC across all 3 measures |
| 2 | Diabetic care gap closure | HbA1c screening > 90% |
| 3 | BP control optimization | CBP measure > 65% |
| 4 | Readmission reduction program | < 15% all-cause 30-day |

### 7.2 Year 2 (2026) — Optimization
| Priority | Action | Target |
|----------|--------|--------|
| 1 | Predictive non-adherence model | Identify at-risk patients before lapse |
| 2 | Social determinants integration | dim_sdoh data driving interventions |
| 3 | Specialty care coordination | Close specialist referral loops |
| 4 | Patient experience redesign | CAHPS score improvement |

### 7.3 Year 3 (2027) — Excellence
| Priority | Action | Target |
|----------|--------|--------|
| 1 | 5-Star achievement on adherence measures | PDC ≥ 83% population-level |
| 2 | Top-quartile on all clinical measures | Per CMS cut points |
| 3 | Integrated analytics platform | Real-time quality dashboards |
| 4 | Value-based contract expansion | All major payers on quality contracts |

## 8. Data Agent Queries for Star Rating Analytics
- "What is our medication adherence rate by drug class for Medicare patients?"
- "Which patients have PDC below 80% for statins?"
- "What is the HbA1c poor control rate by facility?"
- "How does our readmission rate compare to target for heart failure patients?"
- "Which payer has the highest denial rate affecting care access?"
- "What SDOH factors correlate with low medication adherence?"

---

*Last Updated: 2025-01-15 | Next Review: 2025-04-01 (Quarterly)*  
*Document ID: QM-STARS-002 | Version: 2025.1*

---

## References & Sources

1. CMS Medicare Star Ratings Technical Notes, CY2024. https://www.cms.gov/Medicare/Prescription-Drug-Coverage/PrescriptionDrugCovGenIn/PerformanceData
2. CMS Part C and D Star Ratings Methodology. 42 CFR § 422.166. https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-422/subpart-D/section-422.166
3. NCQA HEDIS Volume 2: Technical Specifications for Health Plans. https://www.ncqa.org/hedis/
4. CAHPS Health Plan Survey (Consumer Assessment of Healthcare Providers and Systems). AHRQ. https://www.ahrq.gov/cahps/surveys-guidance/hp/index.html
5. Health Outcomes Survey (HOS). CMS. https://www.hosonline.org/
6. CMS Quality Bonus Payment (QBP) Methodology. https://www.cms.gov/Medicare/Medicare-Advantage/Plan-Payment/Quality-Bonus
