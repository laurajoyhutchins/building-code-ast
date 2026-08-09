"""Deterministic, source-safe graph projection for NFPA 13 relationships.

This module projects relationship records that have already crossed the NFPA 13
bundle boundary. It does not discover references, infer Annex A correspondence,
or resolve unknown target publications. The public projection intentionally
retains evidence coordinates without copying source text.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any

GRAPH_SCHEMA = "nfpa13-reference-graph/0.1.0"
ARTIFACT_ID = "nfpa:13"
EDITION_ID = "2019"
TARGET_DOMAINS = {"internal", "external_standard", "unspecified_document"}

_REQUIRED_FIELDS = {
    "type",
    "source_locator",
    "target_locator",
    "target_artifact_id",
    "target_domain",
    "resolved",
    "evidence",
}


def _canonical(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _stable_id(prefix: str, value: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def _require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _evidence_span(value: Any, label: str) -> dict[str, int] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object or null")
    if set(value) != {"start", "end", "text"}:
        raise ValueError(f"{label} must contain start, end, and text")
    start, end = value["start"], value["end"]
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or start < 0
        or end < start
        or not isinstance(value["text"], str)
    ):
        raise ValueError(f"{label} is invalid")
    return {"start": start, "end": end}


def _validate_relation(raw: Mapping[str, Any], index: int) -> dict[str, Any]:
    label = f"relations[{index}]"
    if not isinstance(raw, Mapping):
        raise ValueError(f"{label} must be an object")
    missing = _REQUIRED_FIELDS - set(raw)
    extra = set(raw) - _REQUIRED_FIELDS
    if missing:
        raise ValueError(f"{label} is missing required fields: {sorted(missing)}")
    if extra:
        raise ValueError(f"{label} has unsupported fields: {sorted(extra)}")

    relation_type = _require_string(raw["type"], f"{label}.type")
    source_locator = _require_string(raw["source_locator"], f"{label}.source_locator")
    target_locator = _require_string(raw["target_locator"], f"{label}.target_locator")
    target_domain = _require_string(raw["target_domain"], f"{label}.target_domain")
    resolved = raw["resolved"]
    target_artifact_id = raw["target_artifact_id"]

    if target_domain not in TARGET_DOMAINS:
        raise ValueError(f"{label}.target_domain is unsupported")
    if not isinstance(resolved, bool):
        raise ValueError(f"{label}.resolved must be a boolean")

    if target_domain == "internal":
        if target_artifact_id != ARTIFACT_ID:
            raise ValueError(f"{label} internal relation must target {ARTIFACT_ID}")
        if not resolved:
            raise ValueError(f"{label} internal relation must be resolved")
    elif target_domain == "external_standard":
        if not isinstance(target_artifact_id, str) or not target_artifact_id:
            raise ValueError(f"{label} external-standard relation must name a target artifact")
        if not target_locator.startswith("external:"):
            raise ValueError(f"{label} external-standard locator must start with external:")
        if not resolved:
            raise ValueError(f"{label} external-standard relation must be resolved")
    else:
        if target_artifact_id is not None:
            raise ValueError(f"{label} unresolved relation must not name a target artifact")
        if resolved:
            raise ValueError(f"{label} unspecified-document relation cannot be resolved")

    return {
        "type": relation_type,
        "source_locator": source_locator,
        "target_locator": target_locator,
        "target_artifact_id": target_artifact_id,
        "target_domain": target_domain,
        "resolved": resolved,
        "evidence_span": _evidence_span(raw["evidence"], f"{label}.evidence"),
    }


def _internal_node(locator: str) -> dict[str, Any]:
    identity = {
        "artifact_id": ARTIFACT_ID,
        "edition_id": EDITION_ID,
        "locator": locator,
        "target_domain": "internal",
    }
    return {
        "id": _stable_id("nfpa13-node", identity),
        "kind": "internal_locator",
        "artifact_id": ARTIFACT_ID,
        "edition_id": EDITION_ID,
        "locator": locator,
        "target_domain": "internal",
    }


def _target_node(relation: Mapping[str, Any]) -> dict[str, Any]:
    domain = str(relation["target_domain"])
    artifact_id = relation["target_artifact_id"]
    locator = str(relation["target_locator"])
    if domain == "internal":
        return _internal_node(locator)
    if domain == "external_standard":
        kind = "external_standard"
    else:
        kind = "unresolved_target"

    identity = {
        "artifact_id": artifact_id,
        "edition_id": None,
        "locator": locator,
        "target_domain": domain,
    }
    return {
        "id": _stable_id("nfpa13-node", identity),
        "kind": kind,
        "artifact_id": artifact_id,
        "edition_id": None,
        "locator": locator,
        "target_domain": domain,
    }


def project_nfpa13_relations(relations: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Project validated NFPA 13 relationship records into a deterministic graph.

    The function is intentionally narrower than a generic provenance graph. It
    preserves the relation vocabulary and resolution state supplied by the NFPA
    bundle and emits no new semantic edges.
    """

    validated = [_validate_relation(item, index) for index, item in enumerate(relations)]
    nodes_by_id: dict[str, dict[str, Any]] = {}
    edges_by_id: dict[str, dict[str, Any]] = {}

    for relation in validated:
        source = _internal_node(str(relation["source_locator"]))
        target = _target_node(relation)
        nodes_by_id[source["id"]] = source
        nodes_by_id[target["id"]] = target

        edge_identity = {
            "type": relation["type"],
            "source_node_id": source["id"],
            "target_node_id": target["id"],
            "source_locator": relation["source_locator"],
            "target_locator": relation["target_locator"],
            "target_artifact_id": relation["target_artifact_id"],
            "target_domain": relation["target_domain"],
            "resolution_state": "resolved" if relation["resolved"] else "unresolved",
            "evidence_span": relation["evidence_span"],
        }
        edge_id = _stable_id("nfpa13-edge", edge_identity)
        edges_by_id[edge_id] = {"id": edge_id, **edge_identity}

    nodes = sorted(nodes_by_id.values(), key=lambda item: item["id"])
    edges = sorted(edges_by_id.values(), key=lambda item: item["id"])
    return {
        "schema": GRAPH_SCHEMA,
        "publication": {"artifact_id": ARTIFACT_ID, "edition_id": EDITION_ID},
        "nodes": nodes,
        "edges": edges,
        "diagnostics": [],
    }
