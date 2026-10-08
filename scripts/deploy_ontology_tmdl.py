"""Deploy the healthcare ontology to Fabric using the new-experience TMDL format.

Usable from a Fabric notebook:

    deploy(notebookutils, owner="rasgiza", repo="Fabric-Payer-Provider-HealthCare-Demo")

The legacy JSON export under ``ontology/`` is converted to TMDL by
``ontology_tmdl`` before upload; sending the legacy JSON directly is accepted by
the API but silently discarded on new-experience tenants.
"""

from __future__ import annotations

import json
import time

import requests

from ontology_tmdl import LegacyOntology, build_parts

API = "https://api.fabric.microsoft.com/v1"
ONTOLOGY_NAME = "Healthcare_Demo_Ontology_HLS"
GOLD_LAKEHOUSE = "lh_gold_curated"


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _lro(resp, headers, label):
    """Resolve a long-running operation. Returns the result response or None.

    A 404 or a missing Location header is treated as a failure rather than
    silently reported as success.
    """
    if resp.status_code in (200, 201):
        return resp
    if resp.status_code != 202:
        print(f"  [FAIL] {label}: HTTP {resp.status_code} {resp.text[:800]}")
        return None
    location = resp.headers.get("Location")
    if not location:
        print(f"  [FAIL] {label}: HTTP 202 without a Location header")
        return None
    for _ in range(60):
        time.sleep(int(resp.headers.get("Retry-After", 5)))
        poll = requests.get(location, headers=headers)
        if poll.status_code != 200:
            continue
        status = poll.json().get("status")
        if status == "Succeeded":
            return requests.get(location.rstrip("/") + "/result", headers=headers)
        if status in ("Failed", "Cancelled"):
            print(f"  [FAIL] {label}: {json.dumps(poll.json())[:800]}")
            return None
    print(f"  [FAIL] {label}: timed out")
    return None


def resolve_gold_lakehouse(workspace_id: str, headers: dict) -> tuple[str, str]:
    """Return (sql_endpoint_id, connection_string) for the gold lakehouse.

    DirectLake's ``Sql.Database(server, database)`` addresses the lakehouse's SQL
    analytics endpoint, whose item ID differs from the lakehouse item ID. Using
    the lakehouse ID produces an ontology that deploys cleanly but whose entities
    resolve no data, which in turn makes it unusable as a Data Agent source.
    """
    items = requests.get(f"{API}/workspaces/{workspace_id}/lakehouses", headers=headers).json()
    lakehouse = next((i for i in items.get("value", []) if i["displayName"] == GOLD_LAKEHOUSE), None)
    if not lakehouse:
        raise RuntimeError(f"{GOLD_LAKEHOUSE} not found in workspace {workspace_id}")

    for _ in range(30):  # the SQL endpoint is provisioned asynchronously
        detail = requests.get(
            f"{API}/workspaces/{workspace_id}/lakehouses/{lakehouse['id']}", headers=headers
        ).json()
        endpoint = (detail.get("properties", {}).get("sqlEndpointProperties") or {})
        if endpoint.get("connectionString") and endpoint.get("id"):
            return endpoint["id"], endpoint["connectionString"]
        time.sleep(10)
    raise RuntimeError("SQL endpoint for the gold lakehouse is not provisioned yet")


def fetch_legacy(owner: str, repo: str, branch: str) -> LegacyOntology:
    base = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/ontology/{ONTOLOGY_NAME}"
    manifest = requests.get(f"{base}/manifest.json").json()

    def read_json(path):
        resp = requests.get(f"{base}/{path}")
        resp.raise_for_status()
        return json.loads(resp.content.decode("utf-8-sig"))

    return LegacyOntology.load(read_json, manifest)


def deploy(notebookutils, owner: str, repo: str, branch: str = "main",
           include_relationships: bool = True) -> bool:
    """Create or update the ontology from the repo definition. Returns success."""
    workspace_id = notebookutils.runtime.context["currentWorkspaceId"]
    headers = _headers(notebookutils.credentials.getToken("pbi"))

    sql_endpoint_id, sql_endpoint = resolve_gold_lakehouse(workspace_id, headers)
    print(f"  gold lakehouse SQL endpoint: {sql_endpoint_id}")

    ontology = fetch_legacy(owner, repo, branch)
    parts = build_parts(
        ontology,
        display_name=ONTOLOGY_NAME,
        sql_endpoint=sql_endpoint,
        database_id=sql_endpoint_id,
        include_relationships=include_relationships,
    )
    print(f"  generated {len(parts)} TMDL parts "
          f"({len(ontology.entities)} entities, {len(ontology.relationships)} relationships)")

    existing = requests.get(f"{API}/workspaces/{workspace_id}/ontologies", headers=headers)
    match = next((o for o in existing.json().get("value", [])
                  if o["displayName"] == ONTOLOGY_NAME), None)

    if match:
        print(f"  updating existing ontology {match['id']}")
        result = _lro(requests.post(
            f"{API}/workspaces/{workspace_id}/ontologies/{match['id']}/updateDefinition",
            headers=headers, json={"definition": {"parts": parts}}), headers, "updateDefinition")
        ontology_id = match["id"]
    else:
        print("  creating ontology")
        result = _lro(requests.post(
            f"{API}/workspaces/{workspace_id}/ontologies", headers=headers,
            json={"displayName": ONTOLOGY_NAME, "description": "Healthcare payer/provider ontology",
                  "definition": {"parts": parts}}), headers, "create")
        ontology_id = (result.json().get("id") if result is not None else None) or next(
            (o["id"] for o in requests.get(f"{API}/workspaces/{workspace_id}/ontologies",
                                           headers=headers).json().get("value", [])
             if o["displayName"] == ONTOLOGY_NAME), None)

    if result is None or not ontology_id:
        return False

    # Verify against what the service actually stored, not the HTTP status.
    read_back = _lro(requests.post(
        f"{API}/workspaces/{workspace_id}/ontologies/{ontology_id}/getDefinition",
        headers=headers), headers, "getDefinition")
    stored = read_back.json().get("definition", {}).get("parts", []) if read_back else []
    entities = [p["path"] for p in stored if p["path"].startswith("entities/")]
    print(f"  stored parts: {len(stored)} | entity types: {len(entities)}")

    if not entities:
        print("  [FAIL] no entity types were stored")
        return False
    print(f"  [OK] ontology deployed with {len(entities)} entity types")
    return True
