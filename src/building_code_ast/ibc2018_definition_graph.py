"""Deterministic, source-safe definition graph projection for IBC 2018.

The projection consumes committed source-safe definition inventory records and
explicit definition-use candidates supplied by a caller. It does not inspect
protected source prose, discover use sites lexically, or choose among ambiguous
candidate definitions.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

_PUBLICATION_KEY = "ibc-2018"
_SCHEMA_VERSION = "ibc-definition-graph/0.1.0"
_DEFINITION_PREFIX = "ibc2018:definition:"
_SAFE_ANCHOR_KEYS = (
    "pdf_page",
    "printed_page",
    "chapter",
    "appendix",
    "bbox",
    "line_id",
    "observed_text_sha256",
)


def _graph_definition_id(source_record_id: str) -> str:
    return f"{_PUBLICATION_KEY}:definition:{source_record_id.removeprefix(_DEFINITION_PREFIX)}"


def _safe_anchor(value: object) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    return {key: value[key] for key in _SAFE_ANCHOR_KEYS if key in value}


def _use_id(use: Mapping[str, Any], candidates: Sequence[str]) -> str:
    identity = {
        "publication_key": _PUBLICATION_KEY,
        "source_locator": str(use.get("source_locator", "")),
        "source_definition_id": use.get("source_definition_id"),
        "term_key": str(use.get("term_key", "")),
        "candidate_definition_ids": list(candidates),
        "review_state": str(use.get("review_state", "")),
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"ibc2018:definition-use:{sha256(encoded).hexdigest()[:24]}"


def _cyclic_components(adjacency: Mapping[str, set[str]]) -> list[list[str]]:
    all_nodes = set(adjacency)
    reverse: dict[str, set[str]] = {}
    for source, targets in adjacency.items():
        for target in targets:
            all_nodes.add(target)
            reverse.setdefault(target, set()).add(source)

    visited: set[str] = set()
    finish_order: list[str] = []
    for start in sorted(all_nodes):
        if start in visited:
            continue
        stack: list[tuple[str, bool]] = [(start, False)]
        while stack:
            node, expanded = stack.pop()
            if expanded:
                finish_order.append(node)
                continue
            if node in visited:
                continue
            visited.add(node)
            stack.append((node, True))
            for target in reversed(sorted(adjacency.get(node, set()))):
                if target not in visited:
                    stack.append((target, False))

    assigned: set[str] = set()
    cycles: list[list[str]] = []
    for start in reversed(finish_order):
        if start in assigned:
            continue
        component: list[str] = []
        stack = [start]
        assigned.add(start)
        while stack:
            node = stack.pop()
            component.append(node)
            for source in reversed(sorted(reverse.get(node, set()))):
                if source not in assigned:
                    assigned.add(source)
                    stack.append(source)
        component.sort()
        if len(component) > 1:
            cycles.append(component)
        elif component and component[0] in adjacency.get(component[0], set()):
            cycles.append(component)

    cycles.sort()
    return cycles


def build_ibc2018_definition_graph(
    definitions: Sequence[Mapping[str, Any]],
    uses: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Project IBC definitions and explicit use candidates into a stable graph."""

    by_source_id: dict[str, dict[str, Any]] = {}
    for record in definitions:
        if record.get("record_type") != "definition":
            raise ValueError("IBC definition graph accepts definition records only")

        source_record_id = str(record.get("id", "")).strip()
        if not source_record_id.startswith(_DEFINITION_PREFIX):
            raise ValueError("IBC definition graph requires an IBC 2018 definition record ID")
        if source_record_id in by_source_id:
            raise ValueError(f"duplicate IBC definition record ID: {source_record_id}")

        normalized_term = str(record.get("normalized_term", "")).strip()
        source_section = str(record.get("source_section", "")).strip()
        scope = str(record.get("scope", "")).strip()
        definition_hash = str(record.get("definition_text_sha256", "")).strip()
        if not normalized_term or not source_section or not scope or not definition_hash:
            raise ValueError(f"incomplete IBC definition record: {source_record_id}")

        node: dict[str, Any] = {
            "id": _graph_definition_id(source_record_id),
            "source_record_id": source_record_id,
            "kind": "definition",
            "normalized_term": normalized_term,
            "observed_term": str(record.get("observed_term", "")).strip() or normalized_term,
            "source_section": source_section,
            "scope": scope,
            "definition_text_sha256": definition_hash,
            "review_state": str(record.get("review_state", "")),
        }
        anchor = _safe_anchor(record.get("source_anchor"))
        if anchor is not None:
            node["source_anchor"] = anchor
        by_source_id[source_record_id] = node

    projected_uses: list[dict[str, Any]] = []
    diagnostics: list[dict[str, str]] = []
    adjacency: dict[str, set[str]] = {}

    for use in uses:
        source_locator = str(use.get("source_locator", "")).strip()
        term_key = str(use.get("term_key", "")).strip()
        review_state = str(use.get("review_state", "")).strip()
        if not source_locator or not term_key or not review_state:
            raise ValueError("IBC definition use requires source_locator, term_key, and review_state")

        raw_candidates = use.get("candidate_definition_ids", ())
        if isinstance(raw_candidates, (str, bytes)) or not isinstance(raw_candidates, Sequence):
            raise ValueError("candidate_definition_ids must be a sequence of definition record IDs")
        candidates = sorted(str(candidate).strip() for candidate in raw_candidates)
        if len(candidates) != len(set(candidates)):
            raise ValueError("candidate_definition_ids must not contain duplicates")
        unknown = [candidate for candidate in candidates if candidate not in by_source_id]
        if unknown:
            raise ValueError(f"unknown IBC definition candidate: {unknown[0]}")

        raw_source_definition_id = use.get("source_definition_id")
        source_definition_id = (
            str(raw_source_definition_id).strip() if isinstance(raw_source_definition_id, str) else None
        )
        if source_definition_id and source_definition_id not in by_source_id:
            raise ValueError(f"unknown IBC source definition: {source_definition_id}")

        if len(candidates) == 0:
            state = "unresolved"
            target_source_id = None
        elif len(candidates) == 1:
            state = "resolved"
            target_source_id = candidates[0]
        else:
            state = "ambiguous"
            target_source_id = None

        use_id = _use_id(use, candidates)
        projected: dict[str, Any] = {
            "id": use_id,
            "source_locator": source_locator,
            "source_definition_id": source_definition_id,
            "source_definition_node_id": (
                _graph_definition_id(source_definition_id) if source_definition_id else None
            ),
            "term_key": term_key,
            "candidate_definition_ids": candidates,
            "candidate_definition_node_ids": [_graph_definition_id(candidate) for candidate in candidates],
            "target_definition_id": (
                _graph_definition_id(target_source_id) if target_source_id is not None else None
            ),
            "resolution_state": state,
            "review_state": review_state,
        }
        anchor = _safe_anchor(use.get("source_anchor"))
        if anchor is not None:
            projected["source_anchor"] = anchor
        projected_uses.append(projected)

        if state != "resolved":
            diagnostics.append(
                {
                    "use_id": use_id,
                    "source_locator": source_locator,
                    "term_key": term_key,
                    "state": state,
                }
            )
        elif source_definition_id and target_source_id:
            adjacency.setdefault(source_definition_id, set()).add(target_source_id)

    definition_nodes = sorted(
        by_source_id.values(),
        key=lambda node: (node["normalized_term"], node["source_section"], node["source_record_id"]),
    )
    projected_uses.sort(key=lambda use: (use["source_locator"], use["term_key"], use["id"]))
    diagnostics.sort(key=lambda item: (item["source_locator"], item["term_key"], item["use_id"]))

    return {
        "schema_version": _SCHEMA_VERSION,
        "publication_key": _PUBLICATION_KEY,
        "definitions": definition_nodes,
        "uses": projected_uses,
        "diagnostics": diagnostics,
        "cycles": _cyclic_components(adjacency),
    }
