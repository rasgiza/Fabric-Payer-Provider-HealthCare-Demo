# Foundry Orchestrator Deployment

This folder deploys the healthcare orchestrator as an ordinary Microsoft
Foundry prompt agent. It connects to the Fabric assets created by
`Healthcare_Launcher.ipynb`; it does not deploy or copy those Fabric assets.

## What is automated

`deploy_foundry_agent.py`:

1. Authenticates with `DefaultAzureCredential`.
2. Verifies the configured model deployment exists.
3. Resolves project connections by name inside the user's Foundry project.
4. Rejects deprecated `fabric_dataagent_preview` connections.
5. Verifies Fabric IQ targets a published Fabric Data Agent endpoint.
6. Requires the Azure AI Search connection and healthcare knowledge index.
7. Deploys the saved instructions with web search, Azure AI Search, and
   Fabric IQ.
8. Creates a new immutable agent version.

Rerunning the script updates the same agent by creating another version.

## One-time prerequisites

1. Deploy Fabric by running `Healthcare_Launcher.ipynb`.
2. Open `HealthcareHLSAgent` in Fabric, verify its sources, and publish it.
3. Create or select a Microsoft Foundry project.
4. Deploy `gpt-4.1` or set `FOUNDRY_MODEL_NAME` to another existing deployment.
5. Create the Azure AI Search connection and
   `healthcare-onelake-ks-index`.
6. In the Foundry portal, add **Fabric IQ (OneLake Catalog)**, filter to
   **Data agent**, and select the published `HealthcareHLSAgent`.

The Fabric IQ portal step establishes the signed-in user's Fabric OAuth
connection and therefore cannot be replaced with a repository credential.

## Configure

Install the supported SDK:

```powershell
python -m pip install -r foundry_agent\requirements.txt
az login --tenant <tenant-id>
```

Set the values shown in `deployment.env.example` in the current shell:

```powershell
$env:FOUNDRY_PROJECT_ENDPOINT = "https://<account>.services.ai.azure.com/api/projects/<project>"
$env:FOUNDRY_AGENT_NAME = "HealthcareOrchestratorAgent2"
$env:FOUNDRY_MODEL_NAME = "gpt-4.1"
$env:FABRIC_IQ_CONNECTION_NAME = "HealthcareHLSAgent"
$env:AZURE_AI_SEARCH_CONNECTION_NAME = "<search-connection-name>"
$env:AZURE_AI_SEARCH_INDEX_NAME = "healthcare-onelake-ks-index"
```

Connection names are portable within a project. Full Azure resource IDs are
accepted for CI compatibility but are not required.

## Validate and deploy

List available connections when their names are unknown:

```powershell
python foundry_agent\deploy_foundry_agent.py --list-connections
```

Run the complete preflight without creating a version:

```powershell
python foundry_agent\deploy_foundry_agent.py --validate-only
```

Deploy after validation succeeds:

```powershell
python foundry_agent\deploy_foundry_agent.py
```

The expected tools are:

```text
web_search_preview, azure_ai_search, fabric_iq_preview
```

If the script finds an old `fabric_dataagent_preview` connection, remove that
tool from the agent and add Fabric IQ from OneLake Catalog before retrying.
