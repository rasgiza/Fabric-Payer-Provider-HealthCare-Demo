import base64
import copy
import io
import json
from pathlib import Path
import re
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from contextlib import redirect_stdout
import warnings


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ontology" / "Healthcare_Demo_Ontology_HLS"
sys.path.insert(0, str(ROOT / "scripts"))

import deploy_ontology_tmdl as deployment
from ontology_tmdl import LegacyOntology, build_parts


def read_json(path: str) -> dict:
    return json.loads((SOURCE / path).read_text(encoding="utf-8-sig"))


def response(payload: dict) -> Mock:
    result = Mock()
    result.json.return_value = payload
    return result


class OntologyTmdlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        manifest = read_json("manifest.json")
        cls.ontology = LegacyOntology.load(read_json, manifest)
        cls.legacy_parts = [
            {
                "path": part["path"],
                "payload": base64.b64encode((SOURCE / part["path"]).read_bytes()).decode("ascii"),
                "payloadType": "InlineBase64",
            }
            for part in manifest["exportedParts"]
        ]
        with warnings.catch_warnings(record=True) as captured:
            cls.parts = build_parts(
                cls.ontology,
                display_name=deployment.ONTOLOGY_NAME,
                sql_endpoint="gold.fabric.microsoft.com",
                database_id="sql-endpoint-id",
            )
        cls.conversion_warnings = "\n".join(str(warning.message) for warning in captured)

    def setUp(self) -> None:
        self.notebookutils = Mock()
        self.notebookutils.runtime.context = {"currentWorkspaceId": "workspace-id"}

    def test_complete_model_preserves_properties_relationships_and_directlake_bindings(self) -> None:
        texts = {
            part["path"]: base64.b64decode(part["payload"]).decode("utf-8")
            for part in self.parts
        }
        entity_names = {e["definition"]["name"] for e in self.ontology.entities}
        self.assertEqual(
            {path for path in texts if path.startswith("entities/")},
            {f"entities/{name}.tmdl" for name in entity_names},
        )
        for entity in self.ontology.entities:
            definition = entity["definition"]
            text = texts[f"entities/{definition['name']}.tmdl"]
            bound_ids = {
                binding["targetPropertyId"]
                for source in entity["bindings"]
                for binding in source["dataBindingConfiguration"]["propertyBindings"]
            }
            self.assertEqual(
                set(re.findall(r"^\tproperty (\w+)$", text, re.MULTILINE)),
                {prop["name"] for prop in definition["properties"] if prop["id"] in bound_ids},
            )
            for prop in definition["properties"]:
                if prop["id"] not in bound_ids:
                    self.assertIn(f"{definition['name']}.{prop['name']}", self.conversion_warnings)
            table = re.search(r"^\tbackingTable: (\w+)$", text, re.MULTILINE)[1]
            table_text = texts[f"tables/{table}.tmdl"]
            self.assertIn("\t\tmode: directLake", table_text)
            self.assertIn("\t\t\tschemaName: dbo", table_text)
            for column in re.findall(r"valueColumn: \w+\.(\w+)", text):
                self.assertIn(f"\tcolumn {column}\n", table_text)

        actual = set()
        for block in texts["entityRelationships.tmdl"].split("entityRelationship ")[1:]:
            name = block.splitlines()[0]
            start = re.search(r"fromEntity: (\w+)", block)[1]
            end = re.search(r"toEntity: (\w+)", block)[1]
            actual.add((start, name, end))
        expected = {
            (
                self.ontology.by_id[str(r["definition"]["source"]["entityTypeId"])]["definition"]["name"],
                r["definition"]["name"],
                self.ontology.by_id[str(r["definition"]["target"]["entityTypeId"])]["definition"]["name"],
            )
            for r in self.ontology.relationships
        }
        self.assertEqual(actual, expected)
        for table, column in re.findall(
            r"(?:fromColumn|toColumn): (\w+)\.(\w+)", texts["relationships.tmdl"]
        ):
            self.assertIn(f"\tcolumn {column}\n", texts[f"tables/{table}.tmdl"])
        self.assertIn(
            'Sql.Database("gold.fabric.microsoft.com", "sql-endpoint-id")',
            texts["expressions.tmdl"],
        )

    def test_incomplete_bindings_fail_instead_of_omitting_entities_or_relationships(self) -> None:
        for invalid in ("entity-binding", "entity-key", "relationship-binding", "value-type"):
            with self.subTest(invalid=invalid):
                ontology = copy.deepcopy(self.ontology)
                if invalid == "entity-binding":
                    ontology.entities[0]["bindings"] = []
                elif invalid == "entity-key":
                    ontology.entities[0]["definition"]["entityIdParts"] = []
                elif invalid == "relationship-binding":
                    ontology.relationships[0]["bindings"] = []
                else:
                    ontology.entities[0]["definition"]["properties"][0]["valueType"] = "Unsupported"
                with warnings.catch_warnings(record=True), self.assertRaises(ValueError):
                    build_parts(ontology, display_name="Test", sql_endpoint="server", database_id="endpoint")

    def test_create_and_update_target_only_the_new_ui_item(self) -> None:
        for exists in (False, True):
            with self.subTest(existing=exists):
                client = Mock(workspace_id="workspace-id")
                client.find.return_value = {"id": "new-ui-id"} if exists else None
                client.lro.side_effect = lambda result, label: result
                uploaded = []
                base = f"{deployment.API}/workspaces/workspace-id/ontologies"

                def request(method, url, **kwargs):
                    if method == "GET" and url == f"{base}/new-ui-id":
                        return response({"properties": {"generation": 2}})
                    if method == "POST" and url == f"{base}/new-ui-id/getDefinition":
                        return response({"definition": {"parts": uploaded[0]}})
                    target = f"{base}/new-ui-id/updateDefinition" if exists else base
                    if method == "POST" and url == target:
                        uploaded.append(kwargs["json"]["definition"]["parts"])
                        if not exists:
                            self.assertEqual(kwargs["json"]["displayName"], deployment.ONTOLOGY_NAME)
                        return response({"id": "new-ui-id"})
                    self.fail(f"Unexpected mutation or request: {method} {url}")

                client.request.side_effect = request
                with (
                    patch.object(deployment, "FabricClient", return_value=client),
                    patch.object(deployment, "resolve_gold_lakehouse", return_value=("sql-endpoint-id", "gold.fabric.microsoft.com")),
                    patch.object(deployment, "fetch_definition_parts", return_value=self.legacy_parts) as fetch,
                    redirect_stdout(io.StringIO()),
                    warnings.catch_warnings(record=True),
                ):
                    self.assertTrue(deployment.deploy(self.notebookutils, "owner", "repo", "feature/test"))
                client.find.assert_called_once_with("Ontology", deployment.ONTOLOGY_NAME)
                fetch.assert_called_once_with(client, "owner", "repo", "feature/test", deployment.ONTOLOGY_NAME)
                self.assertEqual(uploaded, [self.parts])

    def test_legacy_name_and_wrong_generation_are_rejected_before_mutation(self) -> None:
        notebookutils = self.notebookutils
        with self.assertRaisesRegex(ValueError, "different name"):
            deployment.deploy(notebookutils, "owner", "repo", ontology_name=deployment.LEGACY_ONTOLOGY_NAME)
        notebookutils.credentials.getToken.assert_not_called()
        for generation in (1, None):
            with self.subTest(generation=generation):
                client = Mock(workspace_id="workspace-id")
                client.find.return_value = {"id": "conflicting-id"}
                client.request.return_value = response({"properties": {"generation": generation}})
                with patch.object(deployment, "FabricClient", return_value=client):
                    with self.assertRaisesRegex(RuntimeError, "will not be deleted or converted"):
                        deployment.deploy(notebookutils, "owner", "repo")
                client.request.assert_called_once_with(
                    "GET", f"{deployment.API}/workspaces/workspace-id/ontologies/conflicting-id"
                )

    def test_empty_or_partial_readback_and_failed_operations_are_not_success(self) -> None:
        for stored in ([], [p for p in self.parts if p["path"] != "entityRelationships.tmdl"]):
            with self.subTest(stored_parts=len(stored)):
                client = Mock(workspace_id="workspace-id")
                client.lro.return_value = response({"definition": {"parts": stored}})
                with self.assertRaisesRegex(RuntimeError, "did not round-trip"):
                    deployment.verify_definition(client, "new-ui-id", self.parts)
        client.lro.return_value = None
        with self.assertRaisesRegex(RuntimeError, "read new-UI ontology definition failed"):
            deployment.verify_definition(client, "new-ui-id", self.parts)

    def test_sql_endpoint_id_is_used_instead_of_lakehouse_item_id(self) -> None:
        client = Mock(workspace_id="workspace-id")
        client.find.return_value = {"id": "lakehouse-item-id"}
        client.request.return_value = response({
            "properties": {"sqlEndpointProperties": {
                "id": "sql-endpoint-id", "connectionString": "gold.fabric.microsoft.com",
            }},
        })
        self.assertEqual(
            deployment.resolve_gold_lakehouse(client),
            ("sql-endpoint-id", "gold.fabric.microsoft.com"),
        )
        client.request.assert_called_once_with(
            "GET", f"{deployment.API}/workspaces/workspace-id/lakehouses/lakehouse-item-id"
        )

    def test_launcher_cell_downloads_requested_branch_and_can_be_skipped(self) -> None:
        notebook = json.loads((ROOT / "Healthcare_Launcher.ipynb").read_text(encoding="utf-8"))
        cell = next(cell for cell in notebook["cells"] if cell.get("id") == "new-ontology-ui")
        code = compile("".join(cell["source"]), "Cell 9b", "exec")
        for enabled in (False, True):
            with self.subTest(enabled=enabled), tempfile.TemporaryDirectory() as directory:
                notebookutils = SimpleNamespace(calls=[])
                modules = {
                    "deploy_ontology_agent": b"",
                    "ontology_tmdl": b"",
                    "deploy_ontology_tmdl": (
                        b"def deploy(notebookutils, **kwargs):\n"
                        b"    notebookutils.calls.append(kwargs)\n"
                        b"    return True\n"
                    ),
                }

                def download(url, **kwargs):
                    name = url.rsplit("/", 1)[-1].removesuffix(".py")
                    return Mock(content=modules[name])

                variables = {
                    "DEPLOY_NEW_ONTOLOGY": enabled,
                    "GITHUB_OWNER": "owner",
                    "GITHUB_REPO": "repo",
                    "GITHUB_BRANCH": "feature/test",
                    "ont_result": "legacy-result",
                    "ont_id": "legacy-id",
                }
                with (
                    patch.dict(sys.modules, {"notebookutils": notebookutils}),
                    patch.object(sys, "path", list(sys.path)),
                    patch("tempfile.gettempdir", return_value=directory),
                    patch("requests.get", side_effect=download) as get,
                    redirect_stdout(io.StringIO()),
                ):
                    exec(code, variables)
                self.assertEqual(variables["ont_result"], "legacy-result")
                self.assertEqual(variables["ont_id"], "legacy-id")
                self.assertEqual(variables["new_ontology_result"], "[OK]" if enabled else "[SKIP]")
                if enabled:
                    self.assertEqual(notebookutils.calls, [{
                        "owner": "owner", "repo": "repo", "branch": "feature/test",
                        "ontology_name": deployment.ONTOLOGY_NAME,
                    }])
                    self.assertEqual(get.call_count, len(modules))
                    for call in get.call_args_list:
                        self.assertTrue(call.args[0].startswith(
                            "https://raw.githubusercontent.com/owner/repo/feature/test/scripts/"
                        ))
                else:
                    get.assert_not_called()
                    self.assertEqual(notebookutils.calls, [])


if __name__ == "__main__":
    unittest.main()
