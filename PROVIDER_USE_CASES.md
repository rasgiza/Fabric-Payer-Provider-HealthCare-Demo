# Provider Use Cases — What This Demo Solves

This document catalogs the **industry-wide use cases in the healthcare provider space** and maps each one to the specific capability this demo delivers. It is the "why this matters" companion to the [README](README.md): the README explains *what gets deployed*; this document explains *which real provider problems it answers* and *how*.

Every use case below is grounded in a recognized industry pain point (with sources) and traced to a concrete artifact in this repo — a Gold table, a semantic-model measure, a data agent, an RTI scoring notebook, or a Teams/Activator action. Nothing here is aspirational; it reflects what the launcher actually deploys.

> **Scope note.** This demo covers the **operations, analytics, revenue cycle, quality, population health, and program-integrity** surface of a provider organization. It is intentionally complementary to — not a replacement for — clinical documentation (Dragon / DAX Copilot), patient front-door/contact-center (Microsoft Cloud for Healthcare), and EHR-native workflows (Epic / Oracle Health). Those are called out as **complementary** where relevant.

---

## Table of Contents

1. [How to read this document](#how-to-read-this-document)
2. [Use case coverage at a glance](#use-case-coverage-at-a-glance)
3. [Domain 1 — Revenue Cycle Management (RCM)](#domain-1--revenue-cycle-management-rcm)
4. [Domain 2 — Quality & Value-Based Care](#domain-2--quality--value-based-care)
5. [Domain 3 — Population Health & Social Determinants (SDOH)](#domain-3--population-health--social-determinants-sdoh)
6. [Domain 4 — Clinical Operations & Throughput](#domain-4--clinical-operations--throughput)
7. [Domain 5 — Program Integrity (Fraud, Waste & Abuse)](#domain-5--program-integrity-fraud-waste--abuse)
8. [Domain 6 — Data & AI Foundation / Self-Service Analytics](#domain-6--data--ai-foundation--self-service-analytics)
9. [Traceability matrix — use case → demo asset](#traceability-matrix--use-case--demo-asset)
10. [What is intentionally out of scope](#what-is-intentionally-out-of-scope)
11. [Sources](#sources)

---

## How to read this document

Each use case follows the same shape so you can lift it straight into a customer conversation:

- **The industry pain** — what providers struggle with today, with a sourced data point.
- **Why it's hard** — the structural reason existing tools fall short.
- **How this demo solves it** — the exact table / measure / agent / notebook that answers it, and the question a user can ask.

Figures are drawn from public industry sources (CMS, NCQA, HFMA, NHCAA, KFF, AHA, CAQH, and others — see [Sources](#sources)). All patient, claim, and provider data in the demo is **100% synthetic**.

---

## Use case coverage at a glance

| # | Provider domain | Use case | Demo coverage |
|---|-----------------|----------|---------------|
| 1 | Revenue Cycle | Denial risk prediction & root-cause | ✅ Batch scoring + agent + dashboard |
| 2 | Revenue Cycle | Prior-authorization visibility & TAT | ✅ Fields modeled; agent + dashboard |
| 3 | Revenue Cycle | Payer contract & underpayment analytics | ✅ 12-payer model + agent |
| 4 | Revenue Cycle | Discharged-not-final-billed (DNFB) / AR | 🟡 Encounter + billing fields; extendable |
| 5 | Value-Based Care | 30-day readmission risk (HRRP) | ✅ Risk score + SDOH-informed + dashboard |
| 6 | Value-Based Care | HEDIS care-gap closure | ✅ 8 HEDIS measures + real-time alerts |
| 7 | Value-Based Care | Medication adherence (PDC / Star Ratings) | ✅ PDC by drug class + care-manager lists |
| 8 | Population Health | SDOH-informed risk stratification | ✅ Zip-level SDOH joined to every patient |
| 9 | Population Health | Health-equity reporting | ✅ SDOH + demographics segmentation |
| 10 | Clinical Ops | Real-time ADT-driven point-of-care alerts | ✅ RTI ADT events → Teams cards |
| 11 | Clinical Ops | High-cost / rising-risk member trajectory | ✅ Rolling-spend + ED superutilizer scoring |
| 12 | Clinical Ops | Capacity / throughput & length-of-stay | 🟡 LOS + ADT modeled; extendable |
| 13 | Program Integrity | Real-time claims fraud (FWA / SIU) | ✅ 4-signal real-time fraud scoring |
| 14 | Provider Network | Provider performance & outlier detection | ✅ Provider metrics + dashboard page |
| 15 | Data & AI | Natural-language self-service analytics | ✅ SQL agent + graph agent + Foundry |
| 16 | Data & AI | Knowledge-graph / relationship traversal | ✅ 12-entity / 18-relationship ontology |
| 17 | Data & AI | One-click analytics environment stand-up | ✅ Single-notebook, ~15-min deploy |

✅ = directly delivered by the demo   🟡 = data modeled; a small extension completes it

---

## Domain 1 — Revenue Cycle Management (RCM)

Revenue cycle is where providers lose the most money to preventable operational failure. Denials, underpayments, and slow billing directly erode margin.

### 1.1 Denial risk prediction & root-cause analysis

**The industry pain.** Initial claim denial rates now average **roughly 11-12%**, and have been trending upward; the majority of denials are preventable, yet a meaningful share are never reworked because appeals are costly. (Sources: Change Healthcare / Optum Denials Index; HFMA; AHA.)

**Why it's hard.** Most organizations only learn a claim was denied *after* submission and adjudication. There is rarely a real-time view of *which* claims are at risk *before* they go out the door, or *which payer* drives which denial reason.

**How this demo solves it.** The Gold layer computes a **denial-risk signal** on claims and exposes denial reason, payer, and appeal outcome through the `HealthcareDemoHLS` semantic model. The **`HealthcareHLSAgent`** answers questions like *"What is the overall denial rate by payer?"* and *"Which denial reasons are most common for Aetna?"*, and the Power BI **Claim Denials** page shows root cause, payer breakdown, and financial impact (waterfall + matrix). This turns reactive denial management into a proactive, root-cause workflow.

### 1.2 Prior-authorization (PA) visibility & turnaround time

**The industry pain.** Prior authorization is one of the most-cited administrative burdens in healthcare; physicians report it delays care and consumes staff hours, and CMS finalized the **Interoperability and Prior Authorization rule (CMS-0057-F)** to shorten decision timelines. (Sources: AMA prior-authorization surveys; CMS-0057-F; CAQH.)

**Why it's hard.** PA status, turnaround time, and peer-to-peer outcomes are scattered across payer portals and fax logs — invisible to analytics.

**How this demo solves it.** Prior-authorization attributes are modeled on the claims/encounter grain so the agent and dashboard can surface PA-related denials and timely-filing risk by payer. Ask *"Which claims were denied for prior-authorization gaps?"* to see the exposure.

### 1.3 Payer contract & underpayment analytics

**The industry pain.** A typical health system manages **a dozen or more payer contracts**, each with different reimbursement rates, PA requirements, timely-filing deadlines, and denial behaviors. Underpayments and contract variance quietly leak revenue.

**Why it's hard.** Without contract-level analytics, systems can't see which payers underpay, deny most, or create the most rework.

**How this demo solves it.** The demo models **12 simulated payers** with realistic contract rates, denial patterns, and formulary coverage. The agent answers *"Which payer has the highest denial rate and lowest collection rate?"*, and the graph agent can trace **claim → encounter → provider → payer** relationships to reveal where contract negotiation should focus.

### 1.4 Discharged-not-final-billed (DNFB) & accounts receivable

**The industry pain.** Cash tied up in DNFB and aged AR is a persistent RCM KPI; every day in DNFB delays cash and increases denial/timely-filing risk.

**How this demo solves it (🟡 extendable).** The encounter grain carries discharge dates, length of stay, and billing status fields, so DNFB and AR-aging measures are a short DAX extension on the existing star schema — the data foundation is already in place.

---

## Domain 2 — Quality & Value-Based Care

Under value-based reimbursement, quality measures are directly tied to payment. Missing a measure is missing revenue.

### 2.1 30-day readmission risk (CMS HRRP)

**The industry pain.** The **CMS Hospital Readmission Reduction Program (HRRP)** penalizes hospitals up to **3% of Medicare inpatient payments** for excess 30-day readmissions across tracked conditions (AMI, CHF, COPD, pneumonia, CABG, elective TKA/THA). (Source: CMS HRRP.)

**Why it's hard.** Effective risk scoring must combine clinical history with social risk — and SDOH data rarely sits next to clinical data.

**How this demo solves it.** `fact_encounter` carries a **readmission risk score and category** computed from encounter history, diagnosis complexity, and SDOH factors; `agg_readmission` aggregates rates by facility and diagnosis. Care managers get a targetable worklist *before discharge*. Ask *"Which patients have the highest readmission risk?"* or drill into the Power BI **Readmission Risk** page (heatmap + decomposition tree). When streaming is enabled, ADT events trigger real-time alerts (see [4.1](#41-real-time-adt-driven-point-of-care-alerts)).

### 2.2 HEDIS care-gap closure

**The industry pain.** Payers spend real money per member per month chasing HEDIS gaps, but the highest-leverage moment to close a gap is **when the patient is already in front of a provider** — and the care team usually doesn't know a gap is open. (Sources: NCQA HEDIS; industry outreach-cost benchmarks.)

**How this demo solves it.** When `DEPLOY_STREAMING=True`, **`NB_RTI_Care_Gap_Alerts`** fires on each ADT event, joins the patient's **8 HEDIS measures** (CDC, COL, BCS, SPC, CBP, SPD, OMW, PPC), ranks open gaps by priority, and writes human-readable alerts to `rti_care_gap_alerts`. Activator pushes the alert to the care team in **Microsoft Teams** at the point of care.

### 2.3 Medication adherence (PDC) & Star Ratings

**The industry pain.** **CMS Star Ratings triple-weight** medication-adherence measures (diabetes medications, RAS antagonists, statins). Adherence is one of the single largest drivers of plan quality ratings and associated bonus payments — but gaps are invisible without pharmacy-claims integration. (Source: CMS Star Ratings technical notes; PQA PDC methodology.)

**How this demo solves it.** The Gold layer computes **Proportion of Days Covered (PDC)** per patient per drug class and flags non-adherent members with chronic conditions. Ask *"Show medication adherence by drug class for high-risk patients"* to produce a care-manager intervention list; the Power BI **Medication Adherence** page shows PDC gauges and non-adherent populations.

---

## Domain 3 — Population Health & Social Determinants (SDOH)

### 3.1 SDOH-informed risk stratification

**The industry pain.** A large majority of health outcomes are driven by factors **outside the clinic** — housing, food access, transportation, income — yet SDOH data rarely appears alongside clinical data. (Sources: County Health Rankings / RWJF; CDC SVI; KFF.)

**How this demo solves it.** The demo joins **zip-code-level SDOH** — poverty rate, food-desert flag, transportation score, housing instability, and a social-vulnerability index — to **every patient, encounter, and claim**. This powers SDOH-informed readmission prevention and population stratification. Ask *"Which zip codes have the highest social vulnerability and readmission risk?"*

### 3.2 Health-equity reporting

**The industry pain.** Regulators and boards increasingly expect health-equity stratification of outcomes by demographic and social risk.

**How this demo solves it.** Because SDOH and demographics are attached to the clinical grain, the **Social Determinants** dashboard page and the agent can segment any outcome (denials, readmissions, adherence) by social-vulnerability and demographic cohort.

---

## Domain 4 — Clinical Operations & Throughput

### 4.1 Real-time ADT-driven point-of-care alerts

**The industry pain.** The most valuable operational signals — an admission, a discharge, a transfer — are perishable. Batch analytics that refresh nightly miss the window when a care manager could actually act.

**How this demo solves it.** With streaming enabled, ADT events land in the KQL database (`rti_adt_events`), scoring notebooks evaluate them in seconds, and **Activator → Teams cards** push the alert into the workflow the user already lives in. This is the demo's "push" surface: intelligence delivered the instant an event fires, not the next morning.

### 4.2 High-cost / rising-risk member trajectory

**The industry pain.** A small share of members drives the majority of total cost. Identifying members **trending toward** high-cost status enables care-management intervention before a catastrophic, avoidable event. (Sources: AHRQ / KFF concentration-of-spending analyses.)

**How this demo solves it.** **`NB_RTI_HighCost_Trajectory`** computes 30- and 90-day rolling spend, flags members exceeding spend thresholds, and detects **ED superutilizers** (≥3 emergency visits in 30 days), writing to `rti_highcost_alerts`. The **`HealthcareOpsAgent`** (KQL-backed) answers *"Which members are trending toward high-cost this month?"*

### 4.3 Capacity, throughput & length-of-stay

**The industry pain.** Throughput and length-of-stay (LOS) directly affect capacity, cost, and patient experience.

**How this demo solves it (🟡 extendable).** LOS, discharge timing, and ADT flow are modeled on `fact_encounter` and the RTI ADT stream, so LOS-outlier and capacity measures extend directly on the existing foundation.

---

## Domain 5 — Program Integrity (Fraud, Waste & Abuse)

### 5.1 Real-time claims fraud detection (SIU)

**The industry pain.** Estimates put U.S. healthcare fraud losses in the **tens of billions of dollars annually** (NHCAA cites figures in the range of tens of billions to hundreds of billions depending on methodology). Special Investigations Units (SIU) typically investigate **weeks after** submission — by which point the money is gone. (Source: NHCAA.)

**How this demo solves it.** With streaming enabled, **`NB_RTI_Fraud_Detection`** scores every claim in real time using four rule-based signals — **velocity burst**, **amount outlier** (>3σ of the provider's historical mean), **geographic anomaly**, and **upcoding** (over-use of the highest E&M code) — into CRITICAL/HIGH/MEDIUM/LOW tiers, writing to `rti_fraud_scores` with lat/long for fraud-hotspot map visuals on the RTI Dashboard.

---

## Domain 6 — Data & AI Foundation / Self-Service Analytics

The cross-cutting reason the above is possible: one governed data foundation with multiple intelligence surfaces on top.

### 6.1 Natural-language self-service analytics

**The industry pain.** Clinical, quality, and finance stakeholders can't wait in a BI backlog for every question, and most can't write SQL or DAX.

**How this demo solves it.** Two complementary agents make the data conversational: **`HealthcareHLSAgent`** (SQL-based, for aggregations/rates/trends) and the **Healthcare Ontology Agent** (graph traversal, for entity lookups and relationships). The **Foundry Orchestrator** adds knowledge-base grounding with citations for hybrid clinical-decision-support questions. See [SAMPLE_QUESTIONS.md](SAMPLE_QUESTIONS.md) for 90+ tested questions, including an **Executive Pain-Point** set framed for CFO/CMO/CMIO/COO/VP Population Health/CIO.

### 6.2 Knowledge-graph / relationship traversal

**The industry pain.** Many provider questions are inherently about **relationships** — "trace this claim from patient to payer," "show this patient's care pathway" — which flatten badly into SQL joins.

**How this demo solves it.** An auto-deployed ontology (**12 entities, 18 relationships**) connects patients → encounters → claims → providers → payers → diagnoses → prescriptions, letting the graph agent answer traversal questions directly.

### 6.3 One-click analytics environment stand-up

**The industry pain.** Traditional healthcare analytics projects take **weeks to provision** — installing Python, configuring credentials, deploying infrastructure, debugging auth — before a single question is answered.

**How this demo solves it.** **One notebook, one click, ~15 minutes.** SQL-only analysts, clinical informaticists, and business users get a fully functional Fabric environment — medallion lakehouses, semantic model, ontology, agents, dashboards — with no command line. This is itself a provider use case: *time-to-insight* as a competitive lever.

---

## Traceability matrix — use case → demo asset

| Use case | Primary demo asset(s) | Sample question |
|----------|-----------------------|-----------------|
| Denial risk & root-cause | `HealthcareDemoHLS` SM · `HealthcareHLSAgent` · PBI *Claim Denials* | "What is the denial rate by payer, and the top reasons?" |
| Prior-auth visibility | Claims PA fields · `HealthcareHLSAgent` | "Which claims were denied for prior-authorization gaps?" |
| Contract / underpayment | 12-payer model · Ontology Agent | "Trace denied claims from provider to payer for Aetna." |
| Readmission risk (HRRP) | `fact_encounter` risk score · `agg_readmission` · PBI *Readmission Risk* | "Which patients have the highest readmission risk?" |
| HEDIS care-gap closure ⚡ | `NB_RTI_Care_Gap_Alerts` · `rti_care_gap_alerts` · Teams | "Which facilities have the most open care gaps?" |
| Medication adherence | Gold PDC measures · PBI *Medication Adherence* | "Show medication adherence by drug class for high-risk patients." |
| SDOH stratification | Zip-level SDOH join · PBI *Social Determinants* | "Which zip codes have the highest SVI and readmission risk?" |
| Real-time ADT alerts ⚡ | `rti_adt_events` · Activator → Teams | (event-driven push) |
| High-cost trajectory ⚡ | `NB_RTI_HighCost_Trajectory` · `HealthcareOpsAgent` | "Which members are trending toward high-cost this month?" |
| Fraud / FWA ⚡ | `NB_RTI_Fraud_Detection` · `rti_fraud_scores` · RTI Dashboard | "Show the highest-risk fraud claims and hotspots." |
| Provider performance | SM provider metrics · PBI *Provider Performance* | "Rank providers by cost and outlier behavior." |
| NL self-service analytics | `HealthcareHLSAgent` · Ontology Agent · Foundry | (any of the above, in natural language) |
| Environment stand-up | `Healthcare_Launcher.ipynb` | (one-click deploy) |

⚡ = requires `DEPLOY_STREAMING = True`

---

## What is intentionally out of scope

Being explicit here builds credibility in customer conversations. This demo is **operations/analytics/RCM/quality-focused** and complements — does not replace — these adjacent provider solutions:

- **Clinical documentation / ambient scribe** — complementary to Dragon Copilot / DAX Copilot.
- **Patient front door, contact center, scheduling** — complementary to Microsoft Cloud for Healthcare patient-experience accelerators.
- **EHR-native clinical workflows** — care managers ultimately act in Epic (Healthy Planet / In Basket) or Oracle Health; this demo produces the *signals and worklists* that feed those surfaces.
- **FHIR interoperability surface** — the data foundation is FHIR-alignable, but the demo does not expose a FHIR endpoint out of the box.

---

## Sources

Industry figures referenced above are drawn from public, widely-cited sources. Use these for attribution in customer materials:

- **CMS Hospital Readmission Reduction Program (HRRP)** — penalty structure and tracked conditions.
- **CMS Medicare Part C & D Star Ratings** — technical notes; triple-weighted adherence measures.
- **NCQA HEDIS** — measure definitions (CDC, COL, BCS, SPC, CBP, SPD, OMW, PPC).
- **PQA (Pharmacy Quality Alliance)** — Proportion of Days Covered (PDC) methodology.
- **Change Healthcare / Optum Denials Index** and **HFMA** — denial-rate trends and rework cost.
- **AHA (American Hospital Association)** — administrative burden and denial impact.
- **AMA prior-authorization surveys** and **CMS-0057-F Interoperability and Prior Authorization Final Rule** — PA burden and turnaround requirements.
- **CAQH Index** — administrative-transaction cost and automation opportunity.
- **NHCAA (National Health Care Anti-Fraud Association)** — healthcare fraud loss estimates.
- **County Health Rankings / RWJF**, **CDC Social Vulnerability Index (SVI)**, and **KFF** — social determinants and outcome drivers.
- **AHRQ / KFF** — concentration of healthcare spending (small share of members → majority of cost).

> All statistics are used illustratively to frame industry pain points. All data in the demo itself is **100% synthetic** and contains no PHI.
