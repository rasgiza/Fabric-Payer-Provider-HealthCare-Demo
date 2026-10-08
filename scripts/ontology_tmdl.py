"""Convert the legacy JSON ontology export into new-experience (TMDL) definition parts.

Microsoft migrated the Fabric Ontology item to a TMDL-based definition format
("new experience"). The legacy entity-type JSON export in ``ontology/`` is still
accepted by ``updateDefinition`` but is silently discarded, which leaves the
ontology empty. This module rebuilds that same model as TMDL parts.

Reference: https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/ontology-definition

The DirectLake connection is workspace-specific, so ``sql_endpoint`` and
``database_id`` (the lakehouse's SQL analytics endpoint ID) must be resolved at
deployment time and passed in.
"""

from __future__ import annotations

import base64
import json
import uuid

# Legacy ``valueType`` -> TMDL ``dataType``.
DATA_TYPES = {
    "String": "string",
    "BigInt": "int64",
    "Double": "double",
    "DateTime": "dateTime",
    "Boolean": "boolean",
    "Object": "string",
    "Any": "string",
}

_LINEAGE_NS = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")


def _lineage(*parts: str) -> str:
    """Deterministic lineageTag so repeated deployments round-trip stably."""
    return str(uuid.uuid5(_LINEAGE_NS, "|".join(parts)))


def _tmdl_name(name: str) -> str:
    """Quote a TMDL identifier when it isn't a bare word."""
    return name if name.replace("_", "").isalnum() else f"'{name}'"


class LegacyOntology:
    """The legacy JSON export, indexed for conversion."""

    def __init__(self, entities: list[dict], relationships: list[dict]):
        self.entities = entities
        self.relationships = relationships
        self.by_id = {str(e["definition"]["id"]): e for e in entities}

    @classmethod
    def load(cls, read_json, manifest: dict) -> LegacyOntology:
        """Build from a manifest, using ``read_json(path) -> dict``."""
        entities: dict[str, dict] = {}
        relationships: dict[str, dict] = {}

        for part in manifest["exportedParts"]:
            path = part["path"]
            segments = path.split("/")
            if len(segments) < 2:
                continue
            kind, ident = segments[0], segments[1]
            bucket = entities if kind == "EntityTypes" else relationships if kind == "RelationshipTypes" else None
            if bucket is None:
                continue
            record = bucket.setdefault(ident, {"definition": None, "bindings": []})
            if segments[-1] == "definition.json" and len(segments) == 3:
                record["definition"] = read_json(path)
            elif segments[2] in ("DataBindings", "Contextualizations"):
                record["bindings"].append(read_json(path))

        return cls(
            [e for e in entities.values() if e["definition"]],
            [r for r in relationships.values() if r["definition"]],
        )


def _entity_binding(entity: dict) -> dict | None:
    """Prefer a non-time-series binding; it carries the entity's own table."""
    bindings = entity["bindings"]
    for b in bindings:
        cfg = b.get("dataBindingConfiguration", {})
        if cfg.get("dataBindingType") != "TimeSeries":
            return cfg
    return bindings[0].get("dataBindingConfiguration") if bindings else None


