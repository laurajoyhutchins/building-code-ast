"""Versioned applicability-scope semantics justified by NFPA 13 structure.

This contract records structural ownership of applicability evidence without
turning source proximity into project-specific applicability or compliance.
It is publication-neutral so later source-family adapters can share the same
semantic boundary.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import hashlib
import json
from typing import Any

SCHEMA = "applicability-scopes/0.1.0"
RESOLUTION_STATES = {"resolved", "ambiguous", "unsupported"}
REVIEW_STATES = {"unreviewed", "reviewed", "rejected"}
_FIELDS = {
    "owner_locator",
    "applies_to_locators",
    "resolution_state",
    "method",
    "review_status",
    "evidence",
}


def _canonical(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _stable_id(value: Mapping[str, Any]) -> str:
    return "applicability:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _span(value: Any, label: str) -> dict[str, int] | None:
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


def _record(raw: Mapping[str, Any], index: int) -> dict[str, Any]:
    label = f"scopes[{index}]"
    if not isinstance(raw, Mapping):
        raise ValueError(f"{label} must be an object")
    missing, extra = _FIELDS - set(raw), set(raw) - _FIELDS
    if missing:
        raise ValueError(f"{label} is missing required fields: {sorted(missing)}")
    if extra:
        raise ValueError(f"{label} has unsupported fields: {sorted(extra)}")

    owner = _string(raw["owner_locator"], f"{label}.owner_locator")
    applies_raw = raw["applies_to_locators"]
    if not isinstance(applies_raw, list) or not applies_raw:
        raise ValueError(f"{label}.applies_to_locators must be a non-empty array")
    if not all(isinstance(item, str) and item for item in applies_raw):
        raise ValueError(f"{label}.applies_to_locators must contain non-empty strings")
    applies_to = sorted(set(applies_raw))
    if owner in applies_to:
        raise ValueError(f"{label} owner cannot apply to itself")

    resolution = _string(raw["resolution_state"], f"{label}.resolution_state")
    if resolution not in RESOLUTION_STATES:
        raise ValueError(f"{label}.resolution_state is unsupported")
    review = _string(raw["review_status"], f"{label}.review_status")
    if review not in REVIEW_STATES:
        raise ValueError(f"{label}.review_status is unsupported")
    method = _string(raw["method"], f"{label}.method")
    evidence_span = _span(raw["evidence"], f"{label}.evidence")

    identity = {
        "owner_locator": owner,
        "applies_to_locators": applies_to,
        "resolution_state": resolution,
        "method": method,
        "review_status": review,
        "evidence_span": evidence_span,
    }
    return {"id": _stable_id(identity), **identity}


def project_applicability_scopes(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Canonicalize applicability ownership while preserving uncertainty."""

    scopes = [_record(item, index) for index, item in enumerate(records)]
    owners_by_descendant: dict[str, str] = {}
    for scope in scopes:
        for descendant in scope["applies_to_locators"]:
            prior = owners_by_descendant.get(descendant)
            if prior is not None and prior != scope["owner_locator"]:
                raise ValueError(
                    f"multiple applicability owners for {descendant}: {prior}, {scope['owner_locator']}"
                )
            owners_by_descendant[descendant] = scope["owner_locator"]

    scopes.sort(key=lambda item: item["id"])
    return {"schema": SCHEMA, "scopes": scopes, "diagnostics": []}
