# Foundry IQ — Healthcare Orchestrator Agent Setup Guide

> **Complete step-by-step guide** to deploy the Healthcare Intelligence Orchestrator Agent that combines a **Knowledge Base** (unstructured healthcare documents) with a **Fabric Data Agent** (structured Lakehouse data) in Azure AI Foundry.
>
> This guide covers every automated and **manual** step required for a working end-to-end deployment, including managed identity configuration, model deployment, and Fabric Data Agent wiring — all of which are common failure points.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Step 1 — Create Azure AI Foundry Resources](#step-1--create-azure-ai-foundry-resources)
4. [Step 2 — Deploy Required Models](#step-2--deploy-required-models)
5. [Step 3 — Create and Configure Azure AI Search](#step-3--create-and-configure-azure-ai-search)
6. [Step 4 — Assign RBAC Roles (Critical)](#step-4--assign-rbac-roles-critical)
7. [Step 5 — Connect Search Service to Foundry](#step-5--connect-search-service-to-foundry)
8. [Step 6 — Create the Knowledge Source (OneLake)](#step-6--create-the-knowledge-source-onelake)
9. [Step 7 — Create the Knowledge Base](#step-7--create-the-knowledge-base)
10. [Step 8 — Verify the Indexer](#step-8--verify-the-indexer)
11. [Step 9 — Configure the Fabric Data Agent (MANUAL)](#step-9--configure-the-fabric-data-agent-manual)
12. [Step 10 — Connect the Fabric Data Agent to Foundry (MANUAL)](#step-10--connect-the-fabric-data-agent-to-foundry-manual)
13. [Step 11 — Grant Managed Identities Access (Critical)](#step-11--grant-managed-identities-access-critical)
14. [Step 12 — Create the Orchestrator Agent](#step-12--create-the-orchestrator-agent)
15. [Step 13 — Test & Validate](#step-13--test--validate)
16. [Manual Steps Checklist](#manual-steps-checklist)
17. [Troubleshooting](#troubleshooting)
18. [Resource Reference](#resource-reference)

---

## 1. Architecture Overview

```
User Question
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│           HealthcareOrchestratorAgent2 (gpt-4.1)             │
│  ┌───────────────────────────────────────────────────────┐   │
│  │  Orchestrator Instructions (v24)                      │   │
│  │  • Mandatory Decomposition Protocol (5 steps)         │   │
│  │  • Query Catalog (35+ exact phrasings)                │   │
│  │  • Citation Protocol & Deep Response Protocol         │   │
│  │  • 17 Critical Rules incl. Pass-Through Rule          │   │
│  └───────────────────────────────────────────────────────┘   │
├──────────────┬──────────────────────┬────────────────────────┤
│ azure_ai_    │ fabric_dataagent_    │ web_search_            │
│ search       │ preview              │ preview                │
│ (Grounding)  │ (Tool)               │ (Tool)                 │
├──────────────┼──────────────────────┼────────────────────────┤
│ AI Search    │ Fabric Data Agent    │ Bing                   │
│ Index        │ HealthcareHLSAgent   │                        │
│ 11,316 docs  │ lh_gold_curated      │                        │
│              │ (12-table star       │                        │
│              │  schema)             │                        │
└──────────────┴──────────────────────┴────────────────────────┘
     │                   │
     ▼                   ▼
 healthcare_knowledge/   Gold Lakehouse Tables
 (21 markdown files      (dim_patient, dim_provider,
  in OneLake)             fact_encounter, fact_claim,
                          fact_prescription, agg_medication_
                          adherence, etc.)
```

### How It Works

| Question Type | Tool Used | Example |
|---|---|---|
| Policy/guideline/protocol | `azure_ai_search` (Knowledge Base grounding) | "What does our appeal process recommend?" |
| Data/metrics/counts/trends | Fabric IQ (`fabric_iq_preview`) → published `HealthcareHLSAgent` | "Show me denial rates by payer" |
| Combined questions | Both tools, then synthesized | "Show recommendations for Nancy White based on her adherence data and clinical guidelines" |
| External/current regulations | `web_search_preview` | "What are the latest CMS HRRP thresholds?" |

### Dual-Path Architecture

Users can query the same data from **two entry points** with consistent results:

| Entry Point | Path | Use Case |
|---|---|---|
| **Fabric UI** | User → Data Agent → lh_gold_curated | Quick data exploration, testing queries |
| **Foundry Agent** | User → Orchestrator → Data Agent → lh_gold_curated + KB | Full clinical intelligence with guidelines |

> **Important**: Both paths must return identical data for the same question. This is enforced by aggregation rules on the Data Agent and a pass-through rule on the orchestrator (see Steps 9 and 12).

---

## 2. Prerequisites

| Requirement | Details |
|---|---|
| **Azure Subscription** | With permissions to create AI Services, AI Search, and role assignments |
| **Microsoft Fabric Workspace** | With a populated Gold Lakehouse (star schema tables) |
| **Fabric Data Agent** | Already created in the Fabric workspace (deployed by the launcher) |
| **Healthcare Knowledge Files** | Markdown/text files uploaded to a Fabric Lakehouse (deployed by the launcher) |
| **Azure CLI** | Installed and logged in (`az login`) |

### Required Azure Resource Providers
Ensure these are registered in your subscription:
```powershell
az provider register --namespace Microsoft.CognitiveServices
az provider register --namespace Microsoft.Search
```

---

## Step 1 — Create Azure AI Foundry Resources

### 1.1 Create via Azure Portal

1. Go to [Azure AI Foundry Portal](https://ai.azure.com)
2. Click **+ Create project**
3. Fill in:
   - **Project name**: e.g., `HealthcareDemo-HLS`
   - **Hub**: Create new or select existing
     - **Hub name**: e.g., `HLS-HealthcareDemo`
     - **Subscription**: Your subscription
     - **Resource group**: e.g., `healthcaredemofoundry-rg`
     - **Region**: e.g., `East US 2`
   - This auto-creates an **AI Services** account with the same name as the hub
4. Click **Create**

### 1.2 Note Your Resource Details

After creation, record these values -- you'll need them throughout:

| Value | Where to Find | Example |
|---|---|---|
| **AI Services account name** | Azure Portal --> Resource Group --> AI Services | `HLS-HealthcareDemo` |
| **Project name** | Foundry Portal --> Project Settings | `HealthcareDemo-HLS` |
| **Foundry endpoint** | Portal --> Project --> Overview | `https://<account>.services.ai.azure.com/api/projects/<project>` |
| **Foundry project MSI** | Azure Portal --> AI Services --> Identity --> Object ID | `<your-foundry-project-msi>` |
| **Resource Group** | Azure Portal | `healthcaredemofoundry-rg` |
| **Subscription ID** | Azure Portal | `<your-subscription-id>` |

---

## Step 2 — Deploy Required Models

In the Foundry portal, go to **Models + Endpoints** --> **+ Deploy model**:

### 2.1 Deploy gpt-4.1 (for agent chat)
- Model: **gpt-4.1**
- Deployment name: `gpt-4.1`
- Version: Latest
- Tokens per minute: 80K+ recommended

### 2.2 Deploy text-embedding-ada-002 (for search embeddings)
- Model: **text-embedding-ada-002**
- Deployment name: `text-embedding-ada-002`
- Version: 2
- Tokens per minute: 120K+ recommended

> **Important**: The embedding model is required for the Knowledge Base indexer to vectorize documents.

---

## Step 3 — Create and Configure Azure AI Search

### 3.1 Create the Search Service

1. Azure Portal --> **Create a resource** --> **Azure AI Search**
2. Configure:
   - **Service name**: e.g., `healthcarefoundryais`
   - **Resource group**: Same as Foundry (`healthcaredemofoundry-rg`)
   - **Location**: Same region as Foundry
   - **Pricing tier**: **Basic** minimum (Free tier doesn't support managed identity)
3. Click **Create**

### 3.2 Enable System Managed Identity

1. Go to the Search service --> **Identity** (left menu)
2. Set **System assigned** to **On**
3. Click **Save**
4. **Record the Object ID** -- this is the Search MSI (e.g., `<your-search-msi-object-id>`)

### 3.3 Set Authentication Mode

1. Go to Search service --> **Settings** --> **Keys**
2. Set **API access control** to **Both** (allows both API keys AND RBAC/Entra ID auth)
3. Click **Save**

> **Why "Both"?** Foundry IQ connects using Entra ID (RBAC), but having keys available is useful for debugging.

---

## Step 4 — Assign RBAC Roles (Critical)

This is the most important step. Missing roles cause indexer failures, 401 errors, and permission denied errors.

### 4.1 Roles on the AI Search Service

Assign these roles to **both** your user account AND the Search service's managed identity:

```powershell
# Variables -- replace with your values
$searchScope = "/subscriptions/<SUB_ID>/resourceGroups/<RG>/providers/Microsoft.Search/searchServices/<SEARCH_NAME>"
$userObjectId = "<YOUR_USER_OBJECT_ID>"
$searchMsiObjectId = "<SEARCH_MSI_OBJECT_ID>"

# --- Roles for YOUR USER ---
az role assignment create --assignee $userObjectId --role "Search Index Data Contributor" --scope $searchScope
az role assignment create --assignee $userObjectId --role "Search Index Data Reader" --scope $searchScope
az role assignment create --assignee $userObjectId --role "Search Service Contributor" --scope $searchScope

# --- Roles for SEARCH MSI ---
az role assignment create --assignee $searchMsiObjectId --role "Search Index Data Contributor" --scope $searchScope
az role assignment create --assignee $searchMsiObjectId --role "Search Index Data Reader" --scope $searchScope
az role assignment create --assignee $searchMsiObjectId --role "Search Service Contributor" --scope $searchScope
```

### 4.2 Roles on the AI Services Account (for Embeddings)

The Search MSI needs to call the embedding model during indexing:

```powershell
$aiServicesScope = "/subscriptions/<SUB_ID>/resourceGroups/<RG>/providers/Microsoft.CognitiveServices/accounts/<AI_SERVICES_NAME>"

# Search MSI needs these to call the embedding model
az role assignment create --assignee $searchMsiObjectId --role "Cognitive Services OpenAI User" --scope $aiServicesScope
az role assignment create --assignee $searchMsiObjectId --role "Cognitive Services OpenAI Contributor" --scope $aiServicesScope
```

> **Without these roles**, the indexer will fail with: `PermissionDenied -- The API deployment for this resource does not exist`

### 4.3 Roles on the Fabric Workspace

The Search MSI needs access to read OneLake data:

```powershell
# Option A: Add Search MSI as Contributor to Fabric workspace via REST API
$fabricToken = az account get-access-token --resource "https://api.fabric.microsoft.com" --query accessToken -o tsv
$workspaceId = "<FABRIC_WORKSPACE_ID>"

$body = @{
    identifier = $searchMsiObjectId
    groupUserAccessRight = "Contributor"
    principalType = "App"
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://api.fabric.microsoft.com/v1/workspaces/$workspaceId/users" `
    -Headers @{"Authorization"="Bearer $fabricToken"; "Content-Type"="application/json"} `
    -Method POST -Body $body
```

> **Alternative**: In the Fabric portal, go to Workspace --> Manage access --> Add the Search MSI Object ID as Contributor.

### 4.4 Summary of All Role Assignments

| Principal | Resource | Role(s) |
|---|---|---|
| Your User | AI Search Service | Search Index Data Contributor, Reader, Service Contributor |
| Search MSI | AI Search Service | Search Index Data Contributor, Reader, Service Contributor |
| Search MSI | AI Services Account | Cognitive Services OpenAI User, Cognitive Services OpenAI Contributor |
| Search MSI | Fabric Workspace | Contributor |

> **Tip**: Role assignments can take **5-10 minutes** to propagate. Wait before proceeding.

---

## Step 5 — Connect Search Service to Foundry

1. In the **Foundry portal**, go to your project
2. Click **Management center** (bottom left) --> **Connected resources**
3. Click **+ New connection**
4. Select **Azure AI Search**
5. Find your search service
6. **Authentication type**: Select **Microsoft Entra ID** (NOT API Key)
7. Click **Connect**

> **Why Entra ID?** This allows Foundry to use managed identity for auth, which is required for Knowledge Base operations.

---

## Step 6 — Create the Knowledge Source (OneLake)

### 6.1 Upload Healthcare Knowledge Files

The Healthcare Launcher (Cell 6) automatically uploads `healthcare_knowledge/` files to your Lakehouse. The folder structure is:

```
healthcare_knowledge/
├── clinical_guidelines/
│   ├── chf_management.md
│   ├── copd_management.md
│   ├── diabetes_management.md
│   └── preventive_care.md
├── compliance/
│   ├── audit_readiness.md
│   ├── hipaa_compliance.md
│   └── regulatory_reporting.md
├── denial_management/
│   ├── appeal_procedures.md
│   ├── common_denial_codes.md
│   └── prevention_strategies.md
├── formulary/
│   ├── drug_formulary_tiers.md
│   ├── prior_authorization.md
│   └── step_therapy_protocols.md
├── provider_network/
│   ├── contract_terms.md
│   ├── credentialing_requirements.md
│   └── network_adequacy.md
└── quality_measures/
    ├── cms_star_ratings.md
    ├── hedis_measures.md
    └── patient_satisfaction.md
```

### 6.2 Create the Knowledge Source

1. In Foundry portal --> **Knowledge** (left sidebar)
2. Click **+ Add knowledge source**
3. Select **OneLake**
4. Configure:
   - **Name**: e.g., `healthcare-onelake-ks`
   - **Fabric Workspace**: Select your workspace
   - **Lakehouse**: Select your lakehouse
   - **Folder path**: `Files/healthcare_knowledge` (or wherever your files are)
   - **Search connection**: Select the search service connected in Step 5
   - **Embedding model**: `text-embedding-ada-002`
5. Click **Create**

Wait for the status to change from **Creating** --> **Active** (may take 5-15 minutes).

---

## Step 7 — Create the Knowledge Base

1. In Foundry portal --> **Knowledge** --> **Knowledge bases** tab
2. Click **+ Create knowledge base**
3. Configure:
   - **Name**: `healthcareknowledgebase`
   - **Model**: `gpt-4.1`
   - **Knowledge sources**: Select `healthcare-onelake-ks`
   - **Retrieval reasoning effort**: `Medium`
4. Set **Answer Instructions**:
   ```
   You are a healthcare knowledge expert. Answer questions using the provided healthcare
   knowledge documents. Always cite the source document name. If the answer is not in the
   knowledge base, say so clearly. Structure responses with clear headings and bullet points.
   ```
5. Set **Retrieval Instructions**:
   ```
   Search across all healthcare knowledge domains including clinical guidelines, compliance
   policies, denial management procedures, formulary rules, provider network requirements,
   and quality measures. Return the most relevant passages. Include related information from
   adjacent domains when helpful.
   ```
6. Click **Create**

---

## Step 8 — Verify the Indexer

### 8.1 Check Indexer Status

1. Go to **Azure Portal** --> your **AI Search service**
2. Click **Indexers** in the left menu
3. Find the indexer created for your knowledge source (e.g., `healthcare-onelake-ks-indexer`)
4. Check:
   - **Status**: Should be **Success**
   - **Docs Succeeded**: Should be > 0 (our setup indexed 11,316 documents)
   - **Docs Failed**: Should be 0

### 8.2 If Indexer Fails

**Common failure: `PermissionDenied` on embeddings**

The error looks like:
```
Error with status code InternalServerError: PermissionDenied -
The API deployment for this resource does not exist.
```

**Fix**: Ensure the Search MSI has `Cognitive Services OpenAI User` and `Cognitive Services OpenAI Contributor` roles on the AI Services account (see Step 4.2). Then **Reset** and **Run** the indexer.

**To reset and re-run via CLI:**
```powershell
$searchName = "<SEARCH_SERVICE_NAME>"
$indexerName = "<INDEXER_NAME>"
$searchKey = "<SEARCH_ADMIN_KEY>"  # Get from Azure Portal --> Search --> Keys

# Reset the indexer
Invoke-RestMethod -Uri "https://$searchName.search.windows.net/indexers/$indexerName/reset?api-version=2024-07-01" `
    -Headers @{"api-key"=$searchKey; "Content-Type"="application/json"} -Method POST

# Run the indexer
Invoke-RestMethod -Uri "https://$searchName.search.windows.net/indexers/$indexerName/run?api-version=2024-07-01" `
    -Headers @{"api-key"=$searchKey; "Content-Type"="application/json"} -Method POST
```

### 8.3 Check Index Contents

```powershell
# Check document count in the index
Invoke-RestMethod -Uri "https://$searchName.search.windows.net/indexes/$indexName/docs/`$count?api-version=2024-07-01" `
    -Headers @{"api-key"=$searchKey}
```

---

## Step 9 — Configure the Fabric Data Agent (MANUAL)

> **⚠️ This is a MANUAL step** — must be done in the Fabric portal UI.

The Healthcare Launcher deploys the Data Agent item, but you must verify it has:
1. Data sources attached
2. AI instructions configured
3. Aggregation rules for consistent results

### 9.1 Verify Data Sources

1. Go to [Fabric Portal](https://app.fabric.microsoft.com)
2. Open your workspace (e.g., "healthcare demo test2")
3. Click the **HealthcareHLSAgent** item (type: Data Agent)
4. In the left panel under **Data**, verify you see:
   - **HealthcareDemoHLS** (semantic model) — AND/OR
   - **lh_gold_curated** (lakehouse) with Schemas expanded

> **Common Failure**: If the Data Agent definition is empty (`null`), the agent returns no data. Click **Add Data** → select your lakehouse → **Publish**.

### 9.2 Set AI Instructions

1. In the Data Agent editor, click **"Agent instructions"** (top toolbar)
2. Paste the full AI instructions from [`DATA_AGENT_INSTRUCTIONS.md`](DATA_AGENT_INSTRUCTIONS.md) Section 1a
3. Also set the **Data Source Instructions** on `lh_gold_curated` from Section 1b

### 9.3 Add Aggregation Rules (Critical for Consistency)

Add this to the **AI Instructions** (append after the existing content):

```
AGGREGATION RULES:
1. Always aggregate results to the most meaningful summary level unless the user
   explicitly asks for "all rows", "details", "raw data", or "fill history".
2. For medication adherence by drug class: return ONE row per drug class with the
   AVERAGE PDC across all prescriptions in that class. Do NOT return individual
   prescription rows.
3. For providers assigned to a patient: return DISTINCT provider_name and specialty
   only. Do NOT include encounter_type or role unless explicitly asked.
4. For encounters: return summary counts/averages by encounter_type unless individual
   encounters are requested.
5. For claims/denials: return aggregated rates by payer or denial_reason unless
   individual claims are requested.
6. Do NOT return multiple rows for the same entity (e.g., multiple prescriptions
   within the same drug class, or the same provider listed multiple times with
   different encounter types).
7. Order results alphabetically by the primary grouping column (drug_class, specialty,
   payer_name, etc.).
```

> **Why?** Without these rules, the Data Agent returns row-level data when called from Foundry (e.g., every prescription row instead of one row per drug class), while the Fabric UI test returns aggregated data. This causes users to see different results from the two entry points.

### 9.4 Test in Fabric UI

Before connecting to Foundry, test directly in the Data Agent:
1. In the Data Agent editor, use the **"Test the agent's responses"** panel
2. Try: `Show me medication adherence for Nancy White age 63 by drug class`
3. Verify you get ONE row per drug class with a single PDC score
4. Try: `Show me which providers are assigned to patient Nancy White`
5. Verify you get DISTINCT providers with specialty only

### 9.5 Publish

Click **Publish** in the top toolbar to make the Data Agent available for external connections.

### 9.6 Note the Data Agent URL

The Data Agent URL is visible in the browser address bar:
```
https://app.fabric.microsoft.com/groups/<WORKSPACE_ID>/aiskills/<ARTIFACT_ID>?experience=fabric-developer
```

Record both values:

| Value | Location in URL | Example |
|---|---|---|
| **Workspace ID** | After `/groups/` | `d6ed5901-0f1d-4a5c-a263-e5f857169a79` |
| **Artifact ID** | After `/aiskills/` | `4801f1cc-e42f-466e-a506-95b65bd87f9b` |

---

## Step 10 — Connect the Published Data Agent through Fabric IQ (MANUAL)

> **Product migration (October 2026):** Microsoft replaced the earlier
> `fabric_dataagent_preview` integration with the Fabric IQ tool. Keep the
> existing published `HealthcareHLSAgent`; do not rebuild it or change its data
> sources just for this migration.

### 10.1 Add Fabric IQ from the OneLake Catalog

1. Go to [Microsoft Foundry](https://ai.azure.com) and open the project.
2. Open the orchestrator agent. For a first deployment, create a temporary
   prompt agent or toolbox so the project connection can be established before
   running the repository deployment script.
3. Under **Tools**, select **Add** → **Browse all tools**.
4. Select **Fabric IQ (OneLake Catalog)**, then select **Add tool**.
5. In the OneLake Catalog, filter the item type to **Data agent**.
6. Select the published `HealthcareHLSAgent`, then select **Add**.
7. Remove the old **Microsoft Fabric data agent** tool from the Foundry agent.
8. Save a new Foundry agent version.

The selected item resolves to this Fabric IQ MCP endpoint:

```text
https://api.fabric.microsoft.com/v1/mcp/workspaces/<WORKSPACE_ID>/dataagents/<DATA_AGENT_ID>/agent
```

Using the Data Agent endpoint preserves its instructions, examples, data
sources, and support for long-running queries. A direct ontology endpoint is a
different Fabric IQ target and should not replace `HealthcareHLSAgent` in this
orchestrator unless that routing change is intentional.

### 10.2 Recommended Toolbox Option

Microsoft recommends adding Fabric IQ through a **toolbox** when the same tool
will be reused across agents or runtimes. A toolbox centralizes credentials,
versioning, and policy enforcement. Direct tool configuration remains valid for
this single-agent demo.

### 10.3 Verify the Fabric IQ Tool

Confirm all of the following before testing:

1. `HealthcareHLSAgent` is published in Fabric.
2. The connection identity can read the Data Agent and each of its data sources.
3. The Fabric IQ target is the Data Agent endpoint above, not the ontology or
   Power BI endpoint.
4. The Foundry agent has `fabric_iq_preview` and no longer has
   `fabric_dataagent_preview`.
5. The agent instructions identify the route as
   **Fabric IQ — HealthcareHLSAgent**.

For delegated access, the Data Agent connection requires
`DataAgent.Execute.All`. Direct clients of the published Data Agent MCP endpoint
can also use a user or service-principal token.

---

## Step 11 — Grant Managed Identities Access (Critical)

> **⚠️ Multiple identities need access.** Missing any one causes authorization failures.

### 11.1 Identify the Three Managed Identities

| Identity | What It Is | Where to Find |
|---|---|---|
| **Foundry Hub MSI** | System-assigned managed identity of the AI Services account | Azure Portal → AI Services → Identity → Object ID |
| **Search MSI** | System-assigned managed identity of the AI Search service | Azure Portal → AI Search → Identity → Object ID |
| **Your User** | Your Entra ID user account | `az ad signed-in-user show --query id -o tsv` |

```powershell
# Find Foundry Hub MSI
$hub = az cognitiveservices account show --name <AI_SERVICES_NAME> --resource-group <RG> | ConvertFrom-Json
Write-Host "Foundry Hub MSI: $($hub.identity.principalId)"

# Find Search MSI
$search = az search service show --name <SEARCH_NAME> --resource-group <RG> | ConvertFrom-Json
Write-Host "Search MSI: $($search.identity.principalId)"
```

> **Note**: The orchestrator agent also creates its own managed identity (visible in the agent API response as `identity.instance_identity.principal_id`), but this identity may take **hours** to propagate in Entra ID. The Foundry Hub MSI is what actually authenticates to Fabric.

### 11.2 Grant Access to Fabric Workspace

The **Foundry Hub MSI** and **Search MSI** both need **Contributor** access to the Fabric workspace:

**Option A — Fabric Portal UI (recommended)**:

1. Go to [Fabric Portal](https://app.fabric.microsoft.com)
2. Open your workspace → click **Manage access** (top right)
3. Click **+ Add people or groups**
4. Search for:
   - The **AI Services account name** (e.g., `HLS-HealthcareDemo`) — add as **Contributor**
   - The **Search service name** (e.g., `healthcarefoundryais`) — add as **Contributor**
5. Click **Add**

**Option B — REST API**:

```powershell
$fabricToken = az account get-access-token --resource "https://api.fabric.microsoft.com" --query accessToken -o tsv
$fabricHeaders = @{"Authorization"="Bearer $fabricToken"; "Content-Type"="application/json"}
$workspaceId = "<FABRIC_WORKSPACE_ID>"

# Grant Foundry Hub MSI
$body = @{
    principal = @{ id = "<FOUNDRY_HUB_MSI>"; type = "ServicePrincipal" }
    role = "Contributor"
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Uri "https://api.fabric.microsoft.com/v1/workspaces/$workspaceId/roleAssignments" `
    -Headers $fabricHeaders -Method POST -Body $body

# Grant Search MSI
$body2 = @{
    principal = @{ id = "<SEARCH_MSI>"; type = "ServicePrincipal" }
    role = "Contributor"
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Uri "https://api.fabric.microsoft.com/v1/workspaces/$workspaceId/roleAssignments" `
    -Headers $fabricHeaders -Method POST -Body $body2
```

### 11.3 Verify Workspace Roles

```powershell
$roles = Invoke-RestMethod -Uri "https://api.fabric.microsoft.com/v1/workspaces/$workspaceId/roleAssignments" `
    -Headers $fabricHeaders -Method GET
$roles.value | ForEach-Object {
    Write-Host "$($_.principal.id) - $($_.role) - $($_.principal.type)"
}
```

**Expected**: You should see at least 3 entries:

| Principal | Role | Type |
|---|---|---|
| Your User ID | Admin | User |
| Foundry Hub MSI | Contributor | ServicePrincipal |
| Search MSI | Contributor | ServicePrincipal |

### 11.4 Grant Search MSI Access to AI Services (for Embeddings)

```powershell
$aiServicesScope = "/subscriptions/<SUB_ID>/resourceGroups/<RG>/providers/Microsoft.CognitiveServices/accounts/<AI_SERVICES_NAME>"
$searchMsiObjectId = "<SEARCH_MSI>"

az role assignment create --assignee $searchMsiObjectId --role "Cognitive Services OpenAI User" --scope $aiServicesScope
az role assignment create --assignee $searchMsiObjectId --role "Cognitive Services OpenAI Contributor" --scope $aiServicesScope
```

### 11.5 RBAC Propagation Wait

> **⚠️ Role assignments can take 5-15 minutes to propagate.** Do not proceed to testing until you have waited. If you get `PrincipalNotFound` errors when assigning roles via API, the managed identity hasn't propagated in Entra ID yet — try again in the Fabric UI by searching for the resource name instead of Object ID.

---

## Step 12 — Create the Orchestrator Agent

### 12.1 Create via Foundry Portal

1. In [Azure AI Foundry](https://ai.azure.com) → your project
2. Click **Agents** (left sidebar)
3. Click **+ New agent**
4. Set:
   - **Name**: `HealthcareOrchestratorAgent2`
   - **Model**: `gpt-4.1`

### 12.2 Set Agent Instructions

Paste the full instructions from [`foundry_agent/orchestrator_instructions.md`](foundry_agent/orchestrator_instructions.md).

> **Important**: The production instructions contain 17 Critical Rules, a Query Catalog with 35+ exact phrasings, and the Mandatory Decomposition Protocol. Using abbreviated instructions will cause the agent to send compound questions to the Data Agent, which silently fail.

### 12.3 Add Tools

Add these three tools:

1. **Web Search**: Click the ⋮ menu → **Add tool** → **Web Search** → Enable
2. **Fabric IQ**: Click **Add tool** → **Fabric IQ (OneLake Catalog)** → filter by **Data agent** → select the published `HealthcareHLSAgent` from Step 10
3. **Azure AI Search** (Knowledge Base grounding): This is added as **Knowledge**, not a tool:
   - Scroll to the **Knowledge** section
   - Click **Add**
   - Select your Knowledge Base index (e.g., `healthcare-onelake-ks-index`)
   - Select the AI Search connection (e.g., `healthcarefoundryaisde67rm`)

> **⚠️ CRITICAL**: Add the Knowledge Base as **grounding** (in the Knowledge section), NOT as an MCP tool. Adding it as an MCP tool causes a `server_authentication` error that the API doesn't support.

### 12.4 Model Configuration

> **⚠️ MANUAL STEP**: If you need to change the GPT model:

1. In the agent editor, click the **Model** dropdown at the top
2. Select the desired model (recommended: `gpt-4.1`)
3. The model must be **already deployed** in your Foundry project (see Step 2)

**Model considerations:**

| Model | Pros | Cons |
|---|---|---|
| `gpt-4.1` | Tested with this repository and follows the multi-tool instructions | Check availability in your region |
| `gpt-4o` | Compatible fallback | Older deployment |
| `gpt-4o-mini` | Fast, lower cost | May skip multi-call and citation requirements |

> **Recommendation**: Use `gpt-4.1`, which is the model validated by the
> repository deployment and live smoke test.

### 12.5 Deploy from the Repository (Recommended)

Use `azure-ai-projects>=2.2.0` and replace the old
`fabric_dataagent_preview` payload with `FabricIQPreviewTool`:

This repository includes a ready-to-run deployment script:

```powershell
python -m pip install -r foundry_agent\requirements.txt

$env:FOUNDRY_PROJECT_ENDPOINT = "https://<account>.services.ai.azure.com/api/projects/<project>"
$env:FOUNDRY_MODEL_NAME = "gpt-4.1"
$env:FABRIC_IQ_CONNECTION_NAME = "HealthcareHLSAgent"
$env:AZURE_AI_SEARCH_CONNECTION_NAME = "<search-connection-name>"
$env:AZURE_AI_SEARCH_INDEX_NAME = "healthcare-onelake-ks-index"

python foundry_agent\deploy_foundry_agent.py --list-connections
python foundry_agent\deploy_foundry_agent.py --validate-only
python foundry_agent\deploy_foundry_agent.py
```

The Fabric IQ project connection must first be created by selecting the
published Data Agent in OneLake Catalog. The preflight resolves connections by
name in the user's project, verifies the model, rejects deprecated
`fabric_dataagent_preview` connections, verifies the Fabric IQ target is a
published Data Agent endpoint, and requires the Azure AI Search grounding
connection. A successful deployment always contains:

```text
web_search_preview, azure_ai_search, fabric_iq_preview
```

See [`foundry_agent/README.md`](foundry_agent/README.md) for the portable
deployment workflow and `deployment.env.example` for the required values.

For reusable deployments, create a toolbox containing a
`fabric_iq_preview` tool with the Data Agent `server_url`, then attach the
published toolbox endpoint to the agent as an MCP tool. See
[Connect agents to Microsoft Fabric with Fabric IQ](https://learn.microsoft.com/azure/foundry/agents/how-to/tools/fabric-iq).

### 12.6 Save the Agent

Click **Save** in the Foundry portal to save the agent configuration.

---

## Step 13 — Test & Validate

### 13.1 Test Fabric IQ with the Data Agent

In the Foundry agent **Playground**, ask:

```
Show me medication adherence for Nancy White age 63 by drug class
```

**Expected**: A table with one row per drug class, each with a single PDC score. Should match results from the Fabric UI test exactly.

**If Fabric IQ returns no result**: Verify the checks in Step 10.3, then test
the same question directly in the published Data Agent to isolate whether the
failure is in Fabric or the Foundry integration.

### 13.2 Test Knowledge Base (Guidelines)

```
What does our readmission prevention protocol recommend for high-risk patients?
```

**Expected**: A response citing specific documents (e.g., `Readmission_Prevention_Protocol.md`), section numbers, and external references (e.g., LACE Index, CMS HRRP).

**If you get a 403 error**: The Knowledge Base was added as an MCP tool instead of grounding — go back to Step 12.3.

### 13.3 Test Combined Query (Both Tools)

```
What are the recommendations for Nancy White age 63 based on her medication adherence and clinical guidelines?
```

**Expected**: The agent should:
1. Call Fabric IQ — `HealthcareHLSAgent` for PDC scores by drug class
2. Call Fabric IQ — `HealthcareHLSAgent` for assigned providers
3. Use `azure_ai_search` (KB grounding) for clinical guidelines
4. Synthesize a response with tables, citations, and provider routing

### 13.4 Validate Data Consistency

Ask the **same question** in both:
- Fabric Data Agent (in Fabric UI)
- Foundry Orchestrator (in Foundry Playground)

**The data values (PDC scores, provider names, etc.) must match.** Formatting may differ (table vs. bullet list), but the numbers must be identical.

---

## Manual Steps Checklist

These steps **cannot be automated** and must be done manually in the portal UIs:

| # | Step | Where | What |
|---|---|---|---|
| 1 | Deploy gpt-4.1 and embedding models | Foundry portal → Models + Endpoints | Deploy models needed by the agent and indexer |
| 2 | Enable Search managed identity | Azure Portal → AI Search → Identity | Turn on System Assigned identity |
| 3 | Configure Data Agent data sources | Fabric portal → Data Agent → Add Data | Attach lh_gold_curated lakehouse |
| 4 | Set Data Agent AI instructions | Fabric portal → Data Agent → Agent Instructions | Paste from DATA_AGENT_INSTRUCTIONS.md |
| 5 | Add Data Agent aggregation rules | Fabric portal → Data Agent → Agent Instructions | Append aggregation rules (Step 9.3) |
| 6 | Publish Data Agent | Fabric portal → Data Agent → Publish | Make available for external connections |
| 7 | Add Fabric IQ Data Agent tool | Foundry portal → Agent → Add tool → Fabric IQ | Select the published Data Agent from OneLake Catalog |
| 8 | Grant Foundry Hub MSI to Fabric workspace | Fabric portal → Workspace → Manage Access | Add AI Services account as Contributor |
| 9 | Add Knowledge Base as grounding (NOT MCP) | Foundry portal → Agent → Knowledge section | Add azure_ai_search index |
| 10 | Set/change GPT model | Foundry portal → Agent → Model dropdown | Select gpt-4.1 (must be deployed first) |

---

## Troubleshooting

### Error: Fabric IQ returns no Data Agent result

**Cause**: The Data Agent might be unpublished, its source might be
unavailable, the connection identity might lack access, or Fabric IQ might be
targeting the wrong Fabric item type.

**Fix**:
1. Open the Data Agent in Fabric and verify `lh_gold_curated` is available.
2. Test the same question directly in the Data Agent.
3. Publish the Data Agent after any configuration changes.
4. Verify the Fabric IQ selection is the **Data agent** named
   `HealthcareHLSAgent`, not an ontology or semantic model.
5. Verify the connection identity has access to the Data Agent and its sources
   and has the required `DataAgent.Execute.All` delegated permission.
6. Remove any remaining old `fabric_dataagent_preview` tool from the Foundry
   agent and save a new version.

### Error: 403 on Knowledge Base

**Cause**: Knowledge Base was added as an MCP tool instead of as grounding.

**Fix**: Remove the MCP tool and add the Knowledge Base through the **Knowledge** section (Step 12.3).

### Error: "PrincipalNotFound" when granting workspace access

**Cause**: The managed identity hasn't propagated in Entra ID yet (can take minutes to hours for new resources).

**Fix**:
- Wait 10-15 minutes and retry
- Or add via Fabric UI by searching for the **resource name** instead of Object ID
- The Foundry Hub MSI is the one that matters most — it authenticates all tool calls to Fabric

### Error: Search Indexer fails with "PermissionDenied"

**Cause**: Missing RBAC roles.

**Fix**: Ensure the Search MSI has:
- `Cognitive Services OpenAI User` + `Cognitive Services OpenAI Contributor` on the AI Services account (Step 11.4)
- `Contributor` on the Fabric workspace (Step 11.2)

### Inconsistent data between Fabric UI and Foundry

**Cause**: Missing aggregation rules on the Data Agent, or the orchestrator is modifying queries.

**Fix**:
1. Add aggregation rules to the Data Agent instructions (Step 9.3)
2. Add Rule 17 (Pass-Through Rule) to the orchestrator instructions — ensures queries are sent verbatim from the Query Catalog

### Agent instructions were truncated/lost

**Cause**: Foundry portal sometimes truncates long instructions on save.

**Fix**: Push instructions via API (Step 12.5) and verify:
```powershell
$agent = Invoke-RestMethod -Uri "$base/agents/HealthcareOrchestratorAgent2?api-version=v1" -Headers $headers
Write-Host "Instruction length: $($agent.definition.instructions.Length) chars"
# Should be ~19,000+ chars for the full v29 instructions
```

---

## Resource Reference

| Resource | Purpose | Connection Type |
|---|---|---|
| AI Services Account (Hub) | Hosts the Foundry project, provides MSI for Fabric auth | System-assigned MSI |
| AI Search Service | Indexes healthcare knowledge docs for KB grounding | Entra ID (RBAC) |
| Fabric Workspace | Contains Gold Lakehouse + Data Agent | MSI needs Contributor role |
| Fabric IQ → published Data Agent | Conversational Q&A over `lh_gold_curated`, including long-running queries | `fabric_iq_preview` using the Data Agent MCP endpoint |
| AI Search Index | Vectorized healthcare knowledge docs | azure_ai_search connection |
| gpt-4.1 | Agent reasoning model | Deployed in Foundry |
| text-embedding-ada-002 | Document vectorization for search | Deployed in Foundry |

### Key Files in This Repo

| File | Purpose |
|---|---|
| [`foundry_agent/orchestrator_instructions.md`](foundry_agent/orchestrator_instructions.md) | Full orchestrator system prompt (paste into Foundry agent) |
| [`foundry_agent/deploy_foundry_agent.py`](foundry_agent/deploy_foundry_agent.py) | Validates project resources and deploys an immutable prompt-agent version |
| [`foundry_agent/README.md`](foundry_agent/README.md) | Portable Foundry deployment quickstart |
| [`DATA_AGENT_INSTRUCTIONS.md`](DATA_AGENT_INSTRUCTIONS.md) | Data Agent AI + data source instructions (paste into Fabric) |
| [`DATA_AGENT_GUIDE.md`](DATA_AGENT_GUIDE.md) | Comprehensive Data Agent reference |
| [`SAMPLE_QUESTIONS.md`](SAMPLE_QUESTIONS.md) | 60+ ready-to-use test prompts |
| [`FOUNDRY_ORCHESTRATOR_TROUBLESHOOTING.md`](FOUNDRY_ORCHESTRATOR_TROUBLESHOOTING.md) | Deep troubleshooting guide for hybrid query failures |
