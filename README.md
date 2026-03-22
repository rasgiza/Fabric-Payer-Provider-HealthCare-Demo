# Fabric-Payer-Provider-HealthCare-Demo

One-click deployment of a complete **Healthcare Payer/Provider Analytics** solution into Microsoft Fabric — no Python install, no `.env` files, no manual setup.

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
3. **Edit Cell 1** — set `GITHUB_OWNER` to your GitHub org/user  
   *(or leave defaults if using the public repo)*
4. **Run All** — wait ~15-20 minutes

That's it. The launcher deploys everything automatically.

## What Gets Deployed

| Layer | Items | Description |
|-------|-------|-------------|
| **Lakehouses (4)** | `lh_bronze_raw`, `lh_silver_stage`, `lh_silver_ods`, `lh_gold_curated` | Medallion architecture storage |
| **Notebooks (7)** | 5 ETL + `NB_Generate_Sample_Data` + `NB_Generate_Incremental_Data` | Spark-based data processing |
| **Pipelines (2)** | `PL_Healthcare_Full_Load`, `PL_Healthcare_Master` | Orchestration with full/incremental modes |
| **Semantic Model** | `HealthcareDemoHLS` | Star schema for Power BI (facts + dimensions) |
| **Data Agent** | `HealthcareHLSAgent` | Copilot AI agent with healthcare knowledge |
| **Ontology** | `Healthcare_Demo_Ontology_HLS` | GraphQL entity model — **manual UI setup** (see guide below) |

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

```
┌─────────────────────────────────────────────────────────┐
│  Healthcare_Launcher.ipynb                              │
│  (downloads repo → deploys artifacts → generates data   │
│   → runs pipeline → deploys ontology)                   │
└────────────────────────┬────────────────────────────────┘
                         │
    ┌────────────────────┼──────────────────────┐
    ▼                    ▼                      ▼
┌──────────┐     ┌──────────────┐      ┌──────────────┐
│ Lakehouse│     │  Notebooks   │      │  Pipelines   │
│  Bronze  │────▶│ 01_Bronze    │◀─────│ PL_Master    │
│  Silver  │     │ 02_Silver    │      │ PL_Full_Load │
│  Gold    │     │ 03_Gold      │      └──────────────┘
└──────────┘     └──────────────┘             │
                         │                     │
                         ▼                     ▼
                 ┌──────────────┐      ┌──────────────┐
                 │ Semantic     │      │ Data Agent   │
                 │ Model (TMDL) │◀─────│ (Copilot AI) │
                 └──────────────┘      └──────────────┘
```

## Deployment Flow

The launcher executes these stages in order:

1. **Install** `fabric-launcher` library
2. **Download** this GitHub repo as ZIP
3. **Deploy Stage 1** — Lakehouses (must exist before notebooks reference them)
4. **Deploy Stage 2** — Notebooks (must exist before pipelines reference them)
5. **Deploy Stage 3** — Data Pipelines
6. **Deploy Stage 4** — Semantic Model + Data Agent
7. **Upload** healthcare knowledge docs to `lh_gold_curated`
8. **Run** `NB_Generate_Sample_Data` — generates fresh synthetic data with today's dates
9. **Trigger** `PL_Healthcare_Master` with `load_mode=full` — runs Bronze → Silver → Gold ETL
10. **Print** ontology setup instructions — user follows the guide manually (~10 min)

## After Deployment

### Explore the Data
- Open **lh_gold_curated** → Tables → you'll see star schema tables (fact_encounters, dim_patients, etc.)
- Open **HealthcareDemoHLS** semantic model → create Power BI reports

### Sample Questions — Fabric Data Agent

Open **HealthcareHLSAgent** in your Fabric workspace. The Data Agent queries the Gold lakehouse star schema directly. Copy-paste any of these to get started:

