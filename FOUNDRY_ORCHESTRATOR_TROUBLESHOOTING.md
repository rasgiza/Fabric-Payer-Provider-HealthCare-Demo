# Foundry Orchestrator + Fabric Data Agent: Troubleshooting Guide

> **Agent**: HealthcareOrchestratorAgent (gpt-4o)
> **Tools**: fabric_dataagent_preview, Knowledge Base (Azure AI Search), web_search_preview

---

## Problem Summary

The Foundry orchestrator agent failed to return data for **hybrid questions** -- questions that require both structured data (from Fabric Data Agent) and unstructured knowledge (from Knowledge Base).

**Example failing question**:
> "What is our denial rate by payer and what does our appeal process guide recommend for the top denial reasons?"

**Symptom**: The orchestrator returned *"unable to retrieve denial rate by payer due to technical limitations"* and only answered the Knowledge Base portion.

---

## Root Causes (3 Issues Found)

### Issue 1: Orchestrator Sent Compound Questions to Data Agent

**What happened**: The orchestrator forwarded the user's entire compound question verbatim to the Fabric Data Agent:

```
Input to fabric_dataagent_preview:
"What is our denial rate by payer and what does our appeal process guide recommend for the top denial reasons?"
```

The Fabric Data Agent received a question containing KB concepts ("appeal process guide", "recommend") that it has no data for, causing it to fail silently.

**How we found it**: Checked Foundry Playground logs --> Conversation --> clicked on `Tool: fabric_dataagent_preview` --> **Input + Output** tab --> saw the full compound question being sent as-is.

### Issue 2: Missing/Stripped Orchestrator Instructions

**What happened**: The orchestrator instructions in Foundry had been accidentally reduced to ~800 characters -- only the `FABRIC DATA AGENT QUERY RULES` section remained. All routing logic, KB document map, tool descriptions, benchmarks, and response formatting were lost.

**How we found it**: Retrieved agent definition via API:
```powershell
$token = az account get-access-token --resource "https://ai.azure.com" --query accessToken -o tsv
$headers = @{"Authorization"="Bearer $token"; "Content-Type"="application/json"}
$base = "https://<AI_SERVICES_NAME>.services.ai.azure.com/api/projects/<PROJECT_NAME>"
$r = Invoke-RestMethod -Uri "$base/agents/HealthcareOrchestratorAgent?api-version=v1" -Headers $headers
$r.versions.latest.definition.instructions
```

### Issue 3: Fabric Data Agent Fewshot Matching is Phrase-Sensitive

**What happened**: The Fabric Data Agent uses fewshot examples for NL-to-SQL. It matches questions by phrasing similarity. Even small differences in wording cause it to generate its own SQL (often with unwanted date filters) instead of using the trained fewshot SQL.

| Query | Result |
|-------|--------|
| "Show me denial rates by payer" (exact fewshot) | Correct: 100K rows, all 12 payers, correct rates |
| "What is the denial rate by payer?" (not exact) | Wrong: 5 rows, date-filtered result |

**How we found it**: Tested both phrasings directly in the Fabric Data Agent UI (Draft mode) and compared results.

---

## Diagnostic Workflow

Follow these steps when hybrid queries fail in Foundry:

### Step 1: Check Foundry Playground Logs

1. Open **Azure AI Foundry** --> your project --> **Agents** --> select agent
2. Go to **Playground** --> run the failing question
3. Click **Tracing** (or check **Conversation** panel in logs)
4. Look at each `Tool: fabric_dataagent_preview` entry
5. Click on it --> **Input + Output** tab --> read the input text
6. Click --> **Metadata** tab --> check `duration` and `status`

**Key indicators**:
| Observation | Meaning |
|-------------|---------|
| `duration: 0` | Data agent didn't execute (connection/auth issue or instant rejection) |
| `duration: 16+s` | Data agent ran but may have returned wrong/empty data |
| `status: OK` but empty output | Query ran but returned no results |
| Input contains KB words ("recommend", "guide", "protocol") | Orchestrator didn't decompose the question |

### Step 2: Verify Agent Instructions via API

```powershell
$token = az account get-access-token --resource "https://ai.azure.com" --query accessToken -o tsv
$headers = @{"Authorization"="Bearer $token"; "Content-Type"="application/json"}
$base = "https://<AI_SERVICES_NAME>.services.ai.azure.com/api/projects/<PROJECT_NAME>"
$r = Invoke-RestMethod -Uri "$base/agents/HealthcareOrchestratorAgent?api-version=v1" -Headers $headers
Write-Host "Version: v$($r.versions.latest.version)"
Write-Host "Instructions length: $($r.versions.latest.definition.instructions.Length) chars"
Write-Host "Tools: $(($r.versions.latest.definition.tools | ForEach-Object { $_.type }) -join ', ')"
$r.versions.latest.definition.instructions
```

**Expected**: Instructions should be ~7,000+ chars with decomposition protocol, query catalog, and KB map.

### Step 3: Test Data Agent Directly

1. Open **Microsoft Fabric** --> your workspace --> **Data Agent**
2. Switch to **Draft** or **Published** mode
3. Test the exact query the orchestrator sent (from Step 1)
4. Test an exact fewshot phrasing for comparison
5. Compare results -- if fewshot works but orchestrator's phrasing doesn't, the issue is phrasing

### Step 4: Check Fabric Data Agent Status

- Is the Data Agent **Published** (green checkmark)?
- Are all lakehouse tables accessible?
- Were any tables recently added/dropped that might confuse the agent?

