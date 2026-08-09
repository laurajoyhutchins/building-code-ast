"""Deterministic, source-safe graph projection for IBC 2018 internal references.

This module projects relationships that have already been established by the
IBC 2018 internal cross-reference inventory. It does not infer new targets,
copy target text, or elevate lexical references into reviewed semantics.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

_PUBLICATION_KEY = "ibc-2018"
_SCHEMA_VERSION = "ibc-reference-graph/0.1.0"


def _section_node_id(locator: str) -> str:
    return f"{_PUBLICATION_KEY}:section:{locator}"


def _edge_id(record: Mapping[str, Any]) -> str:
    identity = {
        "publication_key": _PUBLICATION_KEY,
        "source_record_id": str(record.get("id", "")),
        "source_section": str(record.get("source_section", "")),
        "target_kind": str(record.get("target_kind", "")),
        "raw_target": str(record.get("raw_target", "")),
        "resolved_target": record.get("resolved_target"),
        "resolution_state": str(record.get("resolution_state", "")),
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"ibc2018:reference-edge:{sha256(encoded).hexdigest()[:24]}"


def _cyclic_components(adjacency: Mapping[str, set[str]]) -> list[list[str]]:
    """Return deterministic cyclic strongly connected components as locators."""

    index = 0
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[list[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for target in sorted(adjacency.get(node, set())):
            if target not in indices:
                visit(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[target])

        if lowlinks[node] != indices[node]:
            return

        component: list[str] = []
        while stack:
            member = stack.pop()
            on_stack.remove(member)
            component.append(member)
            if member == node:
                break

        component.sort()
        if len(component) > 1:
            components.append(component)
        elif component and component[0] in adjacency.get(component[0], set()):
            components.append(component)

    all_nodes = set(adjacency)
    for targets in adjacency.values():
        all_nodes.update(targets)
    for node in sorted(all_nodes):
        if node not in indices:
            visit(node)

    components.sort()
    return components


def build_ibc2018_reference_graph(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Project reconciled IBC 2018 internal references into a stable graph.

    Only resolved section references receive target nodes. Unresolved,
    ambiguous, nonexistent, and non-section targets remain explicit edges with
    ``target=None`` plus diagnostics. The input inventory record ID remains the
    provenance identity for each relationship, while graph edge IDs are
    deterministic and independent of input order.
    """

    nodes_by_locator: dict[str, dict[str, str]] = {}
    edges: list[dict[str, Any]] = []
    diagnostics: list[dict[str, str]] = []
    adjacency: dict[str, set[str]] = {}

    for record in records:
        if record.get("record_type") != "internal_cross_reference":
            raise ValueError("IBC reference graph accepts internal_cross_reference records only")

        source_record_id = str(record.get("id", "")).strip()
        if not source_record_id.startswith("ibc2018:internal-cross-reference:"):
            raise ValueError("IBC reference graph requires an IBC 2018 inventory record ID")

        source_locator = str(record.get("source_section", "")).strip()
        target_kind = str(record.get("target_kind", "")).strip()
        raw_target = str(record.get("raw_target", "")).strip()
        state = str(record.get("resolution_state", "")).strip()
        reason = str(record.get("resolution_reason", "")).strip()
        resolved_value = record.get("resolved_target")
        resolved_target = str(resolved_value).strip() if isinstance(resolved_value, str) else ""

        source_id: str | None = None
        if source_locator:
            source_id = _section_node_id(source_locator)
            nodes_by_locator[source_locator] = {
                "id": source_id,
                "kind": "section",
                "locator": source_locator,
            }

        target_id: str | None = None
        if target_kind == "section" and state == "resolved" and resolved_target:
            target_id = _section_node_id(resolved_target)
            nodes_by_locator[resolved_target] = {
                "id": target_id,
                "kind": "section",
                "locator": resolved_target,
            }
            if source_locator:
                adjacency.setdefault(source_locator, set()).add(resolved_target)

        edge: dict[str, Any] = {
            "id": _edge_id(record),
            "source_record_id": source_record_id,
            "source": source_id,
            "target": target_id,
            "target_kind": target_kind,
            "raw_target": raw_target,
            "resolved_target": resolved_target or None,
            "resolution_state": state,
            "resolution_reason": reason or None,
            "review_state": str(record.get("review_state", "")),
        }
        source_anchor = record.get("source_anchor")
        if isinstance(source_anchor, Mapping):
            edge["source_anchor"] = dict(source_anchor)
        edges.append(edge)

        if target_id is None:
            diagnostics.append(
                {
                    "edge_id": edge["id"],
                    "source_record_id": source_record_id,
                    "state": state,
                    "target_kind": target_kind,
                    "raw_target": raw_target,
                    "reason": reason,
                }
            )

    nodes = [nodes_by_locator[locator] for locator in sorted(nodes_by_locator)]
    edges.sort(key=lambda item: (item["source_record_id"], item["id"]))
    diagnostics.sort(key=lambda item: (item["source_record_id"], item["edge_id"]))

    return {
        "schema_version": _SCHEMA_VERSION,
        "publication_key": _PUBLICATION_KEY,
        "nodes": nodes,
        "edges": edges,
        "diagnostics": diagnostics,
        "cycles": _cyclic_components(adjacency),
    }