#### Claim Denials & Revenue Cycle
| # | Question |
|---|----------|
| 1 | What is the overall claim denial rate and how does it break down by payer? |
| 2 | What are the top 5 denial reasons by claim count and total billed amount? |
| 3 | Which providers have the highest denial rates? Show the top 10 with their specialties. |
| 4 | Show me all denied claims over $50,000 — include the patient, payer, denial reason, and billed amount. |
| 5 | What is the total revenue at risk from claims flagged as high denial risk that haven't been denied yet? |
| 6 | Compare the collection rate (paid / billed) across all payers. Which payer reimburses the least? |
| 7 | How many claims are pending vs paid vs denied this month? Show the month-to-date trend. |

#### Readmissions & Patient Risk
| # | Question |
|---|----------|
| 8 | What is the 30-day readmission rate? How does it trend by month over the past year? |
| 9 | List the top 10 patients with the highest readmission risk scores. Include their age, insurance type, and number of prior encounters. |
| 10 | What is the readmission rate by encounter type (inpatient, outpatient, emergency)? |
| 11 | Which facilities have the highest readmission rates? |
| 12 | Show me the average length of stay for high-risk vs medium-risk vs low-risk readmission patients. |
| 13 | How many patients are in each readmission risk category (high, medium, low)? |

#### Medication Adherence
| # | Question |
|---|----------|
| 14 | How many patients are non-adherent (PDC < 0.8) for diabetes medications? |
| 15 | What is the average PDC score by drug class? Which therapeutic area has the worst adherence? |
| 16 | List patients who are on chronic medications and have PDC scores below 0.5 — include their drug class and gap days. |
| 17 | What is the adherent vs non-adherent member count for statin therapy? |
| 18 | Show the total medication cost by therapeutic area. Which drug class costs the most? |

#### Social Determinants of Health (SDOH)
| # | Question |
|---|----------|
| 19 | How many patients live in zip codes with a social vulnerability index above 0.75? |
| 20 | What is the average readmission risk score for patients in high SDOH risk tier vs low risk tier? |
| 21 | Show me zip codes flagged as food deserts — how many patients are in each? |
| 22 | What is the denial rate for patients in high-poverty zip codes vs low-poverty zip codes? |

#### Encounters & Providers
| # | Question |
|---|----------|
| 23 | What is the average length of stay by encounter type? |
| 24 | Which providers have the highest total charges? Show the top 10 with specialty and department. |
| 25 | What are the top 10 most frequent ICD diagnoses across all encounters? |
| 26 | How many encounters occurred this year by month? Show the trend. |
| 27 | Which patients have had the most encounters in the past 12 months? |

#### Cross-Domain Analytics
| # | Question |
|---|----------|
| 28 | Show me patients who were readmitted AND are non-adherent to their medications. Include their risk scores and drug class. |
| 29 | For patients in high SDOH risk zip codes, what is their average denial rate compared to the overall population? |
| 30 | Which chronic conditions have the highest readmission rates? Show the top 5 ICD categories with readmission counts. |

---

### Sample Questions — Azure AI Foundry Agent

If you've set up the optional **Foundry Orchestrator Agent** (see [FOUNDRY_IQ_SETUP_GUIDE.md](https://github.com/kwamesefah_microsoft/Healthcare-Data-Analytics-Repo/blob/main/FabricDemoHLS/FOUNDRY_IQ_SETUP_GUIDE.md)), it combines the Data Agent's live numbers with 21 clinical knowledge documents and web search. It provides richer, cited responses with clinical context. Copy-paste these:

#### Clinical Decision Support
| # | Question |
|---|----------|
| 1 | Which patients are at highest risk for readmission and what clinical interventions does the readmission prevention protocol recommend for each risk tier? |
| 2 | For our diabetic patients who are non-adherent to Metformin, what does the ADA stepwise therapy guideline recommend as next steps? |
| 3 | What CHF patients have a readmission risk score above 0.7 and what does the GDMT protocol recommend for their discharge planning? |
| 4 | Show me COPD patients who were readmitted within 30 days. What does the GOLD staging guideline say about their exacerbation management? |

