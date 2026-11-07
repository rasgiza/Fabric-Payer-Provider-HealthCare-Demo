from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from deploy_foundry_agent import (
    _connection_name,
    _load_instructions,
    _validate_fabric_iq_connection,
    _validate_search_connection,
)


class DeployFoundryAgentTests(unittest.TestCase):
    def test_load_instructions_removes_repository_header(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "instructions.md"
            path.write_text("# Header\n\n---\n\nUse Fabric IQ.", encoding="utf-8")

            self.assertEqual(_load_instructions(path), "Use Fabric IQ.")

    def test_connection_name_accepts_case_insensitive_resource_id(self) -> None:
        connection_id = (
            "/subscriptions/sub/resourceGroups/rg/providers/provider/accounts/account/"
            "projects/project/Connections/HealthcareHLSAgent"
        )

        self.assertEqual(_connection_name(connection_id), "HealthcareHLSAgent")

    def test_fabric_iq_connection_requires_data_agent_endpoint(self) -> None:
        connection = SimpleNamespace(
            name="HealthcareHLSAgent",
            metadata={"type": "fabric_iq_preview"},
            target=(
                "https://api.fabric.microsoft.com/v1/mcp/workspaces/workspace-id/"
                "dataagents/data-agent-id/agent"
            ),
        )

        _validate_fabric_iq_connection(connection)

    def test_deprecated_fabric_connection_is_rejected(self) -> None:
        connection = SimpleNamespace(
            name="HealthcareHLSAgent",
            metadata={"type": "fabric_dataagent_preview"},
            target="-",
        )

        with self.assertRaisesRegex(ValueError, "not Fabric IQ"):
            _validate_fabric_iq_connection(connection)

    def test_direct_ontology_connection_is_rejected(self) -> None:
        connection = SimpleNamespace(
            name="HealthcareOntology",
            metadata={"type": "fabric_iq_preview"},
            target=(
                "https://api.fabric.microsoft.com/v1/mcp/dataPlane/workspaces/"
                "workspace-id/items/item-id/ontologyEndpoint"
            ),
        )

        with self.assertRaisesRegex(ValueError, "Data Agent endpoint"):
            _validate_fabric_iq_connection(connection)

    def test_search_connection_metadata_is_required(self) -> None:
        connection = SimpleNamespace(
            name="healthcare-search",
            metadata={"type": "azure_ai_search"},
        )

        _validate_search_connection(connection)


if __name__ == "__main__":
    unittest.main()
