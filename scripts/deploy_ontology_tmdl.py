"""Deploy a separate generation-2 ontology for the new Fabric ontology UI.

The generation-1 ontology and its Data Agent are not modified by this module.
The source JSON model is shared, but is converted into the required TMDL format.
No Data Agent is created or connected to this new-UI item.
"""

from __future__ import annotations

import base64
import json
import re
import time

from deploy_ontology_agent import (
    API,
    GOLD_LAKEHOUSE,
    ONTOLOGY_NAME as LEGACY_ONTOLOGY_NAME,
    FabricClient,
    fetch_definition_parts,
)
from ontology_tmdl import LegacyOntology, build_parts


ONTOLOGY_NAME = f"{LEGACY_ONTOLOGY_NAME}_NewUI"


def _result(client: FabricClient, response, label: str):
    result = client.lro(response, label)
    if result is None:
        raise RuntimeError(f"{label} failed")
    result.raise_for_status()
    return result


def _require_generation_two(client: FabricClient, ontology_id: str) -> None:
    response = client.request(
        "GET", f"{API}/workspaces/{client.workspace_id}/ontologies/{ontology_id}"
    )
    response.raise_for_status()
    generation = response.json().get("properties", {}).get("generation")
    if generation != 2:
        raise RuntimeError(
            f"New-UI item {ontology_id} has generation {generation}, expected 2. "
            "It will not be deleted or converted; use a different display name."
        )


def resolve_gold_lakehouse(client: FabricClient) -> tuple[str, str]:
    """Return SQL endpoint ID and server, not the lakehouse item ID."""
    lakehouse = client.find("Lakehouse", GOLD_LAKEHOUSE)
    if not lakehouse:
        raise RuntimeError(f"{GOLD_LAKEHOUSE} not found - run the pipeline first")
    for attempt in range(30):
        response = client.request(
            "GET", f"{API}/workspaces/{client.workspace_id}/lakehouses/{lakehouse['id']}"
        )
        response.raise_for_status()
        endpoint = response.json().get("properties", {}).get("sqlEndpointProperties") or {}
        if endpoint.get("id") and endpoint.get("connectionString"):
            return endpoint["id"], endpoint["connectionString"]
        if attempt < 29:
            time.sleep(10)
    raise RuntimeError("The gold lakehouse SQL analytics endpoint is not provisioned yet")


def _names(parts: list[dict], folder: str, keyword: str) -> set[str]:
    names = set()
    for part in parts:
        path = part["path"]
        if not path.startswith(folder) or not path.endswith(".tmdl"):
            continue
        text = base64.b64decode(part["payload"]).decode("utf-8-sig")
        for match in re.finditer(rf"^{keyword} ([^\r\n]+)", text, re.MULTILINE):
            name = match.group(1).strip().strip("'").replace("''", "'")
            names.add(name.rsplit("#", 1)[-1])
    return names


def verify_definition(client: FabricClient, ontology_id: str, expected: list[dict]) -> None:
    """Verify all entity, table, and relationship declarations survived storage."""
    response = _result(
        client,
        client.request(
            "POST",
            f"{API}/workspaces/{client.workspace_id}/ontologies/{ontology_id}/getDefinition",
            json={},
        ),
        "read new-UI ontology definition",
    )
    stored = response.json().get("definition", {}).get("parts", [])
    for folder, keyword in (
        ("entities/", "entity"),
        ("tables/", "table"),
        ("entityRelationships.tmdl", "entityRelationship"),
    ):
        wanted = _names(expected, folder, keyword)
        actual = _names(stored, folder, keyword)
        if not wanted or actual != wanted:
            raise RuntimeError(
                f"New-UI {keyword} definitions did not round-trip: "
                f"missing={sorted(wanted - actual)}, unexpected={sorted(actual - wanted)}"
            )


def deploy(notebookutils, owner: str, repo: str, branch: str = "main",
           ontology_name: str = ONTOLOGY_NAME) -> bool:
    """Create/update a generation-2 item without touching the legacy agent path."""
    if ontology_name == LEGACY_ONTOLOGY_NAME:
        raise ValueError("The new-UI ontology must have a different name from the legacy ontology")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,99}", ontology_name):
        raise ValueError("Ontology names must start with a letter and contain only letters, digits, or underscores")

    client = FabricClient(
        notebookutils.credentials.getToken("pbi"),
        notebookutils.runtime.context["currentWorkspaceId"],
    )
    existing = client.find("Ontology", ontology_name)
    if existing:
        _require_generation_two(client, existing["id"])

    endpoint_id, endpoint_server = resolve_gold_lakehouse(client)
    legacy_parts = fetch_definition_parts(client, owner, repo, branch, ontology_name)
    definitions = {
        part["path"]: json.loads(base64.b64decode(part["payload"]).decode("utf-8-sig"))
        for part in legacy_parts if part["path"].endswith(".json")
    }
    ontology = LegacyOntology.load(definitions.__getitem__, {"exportedParts": legacy_parts})
    if not ontology.entities or not ontology.relationships:
        raise RuntimeError("The source ontology must contain entities and relationships")
    parts = build_parts(
        ontology, display_name=ontology_name,
        sql_endpoint=endpoint_server, database_id=endpoint_id,
    )

    if existing:
        ontology_id = existing["id"]
        _result(
            client,
            client.request(
                "POST",
                f"{API}/workspaces/{client.workspace_id}/ontologies/{ontology_id}/updateDefinition",
                json={"definition": {"parts": parts}},
            ),
            "update new-UI ontology",
        )
    else:
        response = _result(
            client,
            client.request(
                "POST", f"{API}/workspaces/{client.workspace_id}/ontologies",
                json={
                    "displayName": ontology_name,
                    "description": "Healthcare new-UI ontology; separate from the generation-1 Data Agent source.",
                    "definition": {"parts": parts},
                },
            ),
            "create new-UI ontology",
        )
        ontology_id = response.json().get("id")
        if not ontology_id:
            created = client.find("Ontology", ontology_name)
            ontology_id = created["id"] if created else None
        if not ontology_id:
            raise RuntimeError("The new-UI ontology was created but its ID could not be resolved")

    _require_generation_two(client, ontology_id)
    verify_definition(client, ontology_id, parts)
    print(
        f"  [OK] {ontology_name} (generation 2): "
        f"{len(ontology.entities)} entities, {len(ontology.relationships)} relationships"
    )
    print("  New ontology UI only; the Data Agent remains connected to the generation-1 ontology.")
    return True
