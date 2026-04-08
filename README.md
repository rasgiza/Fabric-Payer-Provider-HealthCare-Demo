# Fabric-Payer-Provider-HealthCare-Demo

One-click deployment of a complete **Healthcare Payer/Provider Analytics** solution into Microsoft Fabric — no Python install, no `.env` files, no manual setup.

---

## Table of Contents

1. [Why This Demo? — The Payer & Provider Pain Points](#why-this-demo--the-payer--provider-pain-points)
2. [Quick Start](#quick-start)
3. [What Gets Deployed](#what-gets-deployed)
   - [Data Volumes (Default)](#data-volumes-default)
4. [Architecture](#architecture)
5. [Deployment Flow](#deployment-flow)
   - [What happens when you click "Run All"](#what-happens-when-you-click-run-all)
   - [Deployment Stages Detail](#deployment-stages-detail)
6. [After Deployment](#after-deployment)
   - [Explore the Data](#explore-the-data)
   - [Sample Questions — Data Agents](#sample-questions--data-agents)
   - [Data Agent Reference](#data-agent-reference)
   - [Power BI Dashboard](#power-bi-dashboard)
7. [Real-Time Intelligence (RTI)](#real-time-intelligence-rti--3-payerprovider-use-cases)
   - [Claims Fraud Detection](#use-case-1-claims-fraud-detection)
   - [Care Gap Closure](#use-case-2-care-gap-closure-at-point-of-care)
   - [High-Cost Member Trajectory](#use-case-3-high-cost-member-trajectory)
   - [RTI Data Tables](#rti-data-tables)
   - [Switching to Live Streaming](#switching-to-live-streaming)
   - [Future: Operations Agent](#future-use-case-4--operations-agent)
8. [Ontology & Graph Model Setup](#create-the-ontology--graph-model-manual--10-min)
9. [Data Activator / Reflex Setup](#set-up-data-activator-alerts-manual--15-min)
10. [Run Incremental Loads](#run-incremental-loads)
11. [Configuration Options](#configuration-options)
12. [Prerequisites](#prerequisites)
13. [Repository Structure](#repository-structure)
14. [Troubleshooting](#troubleshooting)
15. [Credits](#credits)

---

## Why This Demo? — The Payer & Provider Pain Points

Healthcare payers and providers face compounding operational challenges that erode revenue, increase regulatory risk, and compromise patient outcomes. This demo addresses **six critical pain points** that cost the U.S. healthcare system billions annually:

### 1. Claim Denials Are Draining Revenue

> **Industry average denial rate: 10-15%** — costing a mid-size health system **$4.2M+ per year** in rework, appeals, and lost revenue.

Payers deny claims for preventable reasons: missing documentation (23%), invalid codes (18%), eligibility issues (14%), and prior authorization gaps. Most organizations lack real-time visibility into *which* claims are at risk *before* submission. This demo builds a **denial risk scoring model** that flags high-risk claims proactively, surfaces root causes by payer, and tracks appeal success rates — turning reactive denial management into a predictive workflow.

### 2. Readmissions Drive CMS Penalties

> **CMS Hospital Readmission Reduction Program (HRRP)** penalizes hospitals **up to 3% of total Medicare reimbursement** — for a $450M system, that's **$13.5M at stake**.

30-day readmissions for CHF, COPD, pneumonia, AMI, and TKA/THA are tracked and penalized. Yet most providers lack integrated risk scoring that combines clinical data with social determinants. This demo computes **readmission risk scores** using encounter history, diagnosis complexity, and SDOH factors (food deserts, housing instability, transportation barriers), enabling targeted discharge planning before patients leave the facility.

### 3. Medication Non-Adherence Sinks Star Ratings

> **CMS Star Ratings** triple-weight medication adherence measures (diabetes, RAS antagonists, statins) — making PDC scores the **single largest driver** of plan quality ratings and bonus payments.

Plans with 4+ stars receive significant CMS bonus payments, but adherence gaps are invisible without pharmacy claims integration. This demo calculates **Proportion of Days Covered (PDC)** per patient per drug class, identifies non-adherent members with chronic conditions, and maps adherence gaps to HEDIS measures — giving care managers actionable intervention lists.

### 4. Social Determinants Are Invisible in Clinical Workflows

> **80% of health outcomes** are driven by factors outside the clinic — yet SDOH data rarely appears alongside clinical data.

Zip-code-level poverty rates, food desert flags, transportation scores, housing instability rates, and social vulnerability indices exist in public datasets but aren't integrated into analytics platforms. This demo joins **SDOH data at the zip-code level** to every patient, encounter, and claim — enabling population health stratification, SDOH-informed readmission prevention, and health equity reporting.

### 5. Provider-Payer Contract Complexity Creates Revenue Leakage

> Health systems manage **12+ payer contracts** with different reimbursement rates, PA requirements, timely filing deadlines, and denial behaviors.

Without contract-level analytics, systems can't identify which payers underpay, which deny most frequently, or where network adequacy gaps exist. This demo models **payer-specific analytics** across 12 simulated payers with realistic contract rates, denial patterns, and formulary coverage — revealing collection rate variance and contract negotiation priorities.

### 6. Analytics Teams Can't Stand Up Environments Fast Enough

> Traditional healthcare analytics projects take **weeks to provision** — installing Python, configuring credentials, deploying infrastructure, debugging authentication.

This demo eliminates the entire setup burden. **One notebook, one click, fifteen minutes.** SQL-only analysts, clinical informaticists, and business users can explore a fully functional environment without touching a command line.

### What This Demo Proves

By combining all six dimensions — **claims + readmissions + adherence + SDOH + provider network + quality measures** — in a single Fabric workspace, this demo shows how Microsoft Fabric's unified platform (OneLake, Spark, Direct Lake, Copilot AI) can deliver:

- **Real-time denial risk dashboards** with root cause analysis and appeal tracking
- **Predictive readmission scoring** with SDOH-informed discharge planning
- **HEDIS-aligned medication adherence** monitoring with care gap closure
- **Natural language analytics** via Fabric Data Agent and Azure AI Foundry
- **Ontology-driven knowledge graphs** connecting patients → encounters → claims → providers → payers

All from a single workspace deployed in minutes.

---

## Quick Start

1. **Create an empty Fabric workspace** (F64+ capacity recommended)
2. **Import** `Healthcare_Launcher.ipynb` into the workspace  
   *(Workspace → Import → Notebook → upload the .ipynb file)*
3. **Run All** — wait ~15-20 minutes

> **That's it — no configuration needed.** The notebook pulls from the public repo `rasgiza/Fabric-Payer-Provider-HealthCare-Demo` by default. If you want to change settings, edit Cell 3 (the Configuration cell) before running — for example, set `DEPLOY_RTI = False` to skip Real-Time Intelligence, or point `GITHUB_OWNER` to your own fork.

The launcher creates a deploy lakehouse, downloads the repo, deploys all artifacts in the correct stage order, generates sample data, runs the ETL pipeline, and sets up RTI — fully automated.

## What Gets Deployed

| Layer | Items | Description |
|-------|-------|-------------|
| **Lakehouses (4)** | `lh_bronze_raw`, `lh_silver_stage`, `lh_silver_ods`, `lh_gold_curated` | Medallion architecture storage |
| **Notebooks (7)** | 5 ETL + `NB_Generate_Sample_Data` + `NB_Generate_Incremental_Data` | Spark-based data processing |
| **Pipelines (2)** | `PL_Healthcare_Full_Load`, `PL_Healthcare_Master` | Orchestration with full/incremental modes |
| **Semantic Model** | `HealthcareDemoHLS` | Star schema for Power BI (facts + dimensions) |
| **Data Agent** | `HealthcareHLSAgent` | Copilot AI agent with healthcare knowledge |
| **Ontology** | `Healthcare_Demo_Ontology_HLS` | GraphQL entity model — **manual UI setup** (see guide below) |
| **Eventhouse** | `Healthcare_RTI_Eventhouse` | Git-tracked RTI compute engine |
| **KQL Database** | `Healthcare_RTI_DB` | Git-tracked with schema (6 tables + streaming policies) |
| **Eventstream** | `Healthcare_RTI_Eventstream` | API-created at deploy-time (Custom Endpoint source) |
| **RTI Notebooks (6)** | Event Simulator, Post-Deploy Setup, 3 Scoring, Ops Agent (stub) | Real-Time Intelligence for fraud, care gaps, high-cost trajectory + ops agent |

### Data Volumes (Default)

| Entity | Rows |
|--------|------|
| Patients | 10,000 |
| Providers | 500 |
| Encounters | 100,000 |
| Claims | 100,000 |
| Prescriptions | ~250,000 |
| Diagnoses | ~200,000 |
| SDOH Zip Codes | ~560 |

## Architecture

Dual-path design: **Batch ETL** (authoritative, historical) + **Real-Time Intelligence** (operational, sub-minute). Batch feeds streaming — Gold dimension tables are the enrichment layer for real-time scoring.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     HEALTHCARE ANALYTICS ARCHITECTURE                        │
│                     Batch ETL + Real-Time Intelligence                       │
└──────────────────────────────────────────────────────────────────────────────┘

    BATCH PATH (existing)                    STREAMING PATH (new)
    Historical, authoritative,               Operational, sub-minute,
    runs daily / on-demand                   runs continuously
    ─────────────────────────                ────────────────────────

    Source Systems / CSV Gen                 Live Events
    NB_Generate_Sample_Data                  ADT feeds, claims clearinghouse,
    NB_Generate_Incremental_Data             pharmacy PBM, EHR HL7
           │                                          │
           ▼                                          ▼
    ┌──────────────┐                         ┌─────────────────────┐
    │ lh_bronze_raw│                         │ Eventstream         │
    │ (CSV files)  │                         │ (Custom Endpoint)   │
    └──────┬───────┘                         └─────────┬───────────┘
           │                                           │
    01_Bronze_Ingest                              streaming ingestion
           │                                           │
           ▼                                           ▼
    ┌──────────────┐                         ┌─────────────────────┐
    │ lh_silver    │                         │ Healthcare_RTI_DB   │
    │ stage → ODS  │                         │ (KQL Database)      │
    │ (cleansed,   │                         │                     │
    │  enriched)   │                         │ claims_events       │
    └──────┬───────┘                         │ adt_events          │
           │                                 │ rx_events           │
    03_Gold_Star_Schema                      └─────────┬───────────┘
           │                                           │
           ▼                                           │
    ┌──────────────────────┐          reads dims        │
    │   lh_gold_curated    │◄──────────────────────────┤
    │                      │   to enrich events         │
    │ DIMENSIONS (SCD2):   │                            │
    │  dim_patient         │──────────────┐             │
    │  dim_provider        │              │             │
    │  dim_facility        │   reference  │     scoring │
    │  dim_payer           │     data     │             │
    │  dim_diagnosis       │              ▼             ▼
    │  dim_medication      │    ┌──────────────────────────────┐
    │  dim_sdoh            │    │     SCORING NOTEBOOKS         │
    │  care_gaps           │    │                              │
    │  hedis_measures      │    │  NB_RTI_Fraud_Detection      │
    │                      │    │    reads: claims_events      │
    │ FACTS:               │    │    joins: dim_provider,      │
    │  fact_encounter      │    │           fact_claim (hist)  │
    │  fact_claim          │    │    writes: fraud_scores      │
    │  fact_prescription   │    │                              │
    │  fact_diagnosis      │    │  NB_RTI_Care_Gap_Alerts      │
    │                      │    │    reads: adt_events         │
    │ AGGREGATES:          │    │    joins: care_gaps,         │
    │  agg_readmission     │    │           hedis_measures,    │
    │  agg_med_adherence   │    │           dim_patient        │
    │                      │    │    writes: care_gap_alerts   │
    └──────────┬───────────┘    │                              │
               │                │  NB_RTI_HighCost_Trajectory  │
               │                │    reads: claims + adt events│
               │                │    joins: dim_patient         │
               │                │    writes: highcost_alerts   │
               │                └──────────────┬───────────────┘
               │                               │
               ▼                               ▼
    ┌────────────────────┐      ┌──────────────────────────────┐
    │ BATCH CONSUMPTION  │      │ REAL-TIME CONSUMPTION        │
    │                    │      │                              │
    │ Semantic Model     │      │ KQL Dashboard                │
    │ (Direct Lake)      │      │  • Fraud risk heatmap        │
    │                    │      │  • Care gap closure live      │
    │ Data Agent         │      │  • High-cost trend ticker    │
    │ (Copilot AI)       │      │                              │
    │                    │      │ Data Agent                   │
    │ Ontology + Graph   │      │  (queries RTI tables too)    │
    │ (Knowledge Graph)  │      │                              │
    │                    │      │ Operations Agent (future)    │
    │ Power BI Reports   │      │  • Unified triage worklist   │
    └────────────────────┘      │  • SLA & freshness monitor   │
                                │  • Action routing (SIU/EHR)  │
                                │                              │
                                │ Activator (Reflex)           │
                                │  • Teams/Email/Power Automate│
                                └──────────────────────────────┘
```

## Deployment Flow

The launcher notebook (`Healthcare_Launcher.ipynb`) automates the entire deployment. Under the hood, `fabric-launcher` performs these steps:

### What happens when you click "Run All"

1. **Install** `fabric-launcher` library (`%pip install fabric-launcher`)
2. **Initialize** the launcher — auto-detects workspace ID, validates workspace is empty
3. **Download** this GitHub repo as a ZIP archive from the configured branch
4. **Extract** to the notebook's default lakehouse at `Files/src/<repo-name>/`
   — the `workspace/` folder contains all Fabric item definitions (`.platform`, notebook content, TMDL, pipeline JSON, Eventhouse/KQL artifacts)
5. **Deploy Stage 1 — Lakehouses** — `lh_bronze_raw`, `lh_silver_stage`, `lh_silver_ods`, `lh_gold_curated`
   (must exist before notebooks that reference them as default lakehouses)
6. **Deploy Stage 2 — Eventhouse + KQL Database** — Git-tracked RTI infrastructure
   (`Healthcare_RTI_Eventhouse` + `Healthcare_RTI_DB` with `DatabaseSchema.kql`)
7. **Deploy Stage 3 — Notebooks** — 12 notebooks (5 ETL + 2 data gen + 5 RTI + 1 ops agent stub)
   (must exist before pipelines reference them as activities)
8. **Deploy Stage 4 — Data Pipelines** — `PL_Healthcare_Full_Load`, `PL_Healthcare_Master`
9. **Deploy Stage 5 — Semantic Model + Data Agent** — `HealthcareDemoHLS` (TMDL star schema) + `HealthcareHLSAgent` (Copilot AI)
10. **Validate** all deployed items — checks each item exists and has correct type
11. **Upload** healthcare knowledge docs from `healthcare_knowledge/` to `lh_gold_curated/Files/healthcare_knowledge/`
12. **Run** `NB_Generate_Sample_Data` — generates ~10K patients, 100K encounters, HEDIS measures, care gaps
13. **Trigger** `PL_Healthcare_Master` with `load_mode=full` — runs Bronze → Silver → Gold ETL (~8-15 min)
14. **Run** `NB_RTI_Setup_Eventhouse` — discovers deployed Eventhouse by name, creates 6 KQL tables + streaming policies, creates Eventstream with Custom Endpoint, outputs connection string
15. **Run** RTI scoring notebooks — Event Simulator (batch), Fraud Detection, Care Gap Alerts, High-Cost Trajectory
16. **Print** ontology setup instructions — user follows `ONTOLOGY_GRAPH_SETUP_GUIDE.md` manually (~10 min)

> **No manual lakehouse creation required.** Unlike manual deployment approaches that require creating a `deploy_staging` lakehouse and uploading folders, `fabric-launcher` handles repo download, extraction, and artifact reading automatically using the notebook's built-in default lakehouse.

### Deployment Stages Detail

| Stage | Item Types | Count | Why This Order |
|-------|-----------|-------|----------------|
| 1 | Lakehouse | 4 | Notebooks reference lakehouses via `logicalId` in `.metadata` — lakehouses must exist first |
| 2 | Eventhouse, KQLDatabase | 2 | RTI infra must be provisioned before `NB_RTI_Setup_Eventhouse` discovers them |
| 3 | Notebook | 12 | Pipelines reference notebooks as activities — notebooks must exist first |
| 4 | DataPipeline | 2 | Pipelines orchestrate notebook execution |
| 5 | SemanticModel, DataAgent | 2 | Semantic model needs Gold tables populated; Data Agent needs semantic model |

## After Deployment

### Explore the Data
- Open **lh_gold_curated** → Tables → you'll see star schema tables (fact_encounters, dim_patients, etc.)
- Open **HealthcareDemoHLS** semantic model → create Power BI reports

### Sample Questions — Data Agents

Open **HealthcareHLSAgent** in your Fabric workspace and try the pre-built questions covering claim denials, readmissions, medication adherence, SDOH, RTI scoring, and Foundry AI.

See **[SAMPLE_QUESTIONS.md](SAMPLE_QUESTIONS.md)** for 60+ copy-paste questions organized by domain.

### Data Agent Reference

For the complete agent configuration -- AI instructions, concept-to-table routing, SQL rules, few-shot examples, knowledge base, and customization guide -- see **[DATA_AGENT_GUIDE.md](DATA_AGENT_GUIDE.md)**.

### Power BI Dashboard

To build Power BI reports on the `HealthcareDemoHLS` semantic model (26 pre-built DAX measures, 6 recommended report pages, formatting, and Direct Lake tips) -- see **[POWERBI_DASHBOARD_GUIDE.md](POWERBI_DASHBOARD_GUIDE.md)**.

---

## Real-Time Intelligence (RTI) — 3 Payer/Provider Use Cases

When `DEPLOY_RTI=True`, the launcher deploys a full RTI stack: **Eventhouse + KQL Database + 3 scoring notebooks** that address high-value payer/provider pain points where batch analytics fall short.

### Use Case 1: Claims Fraud Detection

> **$68B lost to healthcare fraud annually** (NHCAA). Most SIU teams investigate claims weeks after submission — by then, the money is gone.

**NB_RTI_Fraud_Detection** scores every claim in real-time using 4 rule-based signals:
- **Velocity burst** — Provider submits many claims within a 1-hour window (30 pts max)
- **Amount outlier** — Claim exceeds 3σ of provider's historical mean (25 pts max)
- **Geographic anomaly** — Patient location far from provider facility (25 pts max)
- **Upcoding** — Consistent use of highest E&M code 99215 (20 pts max)

Risk tiers: **CRITICAL** (≥50) → **HIGH** (≥30) → **MEDIUM** (≥15) → **LOW**

**Output:** `rti_fraud_scores` with lat/long for map visuals showing fraud hotspots.

### Use Case 2: Care Gap Closure at Point of Care

> **Payers spend $2-4 per member per month** on outreach for HEDIS gaps. The highest-value moment is when the patient is *already in front of a provider* — but the care team doesn't know about open gaps.

**NB_RTI_Care_Gap_Alerts** fires when an ADT (Admit/Discharge/Transfer) event arrives:
1. Joins the encounter with the patient's **8 HEDIS measures** (CDC, COL, BCS, SPC, CBP, SPD, OMW, PPC)
2. Checks for open care gaps and ranks by priority (CRITICAL if diabetes/cancer gap >180 days)
3. Generates **human-readable alerts** for the care team at the bedside

**Output:** `rti_care_gap_alerts` with facility lat/long for map visuals showing which facilities have the most gap closure opportunities.

### Use Case 3: High-Cost Member Trajectory

> **5% of members drive 50% of total healthcare costs.** Early identification of members *trending toward* high-cost status enables care management intervention before catastrophic events.

**NB_RTI_HighCost_Trajectory** computes rolling windows over claims and encounters:
- **30-day and 90-day rolling spend** — flags members exceeding $15K/30d or $40K/90d
- **ED superutilizer detection** — ≥3 emergency visits in 30 days
- **Readmission tracking** — multiple admits within 30 days
- **Cost trend** — ACCELERATING / RISING / STABLE / DECLINING

Risk tiers: **CRITICAL** (high spend + frequent ED) → **HIGH** (high spend) → **MEDIUM** (ED/readmit/accelerating) → **LOW**

**Output:** `rti_highcost_alerts` with lat/long for map visuals showing cost hotspots.

### RTI Data Tables

| Table | Description | Rows (Default) |
|-------|-------------|----------------|
| `rti_claims_events` | Simulated claim submissions with fraud patterns | ~500 |
| `rti_adt_events` | ADT events (admit/discharge/transfer) | ~250 |
| `rti_rx_events` | Prescription fill events | ~166 |
| `rti_fraud_scores` | Scored claims with risk tiers and fraud flags | ~500 |
| `rti_care_gap_alerts` | Point-of-care gap closure alerts | varies |
| `rti_highcost_alerts` | Members on escalating cost trajectory | varies |

### Switching to Live Streaming

By default, the RTI notebooks run in **batch mode** (single batch → Delta tables). To enable continuous streaming:

1. The launcher already deployed the **Eventhouse** and **KQL Database** as Git artifacts
2. **NB_RTI_Setup_Eventhouse** discovers them, creates 6 KQL tables with streaming ingestion policies, and creates the **Eventstream** with a **Custom Endpoint** source
3. The notebook prints the Custom Endpoint **connection string** and **event hub name**
4. Open **NB_RTI_Event_Simulator** → set `MODE = "stream"`, paste `EVENTSTREAM_CONN_STR` and `EVENTHUB_NAME`
5. Run — events flow continuously every 5 seconds through Eventstream → KQL DB

> **Note:** If the connection string wasn't printed by the setup notebook, open the Eventstream in the Fabric portal, click the Custom Endpoint source node, and copy the values from the details panel.

### Future: Use Case 4 — Operations Agent

> **Status: Architecture stub** (`NB_RTI_Operations_Agent`) — planned for next phase.

The Operations Agent is an AI-powered operational intelligence layer that sits on top of the three RTI scoring outputs and unifies monitoring, triage, and action into a single interface.

| Module | Capability | Integration |
|--------|------------|-------------|
| **Unified Alert Triage** | Merges fraud + care gap + high-cost alerts into a single priority-ranked worklist, deduplicates by patient across alert types | KQL queries against Eventhouse |
| **SLA & Throughput Monitoring** | Tracks data freshness per input table, pipeline completion SLA, alert-to-action latency | Fabric REST API + KQL |
| **Automated Action Routing** | CRITICAL fraud → SIU queue, CRITICAL care gaps → provider EHR/fax, CRITICAL high-cost → care management referral | Fabric Data Activator (Reflex) |
| **Natural Language Ops** | Ops teams query alerts conversationally: "What are today's top 10 priorities?" | Azure AI Foundry Agent with KQL tools |

**Sample Operations Agent questions (planned):**

| # | Question |
|---|----------|
| 38 | What are today's top 10 priorities across all alert types? |
| 39 | Which facilities have the most CRITICAL alerts right now? |
| 40 | Is the claims pipeline running on time? When was the last event ingested? |
| 41 | Show me patients who triggered both fraud and high-cost alerts simultaneously. |
| 42 | How many CRITICAL alerts are unresolved from the last 24 hours? |
| 43 | What is the average time between event ingestion and alert generation? |

---

### Create the Ontology & Graph Model (Manual — ~10 min)

The ontology **cannot** be fully deployed via API — the Fabric Preview API creates unlinked ontology and graph items, which breaks Fabric IQ graph traversal and Copilot integration. You must create it from the semantic model in the UI.

Follow the step-by-step guide: **[ONTOLOGY_GRAPH_SETUP_GUIDE.md](ONTOLOGY_GRAPH_SETUP_GUIDE.md)**

Quick summary:
1. **New item** → Ontology → from semantic model `HealthcareDemoHLS`
2. **Delete** 3 unwanted entities (dim_date, agg_medication_adherence, agg_readmission_by_date)
3. **Rename** 10 entities (e.g., dim_patient → Patient) using the guide's master table
4. **Set** source keys and display names per the guide
5. **Replace** auto-generated relationships with 15 curated ones from the guide
6. **Build the graph** (Graph tab → Build a graph → select all)

The guide includes master configuration tables for all entities, relationships, and full property references.

### Set Up Data Activator Alerts (Manual — ~15 min)

Data Activator (Reflex) monitors RTI KQL tables and fires **proactive alerts** via Email, Teams, or Power Automate when scoring thresholds are breached. No code required — configuration only.

#### Step 1: Create a Reflex Item

1. In your Fabric workspace → **+ New item** → **Reflex**
2. Name it `Healthcare_RTI_Alerts`

#### Step 2: Connect to the KQL Database

1. In the Reflex item → **Get data** → **KQL Database**
2. Select `Healthcare_RTI_DB` (in the `Healthcare_RTI_Eventhouse`)
3. You'll add triggers for each of the 3 scoring tables below

#### Step 3: Configure Alert Rules

**Rule 1 — Fraud Detection (Critical Claims)**

| Setting | Value |
|---------|-------|
| **Table** | `fraud_scores` |
| **Monitor** | `fraud_score` |
| **Condition** | `fraud_score > 0.8 AND risk_tier == 'CRITICAL'` |
| **Action 1** | **Teams** → post to `#fraud-investigations` channel |
| **Action 2** | **Power Automate** → create SIU investigation case (optional) |
| **Card fields** | claim_id, patient_id, provider_id, fraud_score, fraud_flags |

**Rule 2 — Care Gap Closure (High Priority)**

| Setting | Value |
|---------|-------|
| **Table** | `care_gap_alerts` |
| **Monitor** | `alert_priority` |
| **Condition** | `alert_priority == 'HIGH' AND gap_days_overdue > 30` |
| **Action 1** | **Teams** → post to `#care-coordination` channel |
| **Action 2** | **Email** → notify assigned care manager (optional) |
| **Card fields** | patient_id, measure_name, gap_days_overdue, alert_text |

**Rule 3 — High-Cost Member Trajectory (Critical)**

| Setting | Value |
|---------|-------|
| **Table** | `highcost_alerts` |
| **Monitor** | `rolling_spend_90d` |
| **Condition** | `rolling_spend_90d > 50000 AND risk_tier == 'CRITICAL'` |
| **Action 1** | **Power Automate** → trigger care management workflow |
| **Action 2** | **Email** → notify case manager |
| **Card fields** | patient_id, rolling_spend_90d, ed_visits_30d, cost_trend |

#### Step 4: Verify Alerts Fire

1. Run **NB_RTI_Event_Simulator** in batch mode to generate test events
2. Run the 3 scoring notebooks (Fraud, Care Gap, HighCost)
3. Check your Teams channel / email for alert cards within ~60 seconds

> **Power Automate integration**: For complex routing (create ServiceNow tickets, update EHR systems, page on-call staff), select **Power Automate** as the action and build a flow that reads the alert payload. The Reflex trigger passes all card fields as dynamic content to the flow.

### Run Incremental Loads

After the initial full load, you can simulate daily operational data arriving. The pipeline supports a `load_mode` parameter that switches between full rebuild and incremental processing.

#### How It Works

The **PL_Healthcare_Master** pipeline accepts a `load_mode` parameter (default `"full"`). When set to `"incremental"`, the pipeline:

1. **Generates new data** — runs `NB_Generate_Incremental_Data` to create today's records
2. **Bronze: APPEND** — new CSVs are appended to existing Bronze tables (not overwritten), then archived to `Files/processed/` to prevent duplicate reads
3. **Silver: Full rebuild** — Silver notebooks always read all Bronze data, clean, deduplicate, and overwrite Silver tables (idempotent)
4. **Gold: MERGE** — Gold uses Delta Lake merge operations:
   - **SCD Type 2 dimensions** (`dim_patient`, `dim_provider`): detects attribute changes (city, state, zip, specialty, department), expires old versions (`is_current=0`), and inserts new versions with new surrogate keys
   - **Type 1 dimensions** (`dim_payer`, `dim_facility`, `dim_diagnosis`, `dim_medication`): overwritten (reference data, no history needed)
   - **Fact tables** (`fact_encounter`, `fact_claim`, `fact_prescription`): Delta MERGE on business key — updates existing rows, inserts new ones

#### Data Volumes Per Incremental Run

| Entity | New Rows | Notes |
|--------|----------|-------|
| Encounters | ~50 | All dated today |
| Claims | ~50 | One per encounter |
| Diagnoses | ~100–150 | 1 principal + 0–2 secondary per encounter |
| Prescriptions | ~75–100 | 1–3 per encounter based on diagnosis |
| Patients | ~2 new + 2–3 updates | Updates simulate address/insurance changes |

#### Steps

**Option A — Run from the Pipeline UI:**

1. Open **PL_Healthcare_Master** in your Fabric workspace
2. Click **Run** → set parameter `load_mode` = `incremental`
3. Wait ~10–12 minutes for the pipeline to complete

**Option B — Run the notebooks manually:**

1. Open **NB_Generate_Incremental_Data** → Run All  
   *(writes timestamped CSVs to `Files/incremental/YYYY-MM-DD/`)*
2. Open **PL_Healthcare_Full_Load** → Run with parameter `load_mode=incremental`  
   *(or run Bronze → Silver → Gold notebooks individually)*

#### Scheduling

To automate daily incremental loads, add a **Schedule trigger** to `PL_Healthcare_Master`:

1. Open the pipeline → **Schedule** (top toolbar)  
2. Set recurrence (e.g., daily at 6:00 AM)  
3. Add parameter: `load_mode` = `incremental`

#### Verifying Incremental Data

After an incremental run, check that new data flowed through:

```sql
-- Gold layer: count should increase by ~50 per run
SELECT COUNT(*) FROM lh_gold_curated.fact_encounter

-- SCD2: check for expired patient versions
SELECT patient_id, city, is_current, effective_end_date
FROM lh_gold_curated.dim_patient
WHERE is_current = 0
ORDER BY effective_end_date DESC
LIMIT 10
```

Repeat daily to build up a realistic data history showing trends over time in the Power BI dashboard.

## Configuration Options

Edit the top cell of `Healthcare_Launcher.ipynb`:

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_OWNER` | `rasgiza` | GitHub org or username (public repo — no token needed) |
| `GITHUB_REPO` | `Fabric-Payer-Provider-HealthCare-Demo` | Repository name |
| `GITHUB_BRANCH` | `main` | Branch to deploy from |
| `GITHUB_TOKEN` | `""` | Only needed if you fork to a private repo |
| `GENERATE_DATA` | `True` | Generate fresh synthetic data |
| `RUN_PIPELINE` | `True` | Run the full-load pipeline |
| `UPLOAD_KNOWLEDGE_DOCS` | `True` | Upload knowledge docs for AI agent |
| `DEPLOY_RTI` | `True` | Deploy Real-Time Intelligence (Eventhouse + scoring notebooks) |

## Prerequisites

- **Microsoft Fabric** workspace with **F64** or higher capacity
- User must be workspace **Admin** or **Member**
- Workspace should be **empty** (the launcher checks for this)
- Internet access to download from GitHub

## Repository Structure

```
├── Healthcare_Launcher.ipynb          # <- Import this into Fabric
├── ONTOLOGY_GRAPH_SETUP_GUIDE.md      # Manual ontology setup (10 entities, 15 relationships)
├── DATA_AGENT_GUIDE.md                # Agent instructions, routing, few-shots, knowledge base
├── POWERBI_DASHBOARD_GUIDE.md         # Power BI report pages, measures, Direct Lake tips
├── SAMPLE_QUESTIONS.md                # 60+ copy-paste questions for all agents
├── deployment.yaml                    # Optional: CI/CD config
├── README.md
├── workspace/                         # Fabric Git Integration format
│   ├── lh_bronze_raw.Lakehouse/
│   ├── lh_silver_stage.Lakehouse/
│   ├── lh_silver_ods.Lakehouse/
│   ├── lh_gold_curated.Lakehouse/
│   ├── 01_Bronze_Ingest_CSV.Notebook/
│   ├── 02_Silver_Stage_Clean.Notebook/
│   ├── 03_Silver_ODS_Enrich.Notebook/
│   ├── 06a_Create_Gold_Lakehouse_Tables.Notebook/
│   ├── 06b_Gold_Transform_Load_v2.Notebook/
│   ├── NB_Generate_Sample_Data.Notebook/
│   ├── NB_Generate_Incremental_Data.Notebook/
│   ├── NB_RTI_Event_Simulator.Notebook/
│   ├── NB_RTI_Setup_Eventhouse.Notebook/
│   ├── NB_RTI_Fraud_Detection.Notebook/
│   ├── NB_RTI_Care_Gap_Alerts.Notebook/
│   ├── NB_RTI_HighCost_Trajectory.Notebook/
│   ├── PL_Healthcare_Full_Load.DataPipeline/
│   ├── PL_Healthcare_Master.DataPipeline/
│   ├── HealthcareDemoHLS.SemanticModel/
│   └── HealthcareHLSAgent.DataAgent/
├── ontology/                          # Reference definition (used by guide, not auto-deployed)
│   └── Healthcare_Demo_Ontology_HLS/
├── healthcare_knowledge/              # AI agent knowledge base
│   ├── clinical_guidelines/
│   ├── compliance/
│   ├── denial_management/
│   ├── formulary/
│   ├── provider_network/
│   └── quality_measures/
└── scripts/                           # Build tools (not deployed)
    └── convert_from_source.py
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Workspace is not empty" | Create a new empty workspace, or set `allow_non_empty_workspace=True` in the config cell |
| Pipeline fails | Open PL_Healthcare_Master → check activity run details. Common cause: lakehouse tables not yet created |
| Semantic model shows no data | Run the pipeline first — it populates Gold lakehouse tables that the model reads |
| Data Agent returns generic answers | Ensure `healthcare_knowledge/` docs were uploaded to `lh_gold_curated/Files/` |
| Ontology not auto-deployed | By design — must be created in the UI from the semantic model. Follow [ONTOLOGY_GRAPH_SETUP_GUIDE.md](ONTOLOGY_GRAPH_SETUP_GUIDE.md) |
| `fabric-launcher` install fails | Ensure your Fabric capacity supports Python package installation |

## Credits

Built with:
- [fabric-launcher](https://pypi.org/project/fabric-launcher/) by Microsoft
- [fabric-cicd](https://pypi.org/project/fabric-cicd/) for artifact deployment
- Synthetic data generated with [Faker](https://faker.readthedocs.io/)