---

## The Fix: Comprehensive Orchestrator Instructions

The solution was rebuilding the orchestrator instructions with these critical sections:

### 1. Mandatory Decomposition Protocol

The orchestrator MUST classify each part of a user question as DATA, KNOWLEDGE, or EXTERNAL, then send separate queries for each:

```
User: "What is our denial rate by payer and what does our appeal process guide recommend?"

Step 1 - Classify:
  - "denial rate by payer" --> DATA
  - "appeal process guide recommend" --> KNOWLEDGE

Step 2 - Separate calls:
  - fabric_dataagent_preview --> "Show me denial rates by payer"
  - Knowledge Base --> automatic for appeal recommendations

Step 3 - Combine in response
```

### 2. Data Agent Query Catalog

Provide exact fewshot phrasings the orchestrator should use. These match the Fabric Data Agent's trained examples:

```
### Denials & Claims
- "Show me denial rates by payer"
- "What is our overall denial rate?"
- "What are the top denial reasons and their financial impact?"

### Readmissions
- "List patients with high readmission risk"
- "What is our current readmission rate?"
- "Show me readmission trends by month"

### Medication Adherence
- "Show me members who are non-adherent to their medications"
- "Show me medication adherence rates by drug class"
```

### 3. Critical Rules

```
1. NEVER send compound questions to fabric_dataagent_preview
2. NEVER include words like "guide", "recommend", "protocol", "policy" in data agent queries
3. ALWAYS use a phrasing from the Query Catalog
4. If the data agent returns an error or empty result, retry with a simpler phrasing
5. NEVER say "unable to retrieve" if you can retry with a different phrasing
```

### 4. KB Document Map + Benchmarks + Response Format

Tell the orchestrator what topics KB covers so it knows when to rely on automatic KB lookup vs data agent calls. See `foundry_agent/orchestrator_instructions.md` for the full instruction set.

---

## How to Push Updated Instructions via API

```powershell
# 1. Save instructions to a file (foundry_agent/orchestrator_instructions.md)

# 2. Push via API
$token = az account get-access-token --resource "https://ai.azure.com" --query accessToken -o tsv
$headers = @{"Authorization"="Bearer $token"; "Content-Type"="application/json"}
$base = "https://<AI_SERVICES_NAME>.services.ai.azure.com/api/projects/<PROJECT_NAME>"

# Read instructions (skip metadata header lines)
$rawLines = Get-Content "foundry_agent/orchestrator_instructions.md" -Encoding UTF8
$instructions = ($rawLines | Select-Object -Skip 5) -join "`n"

# Get current agent
$r = Invoke-RestMethod -Uri "$base/agents/HealthcareOrchestratorAgent?api-version=v1" -Headers $headers
$def = $r.versions.latest.definition

# Create new version with updated instructions
$body = @{
    definition = @{
        kind = $def.kind
        model = $def.model
        instructions = $instructions
        tools = $def.tools
    }
} | ConvertTo-Json -Depth 10 -Compress

$resp = Invoke-WebRequest `
    -Uri "$base/agents/HealthcareOrchestratorAgent/versions?api-version=v1" `
    -Headers $headers -Method POST `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
    -UseBasicParsing

$j = $resp.Content | ConvertFrom-Json
Write-Host "Created: v$($j.version)"
```

---

## Lessons Learned

| Lesson | Detail |
|--------|--------|
| **Fabric Data Agent is phrase-sensitive** | Fewshot matching requires near-exact question wording. Always provide a "query catalog" to the orchestrator. |
| **Compound questions break the data agent** | The data agent cannot parse questions with KB concepts mixed in. The orchestrator MUST decompose first. |
| **Instructions can silently shrink** | Editing in the Foundry UI can accidentally truncate instructions. Always verify via API after changes. |
| **`duration: 0` = didn't run** | If the data agent tool call shows 0ms duration, the call never reached Fabric -- check connection/auth. |
| **`duration: 16s` + wrong results = phrasing issue** | If the agent ran but returned bad data, the query didn't match a fewshot and it generated its own SQL. |
| **Keep a version-controlled copy** | Save instructions in `foundry_agent/orchestrator_instructions.md` and push via API. Never rely solely on the UI. |
| **Test in Fabric Data Agent first** | Before debugging the orchestrator, test the exact query in the Fabric Data Agent UI to isolate the issue. |

---

## Quick Checklist for New Hybrid Questions

When adding a new hybrid question type:

- [ ] Add fewshot(s) to the Fabric Data Agent for the data portion
- [ ] Test the fewshot phrasing directly in Fabric Data Agent UI
- [ ] Add the exact phrasing to the Query Catalog in orchestrator instructions
- [ ] Add a decomposition example if it's a new pattern
- [ ] Push updated instructions via API
- [ ] Test the hybrid question in Foundry Playground
- [ ] Check logs to confirm decomposition happened correctly

---

## File References

| File | Purpose |
|------|---------|
| [`foundry_agent/orchestrator_instructions.md`](foundry_agent/orchestrator_instructions.md) | Version-controlled orchestrator instructions |
| [`DATA_AGENT_GUIDE.md`](DATA_AGENT_GUIDE.md) | Fabric Data Agent configuration and customization |
| [`FOUNDRY_IQ_SETUP_GUIDE.md`](FOUNDRY_IQ_SETUP_GUIDE.md) | Complete Foundry setup walkthrough |
