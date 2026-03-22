# Fabric-Payer-Provider-HealthCare-Demo

One-click deployment of a complete **Healthcare Payer/Provider Analytics** solution into Microsoft Fabric — no Python install, no `.env` files, no manual setup.

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

### Ask the AI Agent
Open **HealthcareHLSAgent** and try:
- *"What are the top 5 denial reasons by claim volume?"*
- *"Show me readmission risk by facility"*
- *"Which providers have the highest average charges?"*
- *"Compare claim denial rates across payers"*

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