def build_parts(
    ontology: LegacyOntology,
    *,
    display_name: str,
    sql_endpoint: str,
    database_id: str,
    include_relationships: bool = True,
) -> list[dict]:
    """Return InlineBase64 definition parts for the new-experience ontology.

    ``database_id`` is the lakehouse's SQL analytics endpoint ID, not the
    lakehouse item ID; DirectLake addresses the endpoint.
    """
    tables: dict[str, dict] = {}          # table -> {schema, columns{name: dataType}}
    entity_files: dict[str, str] = {}     # entity name -> TMDL text
    entity_table: dict[str, str] = {}     # entity name -> backing table
    entity_key_col: dict[str, str] = {}   # entity name -> key column

    for entity in ontology.entities:
        definition = entity["definition"]
        name = definition["name"]
        cfg = _entity_binding(entity)
        if not cfg:
            continue
        source = cfg.get("sourceTableProperties", {})
        table = source.get("sourceTableName")
        if not table:
            continue

        slot = tables.setdefault(
            table,
            {"schema": source.get("sourceSchema") or "dbo", "columns": {}},
        )
        column_for = {str(b["targetPropertyId"]): b["sourceColumnName"] for b in cfg.get("propertyBindings", [])}

        properties = list(definition.get("properties") or [])
        properties += list(definition.get("timeseriesProperties") or [])

        lines = [f"entity {_tmdl_name(name)}", f"\tlineageTag: {_lineage('entity', name)}", ""]
        lines.append(f"\tbackingTable: {table}")

        key_ids = definition.get("entityIdParts") or []
        key_id = str(key_ids[0]) if key_ids else str(definition.get("displayNamePropertyId") or "")
        key_name = next((p["name"] for p in properties if str(p["id"]) == key_id), None)
        if key_name:
            lines.append(f"\tkeyProperty: {key_name}")
            entity_key_col[name] = column_for.get(key_id, key_name)
        lines.append("")

        for prop in properties:
            column = column_for.get(str(prop["id"]))
            if not column:
                continue  # unbound property has no DirectLake column to read
            data_type = DATA_TYPES.get(prop.get("valueType"), "string")
            slot["columns"].setdefault(column, data_type)
            lines += [
                f"\tproperty {_tmdl_name(prop['name'])}",
                f"\t\tdataType: {data_type}",
                f"\t\tlineageTag: {_lineage('property', name, prop['name'])}",
                "",
                "\t\tbackingConfiguration",
                f"\t\t\tvalueColumn: {table}.{column}",
                "",
            ]

        entity_files[name] = "\n".join(lines) + "\n"
        entity_table[name] = table

    # Relationships are resolved before tables are emitted, because a foreign-key
    # column may still need to be added to a table's column list.
    tom: list[str] = []
    ontology_rels: list[str] = []
    if include_relationships:
        for rel in ontology.relationships:
            definition = rel["definition"]
            name = definition["name"]
            src = ontology.by_id.get(str(definition.get("source", {}).get("entityTypeId")))
            dst = ontology.by_id.get(str(definition.get("target", {}).get("entityTypeId")))
            if not src or not dst:
                continue
            src_name = src["definition"]["name"]
            dst_name = dst["definition"]["name"]
            if src_name not in entity_table or dst_name not in entity_table:
                continue

            ctx = rel["bindings"][0] if rel["bindings"] else {}
            foreign_key = next(
                (b.get("sourceColumnName") for b in (ctx.get("targetKeyRefBindings") or [])), None
            )
            to_column = entity_key_col.get(dst_name)
            if not foreign_key or not to_column:
                continue

            from_table = entity_table[src_name]
            to_table = entity_table[dst_name]
            tables[from_table]["columns"].setdefault(foreign_key, "string")
            tables[to_table]["columns"].setdefault(to_column, "string")

            rel_name = f"rel_{src_name}_{dst_name}_{name}".lower()
            tom += [
                f"relationship {rel_name}",
                f"\tfromColumn: {from_table}.{foreign_key}",
                f"\ttoColumn: {to_table}.{to_column}",
                "",
            ]
            ontology_rels += [
                f"entityRelationship {_tmdl_name(name)}",
                f"\tlineageTag: {_lineage('entityRelationship', name, src_name, dst_name)}",
                f"\tfromEntity: {_tmdl_name(src_name)}",
                f"\ttoEntity: {_tmdl_name(dst_name)}",
                "",
                "\tbackingConfiguration",
                f"\t\trelationship: {rel_name}",
                "",
            ]

    parts: list[dict] = []

    def add(path: str, text: str) -> None:
        parts.append({
            "path": path,
            "payload": base64.b64encode(text.encode("utf-8")).decode("ascii"),
            "payloadType": "InlineBase64",
        })

    add(".platform", json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Ontology", "displayName": display_name},
        "config": {"version": "2.0", "logicalId": "00000000-0000-0000-0000-000000000000"},
    }, indent=2))

    add("database.tmdl", "database\n\tcompatibilityLevel: 1000000\n")
    add("namespaces/default.tmdl", "namespace default\n\tlineageTag: default\n")
    add("expressions.tmdl",
        "expression DatabaseQuery =\n"
        "\t\tlet\n"
        f'\t\t    database = Sql.Database("{sql_endpoint}", "{database_id}")\n'
        "\t\tin\n"
        "\t\t    database\n"
        f"\tlineageTag: {_lineage('expression', 'DatabaseQuery')}\n")

    for table, meta in sorted(tables.items()):
        lines = [f"table {table}", f"\tlineageTag: {_lineage('table', table)}", ""]
        for column, data_type in sorted(meta["columns"].items()):
            lines += [
                f"\tcolumn {_tmdl_name(column)}",
                f"\t\tdataType: {data_type}",
                f"\t\tlineageTag: {_lineage('column', table, column)}",
                f"\t\tsourceColumn: {column}",
                "",
            ]
        lines += [
            f"\tpartition {table} = entity",
            "\t\tmode: directLake",
            "\t\tsource",
            f"\t\t\tentityName: {table}",
            f"\t\t\tschemaName: {meta['schema']}",
            "\t\t\texpressionSource: DatabaseQuery",
            "",
        ]
        add(f"tables/{table}.tmdl", "\n".join(lines) + "\n")

    for name, text in sorted(entity_files.items()):
        add(f"entities/{name}.tmdl", text)

    tom_text = "\n".join(tom) + "\n" if tom else None
    rels_text = "\n".join(ontology_rels) + "\n" if ontology_rels else None
    if tom_text:
        add("relationships.tmdl", tom_text)
    if rels_text:
        add("entityRelationships.tmdl", rels_text)

    model = ["model Model", ""]
    model += [f"ref table {t}" for t in sorted(tables)]
    model += ["", "ref namespace default", ""]
    add("model.tmdl", "\n".join(model) + "\n")

    return parts