#### Denial Management with Policy Context
| # | Question |
|---|----------|
| 5 | What are our top denial reasons and what does the Root Cause Analysis Framework say about corrective actions for each? |
| 6 | For claims denied due to missing prior authorization, what are the PA requirements by payer and what is the appeal success rate? |
| 7 | Show me the highest-value denied claims from BlueCross. What does the Appeal Process Guide recommend for Level 1 appeals? |
| 8 | What does the Clean Claim Checklist say we should verify before submitting emergency encounter claims? |

#### Quality Measures & Star Ratings
| # | Question |
|---|----------|
| 9 | What is our current medication adherence rate for the CMS Star triple-weighted measures (diabetes, RAS, statins) and how far are we from the 4-star cut point? |
| 10 | Based on our HEDIS measures data, which quality gaps should we prioritize to improve our Star Rating? |
| 11 | What is our estimated HRRP penalty exposure based on current readmission rates for CHF and COPD? Compare to the CMS penalty threshold. |

#### Population Health & SDOH
| # | Question |
|---|----------|
| 12 | For patients in food desert zip codes with high SVI, what SDOH-informed readmission prevention interventions does the protocol recommend? |
| 13 | Which patient populations should we target for care management outreach based on combined readmission risk, adherence gaps, and social vulnerability? |
| 14 | What does the clinical documentation standard require for E&M coding on high-complexity inpatient encounters, and are our providers meeting it? |

#### Formulary & Prescription Management
| # | Question |
|---|----------|
| 15 | Which patients are on non-formulary medications? What does the therapeutic interchange policy recommend as alternatives? |
| 16 | What are the step therapy requirements for our diabetic patients on GLP-1 agonists? Which payers require step therapy failure documentation? |
| 17 | Show me specialty drug authorization requirements for Insulin Glargine by payer. Which patients might need reauthorization soon? |

#### Provider Network & Contracts
| # | Question |
|---|----------|
| 18 | Which payers have the lowest reimbursement rates for our highest-volume CPT codes? What does the contract guide say about negotiation priorities? |
| 19 | Do we have any network adequacy gaps based on CMS time/distance standards? Which specialties are underserved? |
| 20 | Compare our collection rates against contracted rates by payer. Where are we seeing the most revenue leakage? |

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

### Run Incremental Loads
To simulate daily operational data arriving:

1. Open **NB_Generate_Incremental_Data** → Run All  
   *(generates ~50 new encounters, claims, prescriptions, diagnoses for today)*
2. Open **PL_Healthcare_Master** → Run with parameter `load_mode=incremental`

Repeat daily to build up a realistic data history.

## Configuration Options

Edit the top cell of `Healthcare_Launcher.ipynb`:

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_OWNER` | `kwame-one` | GitHub org or username |
| `GITHUB_REPO` | `Fabric-Payer-Provider-HealthCare-Demo` | Repository name |
| `GITHUB_BRANCH` | `main` | Branch to deploy from |
| `GITHUB_TOKEN` | `""` | GitHub PAT for private repos |
| `GENERATE_DATA` | `True` | Generate fresh synthetic data |
| `RUN_PIPELINE` | `True` | Run the full-load pipeline |
| `UPLOAD_KNOWLEDGE_DOCS` | `True` | Upload knowledge docs for AI agent |

## Prerequisites

- **Microsoft Fabric** workspace with **F64** or higher capacity
- User must be workspace **Admin** or **Member**
- Workspace should be **empty** (the launcher checks for this)
- Internet access to download from GitHub

## Repository Structure

```
├── Healthcare_Launcher.ipynb          # ← Import this into Fabric
├── ONTOLOGY_GRAPH_SETUP_GUIDE.md      # Manual ontology setup (10 entities, 15 relationships)
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
