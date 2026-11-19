"""Convert the legacy JSON ontology export into new-experience (TMDL) definition parts.

The new experience requires TMDL rather than the generation-1 entity-type JSON
export in ``ontology/``. This module rebuilds that same model as TMDL parts.

Reference: https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/ontology-definition

The DirectLake connection is workspace-specific, so ``sql_endpoint`` and
``database_id`` (the lakehouse's SQL analytics endpoint ID) must be resolved at
deployment time and passed in.
"""

from __future__ import annotations

import base64
import json
import uuid
import warnings

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
    return name if name.isidentifier() else "'" + name.replace("'", "''") + "'"


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

        if any(not record["definition"] for record in [*entities.values(), *relationships.values()]):
            raise ValueError("Every entity and relationship must have a definition")
        return cls(list(entities.values()), list(relationships.values()))


def _entity_binding(entity: dict) -> dict | None:
    """Prefer a non-time-series binding; it carries the entity's own table."""
    bindings = entity["bindings"]
    for b in bindings:
        cfg = b.get("dataBindingConfiguration", {})
        if cfg.get("dataBindingType") != "TimeSeries":
            return cfg
    return None


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
    unbound_properties: list[str] = []

    for entity in ontology.entities:
        definition = entity["definition"]
        name = definition["name"]
        cfg = _entity_binding(entity)
        if not cfg:
            raise ValueError(f"{name}: a non-time-series table binding is required")
        source = cfg.get("sourceTableProperties", {})
        table = source.get("sourceTableName")
        if not table:
            raise ValueError(f"{name}: the binding has no source table")

        slot = tables.setdefault(
            table,
            {"schema": source.get("sourceSchema") or "dbo", "columns": {}},
        )
        column_for = {str(b["targetPropertyId"]): b["sourceColumnName"] for b in cfg.get("propertyBindings", [])}

        properties = list(definition.get("properties") or [])
        properties += list(definition.get("timeseriesProperties") or [])

        lines = [f"entity {_tmdl_name(name)}", f"\tlineageTag: {_lineage('entity', name)}", ""]
        lines.append(f"\tbackingTable: {_tmdl_name(table)}")

        key_ids = definition.get("entityIdParts") or []
        if len(key_ids) != 1:
            raise ValueError(f"{name}: conversion requires a single bound entity key")
        key_id = str(key_ids[0])
        key_name = next((p["name"] for p in properties if str(p["id"]) == key_id), None)
        if not key_name or key_id not in column_for:
            raise ValueError(f"{name}: the entity key is not bound to a source column")
        lines.append(f"\tkeyProperty: {_tmdl_name(key_name)}")
        entity_key_col[name] = column_for[key_id]
        lines.append("")

        for prop in properties:
            column = column_for.get(str(prop["id"]))
            if not column:
                unbound_properties.append(f"{name}.{prop['name']}")
                continue
            value_type = prop.get("valueType")
            if value_type not in DATA_TYPES:
                raise ValueError(f"{name}.{prop['name']}: unsupported value type {value_type}")
            data_type = DATA_TYPES[value_type]
            slot["columns"].setdefault(column, data_type)
            lines += [
                f"\tproperty {_tmdl_name(prop['name'])}",
                f"\t\tdataType: {data_type}",
                f"\t\tlineageTag: {_lineage('property', name, prop['name'])}",
                "",
                "\t\tbackingConfiguration",
                f"\t\t\tvalueColumn: {_tmdl_name(table)}.{_tmdl_name(column)}",
                "",
            ]

        entity_files[name] = "\n".join(lines) + "\n"
        entity_table[name] = table

    if unbound_properties:
        warnings.warn(
            "Omitting legacy properties without DirectLake column bindings: "
            + ", ".join(unbound_properties),
            stacklevel=2,
        )

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
                raise ValueError(f"{name}: relationship endpoint does not exist")
            src_name = src["definition"]["name"]
            dst_name = dst["definition"]["name"]
            if src_name not in entity_table or dst_name not in entity_table:
                raise ValueError(f"{name}: relationship endpoint has no backing table")

            if len(rel["bindings"]) != 1:
                raise ValueError(f"{name}: conversion requires one relationship binding")
            ctx = rel["bindings"][0]
            target_bindings = ctx.get("targetKeyRefBindings") or []
            if len(target_bindings) != 1:
                raise ValueError(f"{name}: conversion requires one target key binding")
            foreign_key = target_bindings[0].get("sourceColumnName")
            to_column = entity_key_col.get(dst_name)
            if not foreign_key or not to_column:
                raise ValueError(f"{name}: relationship key binding is incomplete")

            from_table = entity_table[src_name]
            to_table = entity_table[dst_name]
            if ctx.get("dataBindingTable", {}).get("sourceTableName") != from_table:
                raise ValueError(f"{name}: relationship binding must use its source entity table")
            target_type = tables[to_table]["columns"][to_column]
            source_type = tables[from_table]["columns"].setdefault(foreign_key, target_type)
            if source_type != target_type:
                raise ValueError(f"{name}: relationship key types do not match")

            rel_name = f"rel_{src_name}_{dst_name}_{name}".lower()
            tom += [
                f"relationship {rel_name}",
                f"\tfromColumn: {_tmdl_name(from_table)}.{_tmdl_name(foreign_key)}",
                f"\ttoColumn: {_tmdl_name(to_table)}.{_tmdl_name(to_column)}",
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
    escaped_server = sql_endpoint.replace('"', '""')
    escaped_database = database_id.replace('"', '""')
    add("expressions.tmdl",
        "expression DatabaseQuery =\n"
        "\t\tlet\n"
        f'\t\t    database = Sql.Database("{escaped_server}", "{escaped_database}")\n'
        "\t\tin\n"
        "\t\t    database\n"
        f"\tlineageTag: {_lineage('expression', 'DatabaseQuery')}\n")

    for table, meta in sorted(tables.items()):
        lines = [f"table {_tmdl_name(table)}", f"\tlineageTag: {_lineage('table', table)}", ""]
        for column, data_type in sorted(meta["columns"].items()):
            lines += [
                f"\tcolumn {_tmdl_name(column)}",
                f"\t\tdataType: {data_type}",
                f"\t\tlineageTag: {_lineage('column', table, column)}",
                f"\t\tsourceColumn: {_tmdl_name(column)}",
                "",
            ]
        lines += [
            f"\tpartition {_tmdl_name(table)} = entity",
            "\t\tmode: directLake",
            "\t\tsource",
            f"\t\t\tentityName: {_tmdl_name(table)}",
            f"\t\t\tschemaName: {_tmdl_name(meta['schema'])}",
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
    model += [f"ref table {_tmdl_name(t)}" for t in sorted(tables)]
    model += ["", "ref namespace default", ""]
    add("model.tmdl", "\n".join(model) + "\n")

    return parts
