"""Deploy the healthcare ontology and its Fabric data agent.

An Ontology item's ``generation`` is fixed when the item is created and cannot be
changed afterwards:

* Creating the item **with** the legacy entity-type JSON definition yields
  ``generation = 1``, and the parts are stored.
* Creating an empty item first yields ``generation = 2`` (the TMDL "new
  experience"), after which legacy parts sent to ``updateDefinition`` are
  accepted, reported as successful, and silently discarded.

Only a generation-1 ontology exposes the child graph model that a Fabric data
agent queries, so this module always creates the item with its definition and
asserts the resulting generation.

The deployment sequence is:

1. create the ontology with its definition (generation 1)
2. patch the data bindings to this workspace's gold lakehouse
3. run ``refreshGraph`` on the auto-provisioned child graph model
4. verify with a live GQL query before reporting success
5. register the ontology as a data agent data source, with instructions
"""

from __future__ import annotations

import base64
import json
import time

import requests

API = "https://api.fabric.microsoft.com/v1"
ONTOLOGY_NAME = "Healthcare_Demo_Ontology_HLS"
GOLD_LAKEHOUSE = "lh_gold_curated"
DATA_AGENT_NAME = "HealthcareOntologyAgent"

# Schema versions accepted by the Data Agent import. These are not
# interchangeable -- an unsupported version fails the whole import.
SCHEMA_DATA_AGENT = ("https://developer.microsoft.com/json-schemas/fabric/item/"
                     "dataAgent/definition/dataAgent/2.1.0/schema.json")
SCHEMA_STAGE = ("https://developer.microsoft.com/json-schemas/fabric/item/"
                "dataAgent/definition/stageConfiguration/1.0.0/schema.json")
SCHEMA_PUBLISH = ("https://developer.microsoft.com/json-schemas/fabric/item/"
                  "dataAgent/definition/publishInfo/1.0.0/schema.json")
SCHEMA_DATASOURCE = ("https://developer.microsoft.com/json-schemas/fabric/item/"
                     "dataAgent/definition/dataSource/1.0.0/schema.json")
SCHEMA_PLATFORM = ("https://developer.microsoft.com/json-schemas/fabric/"
                   "gitIntegration/platformProperties/2.0.0/schema.json")

AGENT_INSTRUCTIONS = """\
You are a healthcare analytics assistant for a payer/provider organization. You \
answer questions about patients, providers, payers, claims, encounters, \
diagnoses, prescriptions and medication adherence.

Data source
- Use the healthcare ontology for every question. It models each business entity \
and the relationships between them, so prefer traversing relationships over \
assuming a join.

Terminology
- "member", "patient" and "beneficiary" all mean the same person.
- "payer" is the insurer; "provider" is the treating clinician or facility.
- A "claim" is a billed encounter; an "encounter" is a clinical visit.
- "adherence" refers to medication adherence, not appointment attendance.

Answering
- State the figures you used and the entities you traversed.
- When counting people, count distinct patients rather than rows.
- Return the top N when a question implies a ranking, and say what you ranked by.
- If a question cannot be answered from the connected data, say so plainly \
instead of estimating.
"""


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


class FabricClient:
    """Minimal Fabric REST client with retry and honest long-running-operation handling."""

    def __init__(self, token: str, workspace_id: str):
        self.workspace_id = workspace_id
        self.headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def request(self, method: str, url: str, **kwargs):
        kwargs.setdefault("timeout", 120)
        last = None
        for attempt in range(5):  # this endpoint intermittently resets TLS connections
            try:
                return requests.request(method, url, headers=self.headers, **kwargs)
            except requests.exceptions.RequestException as exc:
                last = exc
                time.sleep(4 * (attempt + 1))
        raise last

    def lro(self, response, label: str):
        """Resolve a long-running operation.

        A missing Location header or a non-2xx status is a failure. It is never
        reported as success, so a rejected request cannot pass silently.
        """
        if response.status_code in (200, 201):
            return response
        if response.status_code != 202:
            print(f"  [FAIL] {label}: HTTP {response.status_code} {response.text[:600]}")
            return None
        location = response.headers.get("Location")
        if not location:
            print(f"  [FAIL] {label}: HTTP 202 without a Location header")
            return None
        for _ in range(120):
            time.sleep(int(response.headers.get("Retry-After", 5)))
            poll = self.request("GET", location)
            if poll.status_code != 200:
                continue
            status = poll.json().get("status")
            if status in ("Succeeded", "Completed"):
                return self.request("GET", location.rstrip("/") + "/result")
            if status in ("Failed", "Cancelled"):
                print(f"  [FAIL] {label}: {json.dumps(poll.json())[:600]}")
                return None
        print(f"  [FAIL] {label}: timed out")
        return None

    def items(self, item_type: str | None = None) -> list[dict]:
        url = f"{API}/workspaces/{self.workspace_id}/items"
        if item_type:
            url += f"?type={item_type}"
        return self.request("GET", url).json().get("value", [])

    def find(self, item_type: str, display_name: str) -> dict | None:
        return next((i for i in self.items()
                     if i["type"] == item_type and i["displayName"] == display_name), None)


