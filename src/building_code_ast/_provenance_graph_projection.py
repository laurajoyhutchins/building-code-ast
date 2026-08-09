"""Private normalization for provenance graph nodes and relationships."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from ._provenance_graph_support import required_string, source_safe_evidence, stable_id

STATES = {"resolved", "unresolved", "ambiguous", "nonexistent"}


def project_nodes(
    publication: Mapping[str, str],
    nodes: Iterable[Mapping[str, object]],
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    allowed = {"key", "kind", "locator", "artifact_id", "edition_id", "evidence"}
    for index, raw in enumerate(nodes):
        if not isinstance(raw, Mapping):
            raise ValueError(f"nodes[{index}] must be an object")
        if set(raw) - allowed:
            raise ValueError(f"nodes[{index}] has unsupported fields")
        key = required_string(raw.get("key"), f"nodes[{index}].key")
        if key in result:
            raise ValueError(f"duplicate node key: {key}")
        artifact = required_string(
            raw.get("artifact_id", publication["artifact_id"]),
            f"nodes[{index}].artifact_id",
        )
        edition_raw = raw.get(
            "edition_id",
            publication["edition_id"] if artifact == publication["artifact_id"] else None,
        )
        edition = (
            None
            if edition_raw is None
            else required_string(edition_raw, f"nodes[{index}].edition_id")
        )
        identity = {
            "artifact_id": artifact,
            "edition_id": edition,
            "key": key,
            "kind": required_string(raw.get("kind"), f"nodes[{index}].kind"),
            "locator": required_string(raw.get("locator"), f"nodes[{index}].locator"),
        }
        item: dict[str, object] = {"id": stable_id("provnode", identity), **identity}
        if "evidence" in raw:
            item["evidence"] = source_safe_evidence(
                raw["evidence"], f"nodes[{index}].evidence"
            )
        result[key] = item
    return result


def project_relationships(
    publication: Mapping[str, str],
    nodes: Mapping[str, Mapping[str, object]],
    relationships: Iterable[Mapping[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, set[str]]]:
    edges: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = []
    adjacency: dict[str, set[str]] = {}
    record_ids: set[str] = set()
    allowed = {
        "source_record_id",
        "type",
        "source_key",
        "target_keys",
        "resolution_state",
        "evidence",
    }
    for index, raw in enumerate(relationships):
        label = f"relationships[{index}]"
        if not isinstance(raw, Mapping):
            raise ValueError(f"{label} must be an object")
        if set(raw) - allowed:
            raise ValueError(f"{label} has unsupported fields")
        record_id = required_string(raw.get("source_record_id"), f"{label}.source_record_id")
        if record_id in record_ids:
            raise ValueError(f"duplicate source_record_id: {record_id}")
        record_ids.add(record_id)
        source_key = required_string(raw.get("source_key"), f"{label}.source_key")
        if source_key not in nodes:
            raise ValueError(f"unknown source node: {source_key}")
        raw_targets = raw.get("target_keys")
        if isinstance(raw_targets, (str, bytes)) or not isinstance(raw_targets, Sequence):
            raise ValueError(f"{label}.target_keys must be an array")
        target_keys = sorted(
            required_string(value, f"{label}.target_keys[]") for value in raw_targets
        )
        if len(target_keys) != len(set(target_keys)):
            raise ValueError(f"{label}.target_keys must not contain duplicates")
        for key in target_keys:
            if key not in nodes:
                raise ValueError(f"unknown target node: {key}")
        state = required_string(raw.get("resolution_state"), f"{label}.resolution_state")
        valid = (
            state == "resolved" and len(target_keys) == 1
            or state in {"unresolved", "nonexistent"} and not target_keys
            or state == "ambiguous" and len(target_keys) >= 2
        )
        if state not in STATES or not valid:
            raise ValueError(f"{label}.resolution_state is inconsistent with target_keys")

        source = nodes[source_key]
        targets = [nodes[key] for key in target_keys]
        target_ids = sorted(str(item["id"]) for item in targets)
        relation_type = required_string(raw.get("type"), f"{label}.type")
        identity = {
            "publication": dict(publication),
            "source_record_id": record_id,
            "type": relation_type,
            "source_node_id": source["id"],
            "target_node_ids": target_ids,
            "resolution_state": state,
        }
        edge: dict[str, object] = {
            "id": stable_id("provedge", identity),
            "source_record_id": record_id,
            "type": relation_type,
            "source_key": source_key,
            "source_node_id": source["id"],
            "target_keys": target_keys,
            "target_node_ids": target_ids,
            "resolution_state": state,
        }
        if "evidence" in raw:
            edge["evidence"] = source_safe_evidence(raw["evidence"], f"{label}.evidence")
        edges.append(edge)

        if state != "resolved":
            diagnostics.append(
                {"edge_id": edge["id"], "source_record_id": record_id, "state": state}
            )
            continue
        target = targets[0]
        internal_source = (
            source["artifact_id"] == publication["artifact_id"]
            and source["edition_id"] == publication["edition_id"]
        )
        internal_target = (
            target["artifact_id"] == publication["artifact_id"]
            and target["edition_id"] == publication["edition_id"]
        )
        if internal_source and internal_target:
            adjacency.setdefault(str(source["id"]), set()).add(str(target["id"]))
    return edges, diagnostics, adjacency
