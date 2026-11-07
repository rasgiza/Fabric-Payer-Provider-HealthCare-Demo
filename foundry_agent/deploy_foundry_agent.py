"""Deploy or update the healthcare Foundry prompt agent."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FabricIQPreviewTool, PromptAgentDefinition
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential


DEFAULT_INSTRUCTIONS = Path(__file__).with_name("orchestrator_instructions.md")


def _required(value: str | None, name: str) -> str:
    if value:
        return value
    raise ValueError(f"{name} is required. Pass it as an argument or environment variable.")


def _load_instructions(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    _, separator, instructions = content.partition("\n---\n")
    return instructions.strip() if separator else content.strip()


def _connection_name(connection_id: str) -> str:
    marker = "/connections/"
    marker_index = connection_id.lower().rfind(marker)
    if marker_index < 0:
        raise ValueError(
            "Connection IDs must be fully qualified Foundry project connection IDs."
        )
    return connection_id[marker_index + len(marker) :].strip("/")


def _connection_metadata(connection: Any) -> dict[str, str]:
    return dict(connection.metadata or {})


def _validate_fabric_iq_connection(connection: Any) -> None:
    metadata = _connection_metadata(connection)
    if metadata.get("type") != "fabric_iq_preview":
        raise ValueError(
            f"Connection '{connection.name}' is not Fabric IQ. Its metadata type "
            f"is '{metadata.get('type', '<missing>')}'. Remove any deprecated "
            "fabric_dataagent_preview connection and add Fabric IQ from OneLake Catalog."
        )
    target = str(connection.target or "")
    if "/workspaces/" not in target or "/dataagents/" not in target or not target.endswith(
        "/agent"
    ):
        raise ValueError(
            f"Connection '{connection.name}' does not target a published Fabric "
            "Data Agent endpoint."
        )


def _validate_search_connection(connection: Any) -> None:
    metadata = _connection_metadata(connection)
    if metadata.get("type") != "azure_ai_search":
        raise ValueError(
            f"Connection '{connection.name}' is not an Azure AI Search connection."
        )


def _resolve_connection(
    project: AIProjectClient,
    *,
    connection_name: str | None,
    connection_id: str | None,
    kind: str,
) -> Any:
    if connection_id:
        name_from_id = _connection_name(connection_id)
        if connection_name and connection_name != name_from_id:
            raise ValueError(
                f"{kind} connection name '{connection_name}' does not match "
                f"connection ID '{connection_id}'."
            )
        connection_name = name_from_id

    if not connection_name:
        raise ValueError(f"{kind} connection name is required.")

    try:
        connection = project.connections.get(connection_name)
    except ResourceNotFoundError as exc:
        raise ValueError(
            f"{kind} connection '{connection_name}' was not found in this "
            "Foundry project."
        ) from exc

    if connection_id and connection.id.lower() != connection_id.lower():
        raise ValueError(
            f"{kind} connection '{connection_name}' resolved to a different project."
        )
    return connection


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create a new immutable version of the healthcare Foundry prompt "
            "agent using Fabric IQ."
        )
    )
    parser.add_argument(
        "--project-endpoint",
        default=os.getenv("FOUNDRY_PROJECT_ENDPOINT"),
        help="Foundry project endpoint. Defaults to FOUNDRY_PROJECT_ENDPOINT.",
    )
    parser.add_argument(
        "--agent-name",
        default=os.getenv("FOUNDRY_AGENT_NAME", "HealthcareOrchestratorAgent2"),
    )
    parser.add_argument(
        "--model",
        default=os.getenv("FOUNDRY_MODEL_NAME", "gpt-4.1"),
        help="Existing model deployment name.",
    )
    parser.add_argument(
        "--fabric-iq-connection-id",
        default=os.getenv("FABRIC_IQ_PROJECT_CONNECTION_ID"),
        help=(
            "Optional fully qualified connection ID. Prefer "
            "--fabric-iq-connection-name for portable deployments."
        ),
    )
    parser.add_argument(
        "--fabric-iq-connection-name",
        default=os.getenv("FABRIC_IQ_CONNECTION_NAME"),
        help="Fabric IQ project connection name. Defaults to HealthcareHLSAgent.",
    )
    parser.add_argument(
        "--search-connection-id",
        default=os.getenv("AZURE_AI_SEARCH_CONNECTION_ID"),
        help=(
            "Optional fully qualified search connection ID. Prefer "
            "--search-connection-name for portable deployments."
        ),
    )
    parser.add_argument(
        "--search-connection-name",
        default=os.getenv("AZURE_AI_SEARCH_CONNECTION_NAME"),
        help="Azure AI Search project connection name.",
    )
    parser.add_argument(
        "--search-index-name",
        default=os.getenv(
            "AZURE_AI_SEARCH_INDEX_NAME", "healthcare-onelake-ks-index"
        ),
        help="Azure AI Search index name.",
    )
    parser.add_argument(
        "--instructions",
        type=Path,
        default=DEFAULT_INSTRUCTIONS,
        help="Path to the saved orchestrator instructions.",
    )
    parser.add_argument(
        "--validate-only",
        "--dry-run",
        dest="validate_only",
        action="store_true",
        help="Validate the model, connections, instructions, and tools without deploying.",
    )
    parser.add_argument(
        "--list-connections",
        action="store_true",
        help="List project connections and exit without deploying.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    project_endpoint = _required(args.project_endpoint, "FOUNDRY_PROJECT_ENDPOINT")

    instructions = _load_instructions(args.instructions)
    if not instructions:
        raise ValueError(f"No agent instructions found in {args.instructions}.")
    if "fabric_dataagent_preview" in instructions:
        raise ValueError(
            "The saved instructions still reference the deprecated "
            "fabric_dataagent_preview tool."
        )
    if "Fabric IQ" not in instructions:
        raise ValueError("The saved instructions do not identify the Fabric IQ tool.")

    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=project_endpoint, credential=credential) as project,
    ):
        if args.list_connections:
            for connection in project.connections.list():
                metadata_type = _connection_metadata(connection).get("type", "")
                print(
                    f"{connection.name}\t{connection.type}\t{metadata_type}\t"
                    f"{connection.target}"
                )
            return

        try:
            project.deployments.get(args.model)
        except ResourceNotFoundError as exc:
            raise ValueError(
                f"Model deployment '{args.model}' was not found in this Foundry project."
            ) from exc

        fabric_iq_connection = _resolve_connection(
            project,
            connection_name=(
                args.fabric_iq_connection_name
                or (None if args.fabric_iq_connection_id else "HealthcareHLSAgent")
            ),
            connection_id=args.fabric_iq_connection_id,
            kind="Fabric IQ",
        )
        _validate_fabric_iq_connection(fabric_iq_connection)

        search_connection = _resolve_connection(
            project,
            connection_name=args.search_connection_name,
            connection_id=args.search_connection_id,
            kind="Azure AI Search",
        )
        _validate_search_connection(search_connection)
        search_index_name = _required(
            args.search_index_name, "AZURE_AI_SEARCH_INDEX_NAME"
        )

        tools: list[object] = [
            {"type": "web_search_preview"},
            {
                "type": "azure_ai_search",
                "azure_ai_search": {
                    "indexes": [
                        {
                            "project_connection_id": search_connection.id,
                            "index_name": search_index_name,
                        }
                    ]
                },
            },
            FabricIQPreviewTool(
                project_connection_id=fabric_iq_connection.id,
                require_approval="never",
            ),
        ]
        definition = PromptAgentDefinition(
            model=args.model,
            instructions=instructions,
            tools=tools,
        )

        tool_types = [tool.get("type") for tool in definition.as_dict()["tools"]]
        print(f"Agent: {args.agent_name}")
        print(f"Project: {project_endpoint}")
        print(f"Model: {args.model}")
        print(f"Fabric IQ: {fabric_iq_connection.name} -> {fabric_iq_connection.target}")
        print(f"Azure AI Search: {search_connection.name} -> {search_index_name}")
        print(f"Instructions: {len(instructions)} characters")
        print(f"Tools: {', '.join(tool_types)}")

        if args.validate_only:
            print("Validation succeeded. No agent version was created.")
            return

        agent = project.agents.create_version(
            agent_name=args.agent_name,
            definition=definition,
            description=(
                "Healthcare orchestrator with Fabric IQ, Knowledge Base "
                "grounding, and web search."
            ),
        )

    print(f"Agent: {agent.name}")
    print(f"Version: {agent.version}")
    print(f"Status: {agent.status}")


if __name__ == "__main__":
    main()