def fetch_definition_parts(client: FabricClient, owner: str, repo: str, branch: str,
                           display_name: str) -> list[dict]:
    """Fetch the legacy ontology export and point its bindings at this workspace."""
    lakehouse = client.find("Lakehouse", GOLD_LAKEHOUSE)
    if not lakehouse:
        raise RuntimeError(f"{GOLD_LAKEHOUSE} not found - run the pipeline first")
    lakehouse_id = lakehouse["id"]

    def repoint(node):
        if isinstance(node, dict):
            for key, value in node.items():
                lowered = key.lower()
                if lowered == "workspaceid" and isinstance(value, str):
                    node[key] = client.workspace_id
                elif lowered in ("itemid", "artifactid", "lakehouseid") and isinstance(value, str):
                    node[key] = lakehouse_id
                else:
                    repoint(value)
        elif isinstance(node, list):
            for item in node:
                repoint(item)
        return node

    base = (f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}"
            f"/ontology/{ONTOLOGY_NAME}")
    manifest = requests.get(f"{base}/manifest.json", timeout=120).json()

    platform = json.dumps({
        "$schema": SCHEMA_PLATFORM,
        "metadata": {"type": "Ontology", "displayName": display_name},
        "config": {"version": "2.0", "logicalId": "00000000-0000-0000-0000-000000000000"},
    }, indent=2)

    # The manifest ships its own .platform; ours carries the right displayName.
    by_path: dict[str, str] = {".platform": platform}
    for part in manifest["exportedParts"]:
        path = part["path"]
        if path == ".platform":
            continue
        resp = requests.get(f"{base}/{path}", timeout=120)
        resp.raise_for_status()
        text = resp.content.decode("utf-8-sig")  # the export is BOM-prefixed
        if path.endswith(".json"):
            text = json.dumps(repoint(json.loads(text)), indent=2)
        by_path[path] = text

    return [{"path": path, "payload": _b64(text), "payloadType": "InlineBase64"}
            for path, text in by_path.items()]


def deploy_ontology(client: FabricClient, parts: list[dict], display_name: str) -> str:
    """Create the ontology as generation 1. Returns its item ID."""
    existing = client.find("Ontology", display_name)
    if existing:
        meta = client.request("GET", f"{API}/workspaces/{client.workspace_id}"
                                     f"/ontologies/{existing['id']}").json()
        generation = meta.get("properties", {}).get("generation")
        if generation == 1:
            print(f"  reusing generation-1 ontology {existing['id']}")
            updated = client.lro(client.request(
                "POST", f"{API}/workspaces/{client.workspace_id}"
                        f"/ontologies/{existing['id']}/updateDefinition",
                json={"definition": {"parts": parts}}), "updateDefinition")
            if updated is None:
                raise RuntimeError("updateDefinition failed")
            return existing["id"]
        # Generation is immutable, so a generation-2 item has to be replaced.
        print(f"  existing ontology is generation {generation}; deleting to recreate")
        client.request("DELETE", f"{API}/workspaces/{client.workspace_id}"
                                 f"/ontologies/{existing['id']}")
        time.sleep(15)

    body = {"displayName": display_name,
            "description": "Healthcare payer/provider ontology",
            "definition": {"parts": parts}}

    created = None
    for attempt in range(12):  # a deleted display name takes minutes to be released
        response = client.request("POST", f"{API}/workspaces/{client.workspace_id}/ontologies",
                                  json=body)
        if response.status_code == 409 and "NotAvailableYet" in (response.text or ""):
            time.sleep(30)
            continue
        created = client.lro(response, "create ontology")
        break
    if created is None:
        raise RuntimeError("could not create the ontology")

    ontology_id = created.json().get("id") or next(
        (o["id"] for o in client.request(
            "GET", f"{API}/workspaces/{client.workspace_id}/ontologies").json().get("value", [])
         if o["displayName"] == display_name), None)
    if not ontology_id:
        raise RuntimeError("ontology created but its ID could not be resolved")

    meta = client.request("GET", f"{API}/workspaces/{client.workspace_id}"
                                 f"/ontologies/{ontology_id}").json()
    generation = meta.get("properties", {}).get("generation")
    if generation != 1:
        raise RuntimeError(
            f"ontology was created as generation {generation}, expected 1. "
            "A generation-2 ontology has no child graph model and cannot be queried "
            "by a data agent."
        )
    print(f"  created generation-1 ontology {ontology_id}")
    return ontology_id


