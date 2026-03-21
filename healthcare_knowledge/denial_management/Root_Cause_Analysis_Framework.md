# Lakeside Health System — Claim Denial Root Cause Analysis Framework

**Effective Date:** January 1, 2025  
**Revenue Cycle Analytics & Quality Improvement**  
**Purpose:** Systematic framework for identifying, categorizing, and eliminating root causes of claim denials  
**Data Sources:** fact_claim, dim_payer, dim_facility, agg_denial_by_date, agg_denial_by_payer

---

## 1. Framework Overview

This root cause analysis (RCA) framework maps every denial to an **upstream process failure** and prescribes corrective actions. The goal is to reduce the overall denial rate from the current ~10% to **< 5%** within 12 months.

### 1.1 Denial Taxonomy
Every denial maps to one of three root cause categories:

| Category | Denial Reasons | % of Denials | Responsible Team |
|----------|---------------|-------------|-----------------|
| **Process Failure** | Prior Auth Required, Missing Documentation, Duplicate Claim | ~52% | Revenue Cycle Operations |
| **Clinical Documentation** | Not Medically Necessary, Invalid Code | ~34% | Clinical Documentation Improvement (CDI) |
| **Eligibility/Access** | Coverage Expired, Out of Network | ~14% | Patient Access / Registration |

## 2. Root Cause Analysis by Denial Reason

### 2.1 Prior Auth Required (30% of denials)

#### Fishbone Analysis
```
                    PEOPLE                    PROCESS
                      |                         |
     Provider unaware of PA req ←→ No real-time PA check at ordering
     PA coordinator backlog    ←→ Manual PA identification process
     New staff training gaps   ←→ No standardized PA workflow
                      |                         |
              ─────── PRIOR AUTH DENIAL ────────
                      |                         |
     PA requirements changed  ←→ Legacy system doesn't flag PA
     Payer portal downtime    ←→ No automated PA submission
     Formulary update missed  ←→ Disconnected payer data feeds
                      |                         |
                   POLICY                   TECHNOLOGY
```

#### Root Causes Ranked by Impact
| Root Cause | Impact | Corrective Action | Owner | Timeline |
|-----------|--------|-------------------|-------|----------|
| No real-time PA check at order entry | High | Implement PA decision support at CPOE | IT + Rev Cycle | Q2 2025 |
| PA coordinator capacity | High | Staff model: 1 FTE per 500 PA cases/month | HR + Rev Cycle | Q1 2025 |
| Payer policy changes not communicated | Medium | Monthly payer update bulletin to all providers | Managed Care | Ongoing |
| PA obtained but not linked to claim | Medium | Automated PA-to-claim matching | IT | Q3 2025 |
| Emergency retro PA missed (48-hour window) | Medium | Automated retro PA alert for ED admissions | IT + ED | Q1 2025 |

### 2.2 Not Medically Necessary (22% of denials)

#### Root Causes Ranked
| Root Cause | Impact | Corrective Action | Owner |
|-----------|--------|-------------------|-------|
| Insufficient clinical documentation | High | CDI specialist reviews before submission | CDI Team |
| Diagnosis doesn't support procedure | High | CPT-to-ICD pairing validation rules | Coding |
| Missing specialist supporting letter | Medium | Auto-request specialist letter for high-cost procedures | Care Coord |
| Outdated clinical protocols referenced | Medium | Annual guideline update and provider education | CMO |
| Lack of alternative treatment documentation | Medium | "Failed alternatives" section added to templates | CDI Team |

