# Foundry IQ — Healthcare Orchestrator Agent Setup Guide

> **Complete step-by-step guide** to replicate the Healthcare Intelligence Orchestrator Agent that combines a **Knowledge Base** (unstructured healthcare documents) with a **Fabric Data Agent** (structured Lakehouse data) in Azure AI Foundry.

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
11. [Step 9 — Connect the Fabric Data Agent](#step-9--connect-the-fabric-data-agent)
12. [Step 10 — Create the Orchestrator Agent](#step-10--create-the-orchestrator-agent)
13. [Step 11 — Test the Agent](#step-11--test-the-agent)
14. [Troubleshooting](#troubleshooting)
15. [Resource Reference](#resource-reference)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              HealthcareOrchestratorAgent                 │
│                     (gpt-4o)                            │
├─────────────┬──────────────────┬────────────────────────┤
│  Knowledge  │  Fabric Data     │  Web Search            │
│  Base       │  Agent           │  (Bing Grounding)      │
│  (Grounding)│  (Preview)       │                        │
├─────────────┼──────────────────┼────────────────────────┤
│ AI Search   │ Fabric Lakehouse │  Bing                  │
│ Index       │ (16 tables)      │                        │
│ 11,316 docs │ Star Schema      │                        │
└─────────────┴──────────────────┴────────────────────────┘
     │                  │
     ▼                  ▼
 healthcare_knowledge/  Gold Lakehouse Tables
 (21 markdown files)    (dim_*, fact_*, agg_*)
```

**How it works:**
- **Policy/guideline/protocol questions** --> Knowledge Base grounding (AI Search index)
- **Data/metrics/counts/trends questions** --> Fabric Data Agent (SQL over Lakehouse)
- **Combined questions** --> Both sources synthesized together

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
| **Foundry endpoint** | Portal --> Project --> Overview | `https://<hub-name>.services.ai.azure.com` |
| **Foundry project MSI** | Azure Portal --> AI Services --> Identity --> Object ID | `<your-foundry-project-msi>` |
| **Resource Group** | Azure Portal | `healthcaredemofoundry-rg` |
| **Subscription ID** | Azure Portal | `<your-subscription-id>` |

---

## Step 2 — Deploy Required Models

In the Foundry portal, go to **Models + Endpoints** --> **+ Deploy model**:

### 2.1 Deploy gpt-4o (for agent chat)
- Model: **gpt-4o**
- Deployment name: `gpt-4o`
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
   - **Model**: `gpt-4o`
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

## Step 9 — Connect the Fabric Data Agent

### 9.1 Prerequisites

You need a **Fabric Data Agent** already created in your Fabric workspace. The Data Agent should:
- Be connected to your **Gold Lakehouse** (`lh_gold_curated`)
- Have AI instructions configured (knowledge of your star schema tables)
- Be tested and working within Fabric

> **Tip**: The Healthcare Launcher deploys the `HealthcareHLSAgent` Data Agent automatically. See [DATA_AGENT_GUIDE.md](DATA_AGENT_GUIDE.md) for configuration details.

### 9.2 Create a Connection in Foundry

1. In **Foundry portal** --> **Management center** --> **Connected resources**
2. Click **+ New connection**
3. Select **Microsoft Fabric** --> **Data Agent**
4. Configure:
   - **Fabric Workspace ID**: Your workspace ID
   - **Data Agent Artifact ID**: The Data Agent's item ID from Fabric
5. Name the connection (e.g., `HealthcareHLSAgent`)
6. Click **Connect**

> **Finding the Data Agent Artifact ID**: In Fabric portal --> Workspace --> find your Data Agent --> the URL contains the artifact ID.

---

## Step 10 — Create the Orchestrator Agent

### 10.1 Create via Portal

1. In **Foundry portal** --> **Agents** (left sidebar)
2. Click **+ New agent**
3. Configure:
   - **Name**: `HealthcareOrchestratorAgent`
   - **Model**: `gpt-4o`

### 10.2 Set Agent Instructions

> **Important**: Use the comprehensive instructions from [`foundry_agent/orchestrator_instructions.md`](foundry_agent/orchestrator_instructions.md). These include a mandatory decomposition protocol that prevents hybrid query failures.

**Quick version** (for initial setup -- replace with full instructions ASAP):

```
You are a Healthcare Intelligence Orchestrator. You have two capabilities:

1. Knowledge Base (healthcareknowledgebase) - Use for questions about clinical guidelines,
   compliance policies, denial management procedures, formulary rules, provider network
   requirements, and quality measures. This knowledge base is available through grounding.

2. Fabric Data Agent (HealthcareHLSAgent) - Use for questions about patient data,
   claims, encounters, prescriptions, diagnoses, readmission rates, denial rates, provider
   performance, payer analytics, and any structured data queries.

Routing rules:
- Policy/guideline/protocol questions -> use your grounded knowledge
- Data/metrics/counts/trends questions -> Fabric Data Agent
- Questions spanning both -> use BOTH grounded knowledge and Fabric Data Agent, then synthesize
- Always cite sources: document names for knowledge, table names for data
```

**Production version** (full instructions, ~10K chars): Copy from `foundry_agent/orchestrator_instructions.md`. This version includes:
- Mandatory Decomposition Protocol (5-step process)
- Decomposition examples for compound questions
- Data Agent Query Catalog (35+ exact fewshot phrasings)
- KB Document Map (20 topics)
- Industry Benchmarks (CMS, HEDIS, etc.)
- Citation Protocol (mandatory source references)
- Deep Response Protocol (multi-call enrichment)
- 15 Critical Rules for reliable hybrid queries

See [FOUNDRY_ORCHESTRATOR_TROUBLESHOOTING.md](FOUNDRY_ORCHESTRATOR_TROUBLESHOOTING.md) for why these detailed instructions exist and how to push them via API.

### 10.3 Add Tools

1. **Web Search** (optional): Click **Add** --> **Web Search** --> Enable
2. **Fabric Data Agent**: Click **Add** --> **Fabric Data Agent** --> Select the connection created in Step 9

### 10.4 Add Knowledge (Grounding)

1. Scroll down to **Knowledge** section
2. Click **Add**
3. Select `healthcareknowledgebase` (created in Step 7)

> **Important**: The Knowledge Base provides grounding for unstructured document queries. This is separate from the tools.

### 10.5 Save the Agent

Click **Save** to save the agent version.

---

### 10.6 Known Issue: `server_authentication` Bug

**Problem**: If you add the Knowledge Base as an MCP tool (instead of in the Knowledge section), the portal injects a `server_authentication` field that the API doesn't support, causing:
```
unknown_parameter - tools[1].server_authentication
```

**Solution**: Use the Knowledge Base through the **Knowledge section** (grounding), NOT as an MCP tool.

**If you need to fix via API** (removing bad tool definitions):

```powershell
# Get a token
$token = az account get-access-token --resource "https://ai.azure.com" --query accessToken -o tsv
$headers = @{"Authorization"="Bearer $token"; "Content-Type"="application/json"}
$base = "https://<AI_SERVICES_NAME>.services.ai.azure.com/api/projects/<PROJECT_NAME>"

# Create a new version without the MCP tool
$body = @{
    definition = @{
        kind = "prompt"
        model = "gpt-4o"
        instructions = "<YOUR_INSTRUCTIONS>"
        tools = @(
            @{ type = "web_search_preview" }
            @{
                type = "fabric_dataagent_preview"
                fabric_dataagent_preview = @{
                    project_connections = @(
                        @{ project_connection_id = "<FULL_CONNECTION_ID>" }
                    )
                }
            }
        )
    }
} | ConvertTo-Json -Depth 10

Invoke-WebRequest -Uri "$base/agents/HealthcareOrchestratorAgent/versions?api-version=v1" `
    -Headers $headers -Method POST `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -UseBasicParsing
```

---

## Step 11 — Test the Agent

### 11.1 Test Knowledge Base (Unstructured Data)

Ask: **"What are the CHF management guidelines?"**

Expected: Detailed response citing clinical guidelines from your healthcare_knowledge documents, including diagnosis, pharmacologic therapy, etc.

### 11.2 Test Fabric Data Agent (Structured Data)

Ask: **"What is the total number of claims by payer?"**

Expected: Data pulled from your Lakehouse tables (fact_claims, dim_payer), with numbers and table citations.

### 11.3 Test Combined Query

Ask: **"What are the readmission rates for CHF patients and what do the clinical guidelines recommend to reduce readmissions?"**

Expected: The agent should use BOTH sources -- pull readmission data from Fabric AND guideline recommendations from the Knowledge Base -- and synthesize the answer.

---

## Troubleshooting

### Issue: Indexer shows 0 documents / PermissionDenied

**Cause**: Search MSI can't call the embedding model.

**Fix**:
```powershell
az role assignment create --assignee <SEARCH_MSI_ID> --role "Cognitive Services OpenAI User" \
    --scope "/subscriptions/<SUB>/resourceGroups/<RG>/providers/Microsoft.CognitiveServices/accounts/<AI_SERVICES>"
az role assignment create --assignee <SEARCH_MSI_ID> --role "Cognitive Services OpenAI Contributor" \
    --scope "/subscriptions/<SUB>/resourceGroups/<RG>/providers/Microsoft.CognitiveServices/accounts/<AI_SERVICES>"
```
Wait 5-10 min, then Reset + Run the indexer.

---

### Issue: `unknown_parameter - tools[1].server_authentication`

**Cause**: Portal injects `server_authentication` into MCP tool config, which the API doesn't support.

**Fix**: Remove the Knowledge Base MCP tool and add the knowledge base via the **Knowledge section** (grounding) instead. Or create a new agent version via API without the offending field (see Step 10.6).

---

### Issue: 405 (Method Not Allowed) on MCP endpoint (RECURRING)

**Cause**: The Foundry portal re-injects the MCP tool every time you save the agent. The MCP server requires SSE transport headers that the Foundry agent runtime doesn't send correctly.

**Fix**: After every portal save, create a new agent version via API that removes the MCP tool definition. Then refresh the portal page and switch to the new version.

---

### Issue: 401 Unauthorized on MCP endpoint

**Cause**: MCP tool can't authenticate to the Search service without `server_authentication`, but including it causes a different error.

**Fix**: Don't use Knowledge Base as an MCP tool. Use the **Knowledge section** for grounding instead.

---

### Issue: Fabric Data Agent not responding

**Cause**: Connection not properly configured, or Data Agent not active.

**Fix**:
1. Verify the connection in Foundry Management Center --> Connected resources
2. Verify the Data Agent is working in Fabric portal first
3. Ensure the Foundry project MSI has access to the Fabric workspace

---

### Issue: Role assignments not taking effect

**Cause**: RBAC propagation delay.

**Fix**: Wait 10-15 minutes. You can verify assignments:
```powershell
az role assignment list --assignee <OBJECT_ID> --scope <RESOURCE_SCOPE> --output table
```

---

## Resource Reference

### Useful API Patterns

```powershell
# Get Foundry token
$token = az account get-access-token --resource "https://ai.azure.com" --query accessToken -o tsv
$base = "https://<AI_SERVICES_NAME>.services.ai.azure.com/api/projects/<PROJECT_NAME>"

# List agents
Invoke-RestMethod -Uri "$base/agents?api-version=v1" -Headers @{"Authorization"="Bearer $token"}

# Get agent details
Invoke-RestMethod -Uri "$base/agents/HealthcareOrchestratorAgent?api-version=v1" -Headers @{"Authorization"="Bearer $token"}

# List agent versions
Invoke-RestMethod -Uri "$base/agents/HealthcareOrchestratorAgent/versions?api-version=v1" -Headers @{"Authorization"="Bearer $token"} -Method GET

# Delete a specific version
Invoke-RestMethod -Uri "$base/agents/HealthcareOrchestratorAgent/versions/<VERSION_NUMBER>?api-version=v1" -Headers @{"Authorization"="Bearer $token"} -Method DELETE
```

---

## Quick Replication Checklist

- [ ] Create AI Foundry Hub + Project
- [ ] Deploy `gpt-4o` and `text-embedding-ada-002` models
- [ ] Create AI Search service (Basic+), enable System MSI, set auth to "Both"
- [ ] Assign RBAC: Search MSI --> Search Service (3 roles)
- [ ] Assign RBAC: Search MSI --> AI Services (2 roles: OpenAI User + Contributor)
- [ ] Assign RBAC: Search MSI --> Fabric Workspace (Contributor)
- [ ] Assign RBAC: Your User --> Search Service (3 roles)
- [ ] Connect Search service to Foundry (Entra ID auth)
- [ ] Ensure healthcare knowledge files are in Lakehouse (uploaded by launcher Cell 6)
- [ ] Create Knowledge Source (OneLake --> Lakehouse)
- [ ] Wait for Knowledge Source status = **Active**
- [ ] Create Knowledge Base with instructions
- [ ] Verify indexer: docs succeeded > 0, docs failed = 0
- [ ] Connect Fabric Data Agent to Foundry
- [ ] Create Orchestrator Agent with instructions + tools + knowledge grounding
- [ ] Push full instructions from `foundry_agent/orchestrator_instructions.md`
- [ ] Test all three query types (knowledge, data, combined)
- [ ] Test a hybrid question (e.g., "denial rates by payer + appeal process recommendations")

---

## Key Lessons Learned

These lessons were discovered through debugging hybrid query failures. Full details in [FOUNDRY_ORCHESTRATOR_TROUBLESHOOTING.md](FOUNDRY_ORCHESTRATOR_TROUBLESHOOTING.md).

| Lesson | Detail |
|--------|--------|
| **Fabric Data Agent is phrase-sensitive** | Fewshot matching requires near-exact question wording. Provide a "query catalog" to the orchestrator. |
| **Compound questions break the data agent** | The data agent cannot parse questions with KB concepts mixed in. The orchestrator MUST decompose first. |
| **Instructions can silently shrink** | Editing in the Foundry UI can accidentally truncate instructions. Always verify via API after changes. |
| **Ontology is visual only** | We tested ontology as a Data Agent source -- it returned wrong results. Keep lakehouse-based agent. |
| **Keep a version-controlled copy** | Save instructions in `foundry_agent/orchestrator_instructions.md` and push via API. Never rely solely on the UI. |
| **Test in Fabric Data Agent first** | Before debugging the orchestrator, test the exact query in the Fabric Data Agent UI to isolate the issue. |

---

## Related Files

| File | Purpose |
|------|---------|
| [`foundry_agent/orchestrator_instructions.md`](foundry_agent/orchestrator_instructions.md) | Version-controlled orchestrator instructions |
| [`FOUNDRY_ORCHESTRATOR_TROUBLESHOOTING.md`](FOUNDRY_ORCHESTRATOR_TROUBLESHOOTING.md) | Full diagnostic guide for hybrid query failures |
| [`DATA_AGENT_GUIDE.md`](DATA_AGENT_GUIDE.md) | Fabric Data Agent configuration and customization |
| [`SAMPLE_QUESTIONS.md`](SAMPLE_QUESTIONS.md) | 60+ copy-paste questions including Foundry agent questions |