def entity_types(client: FabricClient, ontology_id: str) -> list[tuple[str, str]]:
    """Return (id, name) for each entity type stored in the ontology."""
    stored = client.lro(client.request(
        "POST", f"{API}/workspaces/{client.workspace_id}"
                f"/ontologies/{ontology_id}/getDefinition", json={}), "getDefinition")
    if stored is None:
        raise RuntimeError("could not read back the ontology definition")

    found = []
    for part in stored.json()["definition"]["parts"]:
        path = part["path"]
        if path.startswith("EntityTypes/") and path.endswith("definition.json"):
            doc = json.loads(base64.b64decode(part["payload"]).decode("utf-8-sig"))
            found.append((str(doc["id"]), doc["name"]))
    return found


def refresh_graph(client: FabricClient, ontology_id: str) -> str:
    """Build the ontology's child graph model and verify it answers a query."""
    key = ontology_id.replace("-", "")[:8]
    graph = next((i for i in client.items()
                  if i["type"] == "GraphModel" and key in i["displayName"].replace("-", "")), None)
    if not graph:
        raise RuntimeError("the ontology's child graph model was not provisioned")
    print(f"  child graph model: {graph['displayName']}")

    response = client.request(
        "POST", f"{API}/workspaces/{client.workspace_id}"
                f"/graphModels/{graph['id']}/jobs/refreshGraph/instances", json={})
    if response.status_code not in (200, 201, 202):
        raise RuntimeError(f"refreshGraph rejected: HTTP {response.status_code} "
                           f"{response.text[:400]}")

    location = response.headers.get("Location")
    if location:
        for _ in range(120):
            time.sleep(10)
            poll = client.request("GET", location)
            if poll.status_code != 200:
                continue
            status = poll.json().get("status")
            if status in ("Completed", "Succeeded"):
                break
            if status in ("Failed", "Cancelled"):
                raise RuntimeError(f"refreshGraph failed: {json.dumps(poll.json())[:600]}")
        else:
            print("  [WARN] refreshGraph still running; verifying anyway")
    print("  graph refreshed")
    return graph["id"]


def verify_graph(client: FabricClient, graph_id: str) -> int:
    """Run a real query. Structural success is not evidence that data is readable."""
    response = client.request(
        "POST", f"{API}/workspaces/{client.workspace_id}"
                f"/graphModels/{graph_id}/executeQuery?beta=true",
        json={"query": "MATCH (p:Patient) RETURN count(p) AS n"})
    body = response.json()
    if body.get("status", {}).get("code") != "00000":
        cause = (body.get("status", {}).get("cause", {}).get("description")
                 or body.get("status", {}).get("description"))
        raise RuntimeError(f"graph query failed: {cause}")
    count = body["result"]["data"][0]["n"]
    print(f"  verified: {count} Patient nodes")
    return int(count)


