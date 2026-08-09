"""Deterministic, source-safe NFPA 13 definition graph projection.

This module starts downstream of NFPA definition recognition. It does not discover
terms in source text or decide which definition governs a use. Callers supply
reviewable definition records and candidate definition locators; this projection
preserves resolved, ambiguous, and unresolved states without copying source text.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import hashlib
import json
from typing import Any

GRAPH_SCHEMA = "nfpa13-definition-graph/0.1.0"
ARTIFACT_ID = "nfpa:13"
EDITION_ID = "2019"

_DEFINITION_FIELDS = {"locator", "scope_locator", "term_key", "evidence"}
_USE_FIELDS = {
    "source_locator",
    "term_key",
    "candidate_definition_locators",
    "evidence",
}


def _canonical(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _stable_id(prefix: str, value: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _evidence_span(value: Any, label: str) -> dict[str, int] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping) or set(value) != {"start", "end", "text"}:
        raise ValueError(f"{label} must contain start, end, and text")
    start, end, text = value["start"], value["end"], value["text"]
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or start < 0
        or end < start
        or not isinstance(text, str)
    ):
        raise ValueError(f"{label} is invalid")
    return {"start": start, "end": end}


def _definition(raw: Mapping[str, Any], index: int) -> dict[str, Any]:
    label = f"definitions[{index}]"
    if not isinstance(raw, Mapping):
        raise ValueError(f"{label} must be an object")
    missing, extra = _DEFINITION_FIELDS - set(raw), set(raw) - _DEFINITION_FIELDS
    if missing:
        raise ValueError(f"{label} is missing required fields: {sorted(missing)}")
    if extra:
        raise ValueError(f"{label} has unsupported fields: {sorted(extra)}")
    locator = _string(raw["locator"], f"{label}.locator")
    scope_locator = _string(raw["scope_locator"], f"{label}.scope_locator")
    term_key = _string(raw["term_key"], f"{label}.term_key")
    identity = {
        "artifact_id": ARTIFACT_ID,
        "edition_id": EDITION_ID,
        "locator": locator,
        "scope_locator": scope_locator,
        "term_key": term_key,
    }
    return {
        "id": _stable_id("nfpa13-definition", identity),
        "locator": locator,
        "scope_locator": scope_locator,
        "term_key": term_key,
        "evidence_span": _evidence_span(raw["evidence"], f"{label}.evidence"),
    }


def _use(raw: Mapping[str, Any], index: int, known: set[str]) -> dict[str, Any]:
    label = f"uses[{index}]"
    if not isinstance(raw, Mapping):
        raise ValueError(f"{label} must be an object")
    missing, extra = _USE_FIELDS - set(raw), set(raw) - _USE_FIELDS
    if missing:
        raise ValueError(f"{label} is missing required fields: {sorted(missing)}")
    if extra:
        raise ValueError(f"{label} has unsupported fields: {sorted(extra)}")
    source_locator = _string(raw["source_locator"], f"{label}.source_locator")
    term_key = _string(raw["term_key"], f"{label}.term_key")
    candidates_raw = raw["candidate_definition_locators"]
    if not isinstance(candidates_raw, list) or not all(isinstance(item, str) and item for item in candidates_raw):
        raise ValueError(f"{label}.candidate_definition_locators must be an array of strings")
    candidates = sorted(set(candidates_raw))
    for locator in candidates:
        if locator not in known:
            raise ValueError(f"{label} names unknown definition locator: {locator}")
    if not candidates:
        state = "unresolved"
    elif len(candidates) == 1:
        state = "resolved"
    else:
        state = "ambiguous"
    evidence_span = _evidence_span(raw["evidence"], f"{label}.evidence")
    identity = {
        "artifact_id": ARTIFACT_ID,
        "edition_id": EDITION_ID,
        "source_locator": source_locator,
        "term_key": term_key,
        "candidate_definition_locators": candidates,
        "resolution_state": state,
        "evidence_span": evidence_span,
    }
    return {
        "id": _stable_id("nfpa13-definition-use", identity),
        "source_locator": source_locator,
        "term_key": term_key,
        "candidate_definition_locators": candidates,
        "resolution_state": state,
        "evidence_span": evidence_span,
    }


def project_nfpa13_definitions(
    definitions: Iterable[Mapping[str, Any]],
    uses: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Project normalized NFPA 13 definitions and use candidates deterministically."""

    projected_definitions = [_definition(item, index) for index, item in enumerate(definitions)]
    by_locator: dict[str, dict[str, Any]] = {}
    for item in projected_definitions:
        locator = item["locator"]
        if locator in by_locator:
            raise ValueError(f"duplicate definition locator: {locator}")
        by_locator[locator] = item

    known = set(by_locator)
    projected_uses = [_use(item, index, known) for index, item in enumerate(uses)]
    projected_definitions.sort(key=lambda item: item["id"])
    projected_uses.sort(key=lambda item: item["id"])

    return {
        "schema": GRAPH_SCHEMA,
        "publication": {"artifact_id": ARTIFACT_ID, "edition_id": EDITION_ID},
        "definitions": projected_definitions,
        "uses": projected_uses,
        "diagnostics": [],
    }