#### High-Risk Procedure/Diagnosis Pairs
| Procedure | ICD-10 | Common Denial Trigger | Prevention |
|-----------|--------|--------------------|-----------|
| CT Abdomen (74177) | R10.9 (Abdominal pain) | "Insufficient workup" | Document physical exam, labs, ultrasound first |
| Echo (93306) | I50.9 (CHF) | "Repeat within 12 months" | Document clinical status change triggering repeat |
| TKR (27447) | Various musculoskeletal | "Conservative therapy insufficient" | 6+ months PT, imaging, injection documentation |
| Insulin (1373463) | E11.9 (Diabetes) | "Oral therapy not exhausted" | Document 90+ days dual oral therapy failure |
| Inpatient vs Observation | J18.9 (Pneumonia) | "Doesn't meet inpatient criteria" | InterQual/Milliman criteria documented at admission |

### 2.3 Missing Documentation (18% of denials)

#### Root Causes Ranked
| Root Cause | Impact | Corrective Action | Owner |
|-----------|--------|-------------------|-------|
| Operative report not finalized timely | High | 48-hour signature requirement, automated reminders | Surgery dept |
| H&P not completed within 24 hours | High | H&P delinquency dashboard, medical staff bylaws | CMO |
| Referring provider records not obtained | Medium | Standardized record request at scheduling | Patient Access |
| PA number not included on claim | Medium | PA-claim linkage automation | Rev Cycle IT |
| Pathology report pending at claim submission | Low | Hold claim until path results available | Billing |

### 2.4 Invalid Code (12% of denials)

#### Root Causes Ranked
| Root Cause | Impact | Corrective Action | Owner |
|-----------|--------|-------------------|-------|
| ICD-10 specificity insufficient | High | Coding specificity audits, auto-flag truncated codes | Coding |
| CPT-to-diagnosis mismatch | High | Pre-submission edit engine rules | Rev Cycle IT |
| Modifier error (missing/wrong) | Medium | Modifier decision support tool | Coding |
| Outdated code (annual updates missed) | Medium | Annual code update education + system refresh | Coding Mgr |
| Gender/age mismatch | Low | Auto-validation against demographics | IT |

### 2.5 Coverage Expired (8% of denials)

#### Root Causes Ranked
| Root Cause | Impact | Corrective Action | Owner |
|-----------|--------|-------------------|-------|
| No eligibility check before service | High | Real-time eligibility at every encounter | Registration |
| Eligibility changed between scheduling and service | Medium | T-2 day (48 hours before) reverification | Scheduling |
| Medicaid (PAY008) coverage gap | Medium | Coverage advocacy, retro eligibility requests | Social Work |
| COBRA not yet activated | Low | Patient notification process | Patient Access |

### 2.6 Out of Network (6% of denials)

#### Root Causes Ranked
| Root Cause | Impact | Corrective Action | Owner |
|-----------|--------|-------------------|-------|
| Patient referred to OON facility/provider | High | Network status visible in referral workflow | Managed Care |
| FAC003/FAC007/FAC008 not in all networks | Medium | Network gap analysis + contract negotiations | Managed Care |
| Specialist provider OON for specific payer | Medium | Network directory in EHR |  IT + Managed Care |
| Emergency at OON facility | Low | No Surprises Act compliance | Legal |

### 2.7 Duplicate Claim (4% of denials)

#### Root Causes Ranked
| Root Cause | Impact | Corrective Action | Owner |
|-----------|--------|-------------------|-------|
| System resubmission error | High | Duplicate claim detection pre-submission | Rev Cycle IT |
| Bilateral procedures coded wrong | Medium | Modifier 50 or RT/LT education | Coding |
| Same-day multiple encounters | Low | Encounter-level claim linking | Billing |

## 3. Denial Prevention Dashboard Metrics

### 3.1 Leading Indicators (Predict Denials Before They Happen)
| Metric | Red Flag Threshold | Data Source |
|--------|-------------------|-------------|
| PA cases pending > 5 days | > 15% of cases | PA tracking system |
| Operative reports unsigned > 48 hours | > 10% of surgeries | EHR documentation queue |
| Real-time eligibility check rate | < 90% of encounters | Registration system |
| Coding accuracy rate (audit) | < 95% accuracy | Coding audit reports |
| Claim scrubber rejection rate | > 8% | Claim submission engine |