def deploy_data_agent(client: FabricClient, ontology_id: str, ontology_name: str,
                      types: list[tuple[str, str]], agent_name: str) -> str:
    """Create or update the data agent with the ontology attached and published."""
    datasource = json.dumps({
        "$schema": SCHEMA_DATASOURCE,
        "artifactId": ontology_id,
        "workspaceId": client.workspace_id,
        "displayName": ontology_name,
        "type": "ontology",
        "userDescription": "Healthcare payer/provider ontology covering patients, providers, "
                           "payers, claims, encounters, diagnoses and prescriptions.",
        "dataSourceInstructions": "Use for any question about patients, providers, payers, "
                                  "claims, encounters, diagnoses, prescriptions or medication "
                                  "adherence, including relationships between them.",
        "metadata": {},
        # Ontology entity types are registered as graph node types; there is no
        # ontology-specific element type in the data source schema.
        "elements": [
            {"id": type_id, "is_selected": True, "display_name": name,
             "type": "graph.nodeType", "description": None, "children": []}
            for type_id, name in sorted(types, key=lambda t: t[1])
        ],
    }, indent=2)

    stage_config = json.dumps({
        "$schema": SCHEMA_STAGE,
        "aiInstructions": AGENT_INSTRUCTIONS,
        "experimental": {"enableExperimentalFeatures": True},
    }, indent=2)

    platform = json.dumps({
        "$schema": SCHEMA_PLATFORM,
        "metadata": {"type": "DataAgent", "displayName": agent_name},
        "config": {"version": "2.0", "logicalId": "00000000-0000-0000-0000-000000000000"},
    }, indent=2)

    publish_info = json.dumps({
        "$schema": SCHEMA_PUBLISH,
        "description": "Healthcare analytics agent answering questions about patients, "
                       "providers, payers, claims and encounters via the ontology.",
    }, indent=2)

    folder = f"ontology-{ontology_name}"
    # Writing the published stage as well as the draft makes the agent usable
    # without a manual Publish in the portal.
    parts = [
        {"path": ".platform", "payload": _b64(platform)},
        {"path": "Files/Config/data_agent.json",
         "payload": _b64(json.dumps({"$schema": SCHEMA_DATA_AGENT}, indent=2))},
        {"path": "Files/Config/draft/stage_config.json", "payload": _b64(stage_config)},
        {"path": f"Files/Config/draft/{folder}/datasource.json", "payload": _b64(datasource)},
        {"path": "Files/Config/published/stage_config.json", "payload": _b64(stage_config)},
        {"path": f"Files/Config/published/{folder}/datasource.json", "payload": _b64(datasource)},
        {"path": "Files/Config/publish_info.json", "payload": _b64(publish_info)},
    ]
    for part in parts:
        part["payloadType"] = "InlineBase64"

    existing = client.find("DataAgent", agent_name)
    if existing:
        result = client.lro(client.request(
            "POST", f"{API}/workspaces/{client.workspace_id}"
                    f"/items/{existing['id']}/updateDefinition",
            json={"definition": {"parts": parts}}), "update data agent")
        if result is None:
            raise RuntimeError("could not update the data agent")
        print(f"  updated data agent {existing['id']}")
        return existing["id"]

    created = client.lro(client.request(
        "POST", f"{API}/workspaces/{client.workspace_id}/items",
        json={"displayName": agent_name, "type": "DataAgent",
              "definition": {"parts": parts}}), "create data agent")
    if created is None:
        raise RuntimeError("could not create the data agent")

    agent_id = created.json().get("id") or next(
        (i["id"] for i in client.items()
         if i["type"] == "DataAgent" and i["displayName"] == agent_name), None)
    print(f"  created data agent {agent_id}")
    return agent_id


def deploy(notebookutils, owner: str, repo: str, branch: str = "main",
           ontology_name: str = ONTOLOGY_NAME,
           agent_name: str = DATA_AGENT_NAME,
           create_agent: bool = True) -> bool:
    """Deploy the ontology, build its graph, and wire it into a data agent."""
    workspace_id = notebookutils.runtime.context["currentWorkspaceId"]
    client = FabricClient(notebookutils.credentials.getToken("pbi"), workspace_id)

    try:
        print("Step 1: Deploy Ontology")
        parts = fetch_definition_parts(client, owner, repo, branch, ontology_name)
        print(f"  definition parts: {len(parts)}")
        ontology_id = deploy_ontology(client, parts, ontology_name)

        types = entity_types(client, ontology_id)
        print(f"  entity types: {len(types)}")
        if not types:
            raise RuntimeError("no entity types were stored")

        print("\nStep 2: Build Ontology Graph")
        graph_id = refresh_graph(client, ontology_id)
        verify_graph(client, graph_id)

        if create_agent:
            print("\nStep 3: Deploy Data Agent")
            deploy_data_agent(client, ontology_id, ontology_name, types, agent_name)

        print(f"\n[OK] ontology '{ontology_name}' deployed with {len(types)} entity types")
        return True
    except Exception as exc:  # surfaced to the notebook so a failure is never silent
        print(f"\n[FAIL] {exc}")
        return False
