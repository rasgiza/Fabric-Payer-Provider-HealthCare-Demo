"""
Graph Definition Builder
=========================
Generates the 4-part GraphModel definition from ontology metadata on disk.

Parts:
  1. graphType.json           — Node/edge type schema (aliases, labels, PKs, properties)
  2. graphDefinition.json     — Data mappings (property→column, node/edge tables)
  3. dataSources.json         — OneLake delta table paths
  4. stylingConfiguration.json — Circular layout & visual defaults

This module is a reusable extraction of the logic originally in
05b_deploy_graph_model.py. It can be used for both initial graph creation
and for fixing an auto-provisioned graph's entity keys, contextualizations,
and edge discovery via the updateDefinition API.

Usage:
    from clients.graph_definition_builder import GraphDefinitionBuilder

    builder = GraphDefinitionBuilder(ontology_dir, workspace_id, lakehouse_id)
    builder.load_ontology()
    parts = builder.build_all_parts()
    # parts is ready for GraphModelClient.create() or .update_definition()
"""
from __future__ import annotations

import json
import base64
import math
import uuid
from pathlib import Path

# Ontology valueType → GraphModel property type
TYPE_MAP = {
    "String": "STRING",
    "BigInt": "INT",
    "Double": "FLOAT",
    "DateTime": "DATETIME",
    "Boolean": "BOOLEAN",
    "Int": "INT",
}