### 3.2 Lagging Indicators (Measure Denial Outcomes)
| Metric | Target | Data Source |
|--------|--------|-------------|
| Overall denial rate | < 5% | agg_denial_by_date |
| Denial rate by payer | Varies | agg_denial_by_payer |
| Average days to appeal | < 15 days | Appeal tracking |
| Appeal success rate | ≥ 55% | Appeal outcomes |
| Net collection rate (post-denial) | ≥ 95% | Revenue cycle KPIs |
| Write-off from denials | < $2.1M/year (50% reduction) | Financial reports |

### 3.3 Data Agent Queries for RCA
The Fabric Data Agent can answer these denial RCA questions:
- "What are the top denial reasons by payer for the last quarter?"
- "Which facility has the highest denial rate and for what reason?"
- "What is the trend in Prior Auth Required denials month over month?"
- "Which payer denies the most claims as Not Medically Necessary?"
- "What is the denial rate for CHF (I50.9) patients by payer?"
- "How does denial rate correlate with encounter type (inpatient vs outpatient)?"

## 4. Corrective Action Priority Matrix

### Quadrant Model (Impact vs Effort)

**HIGH IMPACT + LOW EFFORT (Do First):**
- Real-time eligibility verification (Coverage Expired)
- Pre-submission claim scrubber rules (Invalid Code, Duplicate)
- PA number auto-linking to claims (Prior Auth Required)

**HIGH IMPACT + HIGH EFFORT (Plan and Execute):**
- Real-time PA decision support at CPOE (Prior Auth Required)
- CDI integration into clinical workflow (Not Medically Necessary)
- Automated payer policy update system (Prior Auth Required)

**LOW IMPACT + LOW EFFORT (Quick Wins):**
- Modifier education refresher (Invalid Code)
- Operative report signature reminders (Missing Documentation)
- Network directory in referral module (Out of Network)

**LOW IMPACT + HIGH EFFORT (Deprioritize):**
- Complete payer portal integration (diminishing returns)
- Building custom denial prediction ML model (future phase)

## 5. Monthly Denial Review Meeting Agenda

| Agenda Item | Time | Owner |
|------------|------|-------|
| Denial rate dashboard review | 10 min | Rev Cycle Analytics |
| Top 3 denials by volume and root cause | 15 min | Denial Management Team |
| Payer-specific trends (agg_denial_by_payer) | 10 min | Managed Care |
| Corrective action status updates | 10 min | Action owners |
| New payer policy changes | 5 min | Managed Care |
| Escalation items | 10 min | VP Revenue Cycle |

**Attendees:** VP Revenue Cycle, CMO (or designee), Coding Manager, Managed Care Director, CDI Director, Patient Access Director, IT Revenue Cycle Lead

---

*Last Updated: 2025-01-20 | Next Review: 2025-07-20*  
*Document ID: DM-RCA-003 | Version: 2.0*

---

## References & Sources

1. AHRQ Patient Safety Network. Root Cause Analysis. Agency for Healthcare Research and Quality. https://psnet.ahrq.gov/primer/root-cause-analysis
2. IHI. Institute for Healthcare Improvement. Model for Improvement and PDSA Cycles. https://www.ihi.org/resources/Pages/HowtoImprove/default.aspx
3. CMS CERT Program Analysis Reports. Comprehensive Error Rate Testing. https://www.cms.gov/Research-Statistics-Data-and-Systems/Monitoring-Programs/Medicare-FFS-Compliance-Programs/CERT
4. HFMA. Revenue Cycle Denial Management Benchmarks. Healthcare Financial Management Association. https://www.hfma.org/
5. The Joint Commission. Sentinel Event Policy and Root Cause Analysis Framework. https://www.jointcommission.org/measurement/sentinel-event-policy/
6. ASQ. Six Sigma and Process Improvement Tools (Fishbone/Ishikawa, Pareto Analysis). American Society for Quality. https://asq.org/quality-resources
