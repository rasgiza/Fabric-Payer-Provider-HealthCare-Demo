import base64
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data_agents" / "Healthcare Ontology Agent.DataAgent" / "Files" / "Config"
SOURCE = "graph-Healthcare_Demo_Graph"
sys.path.insert(0, str(ROOT / "scripts"))

import deploy_ontology_agent as deployment


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


class OntologyAgentConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ontology = ROOT / "ontology" / "Healthcare_Demo_Ontology_HLS"
        cls.entities = {}
        for path in (ontology / "EntityTypes").glob("*/definition.json"):
            entity = read_json(path)
            cls.entities[entity["id"]] = entity
        cls.relationships = {}
        for path in (ontology / "RelationshipTypes").glob("*/definition.json"):
            relationship = read_json(path)
            cls.relationships[relationship["name"]] = (
                cls.entities[relationship["source"]["entityTypeId"]]["name"],
                cls.entities[relationship["target"]["entityTypeId"]]["name"],
            )

    def test_draft_published_and_documented_instructions_stay_in_sync(self) -> None:
        for relative in (
            Path("stage_config.json"),
            Path(SOURCE) / "datasource.json",
            Path(SOURCE) / "fewshots.json",
        ):
            with self.subTest(file=str(relative)):
                self.assertEqual(
                    read_json(CONFIG / "draft" / relative),
                    read_json(CONFIG / "published" / relative),
                )
        instructions = read_json(CONFIG / "draft" / "stage_config.json")["aiInstructions"]
        section = (ROOT / "DATA_AGENT_INSTRUCTIONS.md").read_text(encoding="utf-8")
        section = section.split("## 2a", 1)[1].split("## Graph Ontology", 1)[0]
        self.assertIn(instructions, section)
        self.assertLessEqual(len(instructions), 2000, "Keep behavior guidance concise.")

    def test_source_descriptions_match_actual_relationship_directions(self) -> None:
        source = read_json(CONFIG / "draft" / SOURCE / "datasource.json")
        nodes = {e["display_name"] for e in source["elements"] if e["type"] == "graph.nodeType"}
        self.assertEqual(nodes, {e["name"] for e in self.entities.values()})
        edges = {e["display_name"]: e for e in source["elements"] if e["type"] == "graph.edgeType"}
        self.assertEqual(set(edges), set(self.relationships))
        for name, (start, end) in self.relationships.items():
            with self.subTest(relationship=name):
                self.assertTrue(
                    edges[name]["description"].startswith(f"{start} -> {end}:"),
                    edges[name]["description"],
                )

    def test_example_labels_properties_and_edges_match_schema(self) -> None:
        properties = {
            entity["name"]: {p["name"] for p in entity["properties"]}
            for entity in self.entities.values()
        }
        examples = read_json(CONFIG / "draft" / SOURCE / "fewshots.json")["fewShots"]
        for example in examples:
            with self.subTest(question=example["question"]):
                query = example["answer"]
                aliases = dict(re.findall(r"\((\w+):(\w+)\)", query))
                self.assertTrue(aliases, "Each example must demonstrate a query.")
                for alias, label in aliases.items():
                    self.assertIn(label, properties)
                for alias, prop in re.findall(r"\b(\w+)\.(\w+)\b", query):
                    self.assertIn(alias, aliases)
                    self.assertIn(prop, properties[aliases[alias]])
                for start, edge, end in re.findall(
                    r"\((\w+)(?::\w+)?\)-\[:(\w+)\]->\((\w+)(?::\w+)?\)",
                    query,
                ):
                    self.assertEqual(
                        (aliases[start], aliases[end]),
                        self.relationships[edge],
                    )

    def test_deployment_loads_curated_config_from_requested_branch(self) -> None:
        branch = "test/legacy-ontology-agent-guidance"
        responses = {}
        for relative in ("stage_config.json", f"{SOURCE}/datasource.json", f"{SOURCE}/fewshots.json"):
            content = (CONFIG / "draft" / Path(relative)).read_bytes()
            responses[relative] = SimpleNamespace(ok=True, content=content)

        def get(url: str, **kwargs):
            self.assertIn(f"/{branch}/", url)
            return next(response for relative, response in responses.items() if url.endswith(relative))

        with patch.object(deployment.requests, "get", side_effect=get) as request:
            curated = deployment.fetch_curated_config("owner", "repo", branch)
        self.assertEqual(request.call_count, 3)
        self.assertEqual(
            curated["instructions"],
            read_json(CONFIG / "draft" / "stage_config.json")["aiInstructions"],
        )
        source = read_json(CONFIG / "draft" / SOURCE / "datasource.json")
        self.assertEqual(curated["datasource_instructions"], source["dataSourceInstructions"])
        self.assertEqual(curated["descriptions"], {
            e["display_name"]: e["description"] for e in source["elements"]
        })
        self.assertEqual(
            json.loads(curated["fewshots"]),
            read_json(CONFIG / "draft" / SOURCE / "fewshots.json"),
        )

    def test_agent_import_contains_instructions_examples_and_live_schema_ids(self) -> None:
        source = read_json(CONFIG / "draft" / SOURCE / "datasource.json")
        instructions = read_json(CONFIG / "draft" / "stage_config.json")["aiInstructions"]
        curated = {
            "instructions": instructions,
            "descriptions": {e["display_name"]: e["description"] for e in source["elements"]},
            "datasource_instructions": source["dataSourceInstructions"],
            "user_description": source["userDescription"],
            "fewshots": (CONFIG / "draft" / SOURCE / "fewshots.json").read_text(encoding="utf-8"),
        }
        entities = [(e["id"], e["name"]) for e in self.entities.values()]
        relationships = [(f"live-edge-{name}", name) for name in self.relationships]
        for existing in (None, {"id": "test-agent"}):
            with self.subTest(existing=existing):
                client = Mock(workspace_id="test-workspace")
                client.find.return_value = existing
                client.lro.return_value.json.return_value = {"id": "test-agent"}
                deployment.deploy_data_agent(
                    client, "legacy-ontology-id", deployment.ONTOLOGY_NAME,
                    entities, relationships, "HealthcareOntologyAgent_GuidanceTest", curated,
                )
                payload = client.request.call_args.kwargs["json"]
                parts = {
                    part["path"]: json.loads(base64.b64decode(part["payload"]))
                    for part in payload["definition"]["parts"]
                }
                for stage in ("draft", "published"):
                    prefix = f"Files/Config/{stage}"
                    self.assertEqual(parts[f"{prefix}/stage_config.json"]["aiInstructions"], instructions)
                    imported = parts[f"{prefix}/ontology-{deployment.ONTOLOGY_NAME}/datasource.json"]
                    self.assertEqual(imported["artifactId"], "legacy-ontology-id")
                    self.assertEqual(imported["workspaceId"], "test-workspace")
                    self.assertEqual(imported["type"], "ontology")
                    self.assertEqual(
                        {e["id"] for e in imported["elements"]},
                        {key for key, _ in entities + relationships},
                    )
                    self.assertEqual(
                        {e["display_name"]: e["description"] for e in imported["elements"]},
                        curated["descriptions"],
                    )
                    self.assertEqual(imported["dataSourceInstructions"], curated["datasource_instructions"])
                    self.assertEqual(
                        parts[f"{prefix}/ontology-{deployment.ONTOLOGY_NAME}/fewshots.json"],
                        json.loads(curated["fewshots"]),
                    )


if __name__ == "__main__":
    unittest.main()