class GraphDefinitionBuilder:
    """Build a 4-part GraphModel definition from ontology files on disk."""

    def __init__(self, ontology_dir: str | Path,
                 workspace_id: str, lakehouse_id: str):
        """
        Args:
            ontology_dir: Path to the ontology folder containing
                          EntityTypes/ and RelationshipTypes/ dirs.
            workspace_id: Target Fabric workspace GUID.
            lakehouse_id: Target lakehouse GUID (for abfss:// paths).
        """
        self.ontology_dir = Path(ontology_dir)
        self.workspace_id = workspace_id
        self.lakehouse_id = lakehouse_id
        self.entities: dict = {}       # id → entity metadata
        self.relationships: dict = {}  # id → relationship metadata

    # ── Load Ontology Metadata ────────────────────────────────

    def load_ontology(self):
        """
        Parse the ontology folder's EntityTypes and RelationshipTypes.

        Populates self.entities and self.relationships with structured
        metadata needed to generate graph definition parts.
        """
        entity_dir = self.ontology_dir / "EntityTypes"
        rel_dir = self.ontology_dir / "RelationshipTypes"

        if not entity_dir.exists():
            raise FileNotFoundError(f"EntityTypes dir not found: {entity_dir}")

        # ── Entity Types ──────────────────────────────────────
        for ent_folder in sorted(entity_dir.iterdir()):
            if not ent_folder.is_dir():
                continue
            defn_file = ent_folder / "definition.json"
            if not defn_file.exists():
                continue

            defn = json.loads(defn_file.read_text(encoding="utf-8-sig"))
            eid = defn["id"]
            name = defn["name"]
            pk_prop_id = (defn["entityIdParts"][0]
                          if defn.get("entityIdParts") else None)

            # Build property map {property_id → {name, type}}
            prop_map = {}
            for p in defn.get("properties", []):
                prop_map[p["id"]] = {"name": p["name"], "type": p["valueType"]}

            pk_prop_name = (prop_map[pk_prop_id]["name"]
                            if pk_prop_id and pk_prop_id in prop_map else None)

            # Load DataBinding (column mappings + source table)
            bindings = {}  # property_id → source_column_name
            source_table = None
            db_dir = ent_folder / "DataBindings"
            if db_dir.exists():
                for db_file in db_dir.glob("*.json"):
                    db = json.loads(db_file.read_text(encoding="utf-8-sig"))
                    cfg = db.get("dataBindingConfiguration", {})
                    for pb in cfg.get("propertyBindings", []):
                        bindings[pb["targetPropertyId"]] = pb["sourceColumnName"]
                    st = cfg.get("sourceTableProperties", {})
                    source_table = st.get("sourceTableName")

            # pk_col: source column for the PK (from binding)
            pk_col = bindings.get(pk_prop_id) if pk_prop_id else None

            self.entities[eid] = {
                "name": name,
                "pk_prop_name": pk_prop_name,
                "pk_col": pk_col,
                "properties": prop_map,
                "source_table": source_table,
                "bindings": bindings,
            }

        # ── Relationship Types ────────────────────────────────
        if rel_dir.exists():
            for rel_folder in sorted(rel_dir.iterdir()):
                if not rel_folder.is_dir():
                    continue
                defn_file = rel_folder / "definition.json"
                if not defn_file.exists():
                    continue

                defn = json.loads(defn_file.read_text(encoding="utf-8-sig"))
                rid = defn["id"]
                name = defn["name"]
                src_entity_id = defn["source"]["entityTypeId"]
                tgt_entity_id = defn["target"]["entityTypeId"]

                # Load Contextualization (edge table + key columns)
                ctx_table = None
                src_key_cols = []
                tgt_key_cols = []
                ctx_dir = rel_folder / "Contextualizations"
                if ctx_dir.exists():
                    for ctx_file in ctx_dir.glob("*.json"):
                        ctx = json.loads(ctx_file.read_text(encoding="utf-8-sig"))
                        ctx_table = (ctx.get("dataBindingTable", {})
                                     .get("sourceTableName"))
                        # Source key: FK column(s) in edge table → source entity
                        for skr in ctx.get("sourceKeyRefBindings", []):
                            src_key_cols.append(skr["sourceColumnName"])
                        # Target key: FK column(s) in edge table → target entity
                        for tkr in ctx.get("targetKeyRefBindings", []):
                            tgt_key_cols.append(tkr["sourceColumnName"])

                self.relationships[rid] = {
                    "name": name,
                    "source_id": src_entity_id,
                    "target_id": tgt_entity_id,
                    "ctx_table": ctx_table,
                    "src_key_cols": src_key_cols,
                    "tgt_key_cols": tgt_key_cols,
                }

        print(f"  Loaded: {len(self.entities)} entity types, "
              f"{len(self.relationships)} relationships")

    # ── Build graphType.json ──────────────────────────────────

    def build_graph_type(self) -> dict:
        """
        Build the node/edge schema.

        NodeTypes have alias, labels, primaryKeyProperties, typed properties.
        EdgeTypes have alias, labels, source/destination node type references.
        """
        node_types = []
        for eid, e in self.entities.items():
            props = []
            for pid, p in e["properties"].items():
                # Only include properties that have a data binding (skip computed)
                if pid in e["bindings"]:
                    gm_type = TYPE_MAP.get(p["type"], "STRING")
                    props.append({"name": p["name"], "type": gm_type})
            node_types.append({
                "alias": f"{e['name']}_nodeType",
                "labels": [e["name"]],
                "primaryKeyProperties": [e["pk_prop_name"]],
                "properties": props,
            })

        edge_types = []
        for rid, r in self.relationships.items():
            src_name = self.entities[r["source_id"]]["name"]
            tgt_name = self.entities[r["target_id"]]["name"]
            edge_types.append({
                "alias": f"{r['name']}_edgeType",
                "labels": [r["name"]],
                "sourceNodeType": {"alias": f"{src_name}_nodeType"},
                "destinationNodeType": {"alias": f"{tgt_name}_nodeType"},
                "properties": [],
            })

        return {
            "schemaVersion": "1.0.0",
            "nodeTypes": node_types,
            "edgeTypes": edge_types,
        }

    # ── Build graphDefinition.json ────────────────────────────

    def build_graph_definition(self) -> dict:
        """
        Build data mappings (property→column) for nodes and edges.

        NodeTables map entity properties to source columns.
        EdgeTables specify source/destination key columns for joins.
        """
        node_tables = []
        for eid, e in self.entities.items():
            mappings = []
            for pid, p in e["properties"].items():
                if pid in e["bindings"]:
                    mappings.append({
                        "propertyName": p["name"],
                        "sourceColumn": e["bindings"][pid],
                    })
            node_tables.append({
                "id": str(uuid.uuid4()),
                "nodeTypeAlias": f"{e['name']}_nodeType",
                "dataSourceName": f"{e['source_table']}_Source",
                "propertyMappings": mappings,
            })

        edge_tables = []
        for rid, r in self.relationships.items():
            # Use source entity's PK column for sourceNodeKeyColumns.
            # Ontology contextualizations may have sourceKeyRefBindings
            # duplicating the target FK; the Graph Model API requires
            # the column that identifies the SOURCE node (its PK).
            src_ent = self.entities[r["source_id"]]
            src_key = ([src_ent["pk_col"]]
                       if src_ent.get("pk_col")
                       else r["src_key_cols"])
            edge_tables.append({
                "id": str(uuid.uuid4()),
                "edgeTypeAlias": f"{r['name']}_edgeType",
                "dataSourceName": f"{r['ctx_table']}_Source",
                "sourceNodeKeyColumns": src_key,
                "targetNodeKeyColumns": r["tgt_key_cols"],
                "propertyMappings": [],
            })

        return {
            "schemaVersion": "1.0.0",
            "nodeTables": node_tables,
            "edgeTables": edge_tables,
        }

    # ── Build dataSources.json ────────────────────────────────

    def build_data_sources(self) -> dict:
        """
        Build OneLake DFS paths for each delta table.

        Path: abfss://<workspace>@onelake.dfs.fabric.microsoft.com/<lakehouse>/Tables/<table>
        """
        tables = set()
        for e in self.entities.values():
            if e["source_table"]:
                tables.add(e["source_table"])
        for r in self.relationships.values():
            if r["ctx_table"]:
                tables.add(r["ctx_table"])

        sources = []
        for tbl in sorted(tables):
            path = (f"abfss://{self.workspace_id}@onelake.dfs.fabric.microsoft.com"
                    f"/{self.lakehouse_id}/Tables/{tbl}")
            sources.append({
                "name": f"{tbl}_Source",
                "type": "DeltaTable",
                "properties": {"path": path},
            })

        return {"dataSources": sources}

    # ── Build stylingConfiguration.json ───────────────────────

    def build_styling(self) -> dict:
        """Build circular layout for the graph canvas."""
        positions = {}
        styles = {}
        n = len(self.entities)
        radius = 300
        for i, (eid, e) in enumerate(self.entities.items()):
            angle = 2 * math.pi * i / n
            alias = f"{e['name']}_nodeType"
            positions[alias] = {
                "x": int(radius + radius * math.cos(angle)),
                "y": int(radius + radius * math.sin(angle)),
            }
            styles[alias] = {"size": 30}

        # Add edge type styles
        for r in self.relationships.values():
            edge_alias = f"{r['name']}_edgeType"
            styles[edge_alias] = {"size": 30}

        return {
            "schemaVersion": "1.0.0",
            "modelLayout": {
                "positions": positions,
                "styles": styles,
                "pan": {"x": 0, "y": 0},
                "zoomLevel": 1,
            },
        }

    # ── Build .platform ────────────────────────────────────────

    def build_platform(self, display_name: str, description: str = "") -> dict:
        """
        Build the .platform metadata file required by the GraphModel API.

        The .platform part is mandatory — without it, the data-loading
        pipeline may not trigger after updateDefinition.
        """
        platform = {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/"
                       "gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {
                "type": "GraphModel",
                "displayName": display_name,
            },
            "config": {
                "version": "2.0",
                "logicalId": "00000000-0000-0000-0000-000000000000",
            },
        }
        if description:
            platform["metadata"]["description"] = description
        return platform

    # ── Build All Parts ───────────────────────────────────────

    def build_all_parts(self, display_name: str = "GraphModel",
                        description: str = "") -> list[dict]:
        """
        Generate the complete 5-part definition (4 data + .platform),
        base64-encoded and ready for the GraphModel create or
        updateDefinition API.

        The 5 parts match the official API examples:
          graphType.json, graphDefinition.json, dataSources.json,
          stylingConfiguration.json, .platform

        Args:
            display_name: Graph model display name (for .platform metadata).
            description: Optional description (for .platform metadata).

        Returns:
            List of 5 dicts with keys: path, payload (base64), payloadType.
        """
        gt = self.build_graph_type()
        gd = self.build_graph_definition()
        ds = self.build_data_sources()
        sc = self.build_styling()
        pf = self.build_platform(display_name, description)

        print(f"    graphType.json:           {len(gt['nodeTypes'])} nodeTypes, "
              f"{len(gt['edgeTypes'])} edgeTypes")
        print(f"    graphDefinition.json:     {len(gd['nodeTables'])} nodeTables, "
              f"{len(gd['edgeTables'])} edgeTables")
        print(f"    dataSources.json:         {len(ds['dataSources'])} delta tables")
        print(f"    stylingConfiguration.json: {len(sc['modelLayout']['positions'])} "
              f"node positions")
        print(f"    .platform:                type=GraphModel, name={display_name}")

        return [
            self._encode_part("graphType.json", gt),
            self._encode_part("graphDefinition.json", gd),
            self._encode_part("dataSources.json", ds),
            self._encode_part("stylingConfiguration.json", sc),
            self._encode_part(".platform", pf),
        ]

    @staticmethod
    def _encode_part(path: str, content: dict) -> dict:
        """Base64-encode a JSON object as a definition part."""
        raw = json.dumps(content, indent=2)
        b64 = base64.b64encode(raw.encode("utf-8")).decode("utf-8")
        return {"path": path, "payload": b64, "payloadType": "InlineBase64"}
