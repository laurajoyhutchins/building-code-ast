"""Source-safe reconciliation helpers for generated IBC 2018 inventories."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence


def _add_locator(targets: set[str], value: Any) -> None:
    if isinstance(value, str) and value.strip():
        targets.add(value.strip())


def collect_known_section_targets(
    *,
    cross_references: Sequence[Mapping[str, Any]],
    tables: Sequence[Mapping[str, Any]],
    figures: Sequence[Mapping[str, Any]],
    equations: Sequence[Mapping[str, Any]],
    exceptions: Sequence[Mapping[str, Any]],
) -> set[str]:
    """Collect section locators already established by source-safe inventories."""

    targets: set[str] = set()
    for record in cross_references:
        _add_locator(targets, record.get("source_section"))
        if record.get("target_kind") == "section" and record.get("resolution_state") == "resolved":
            _add_locator(targets, record.get("resolved_target"))
    for record in tables:
        _add_locator(targets, record.get("section_context"))
    for record in figures:
        _add_locator(targets, record.get("section_context"))
    for record in equations:
        _add_locator(targets, record.get("source_section"))
    for record in exceptions:
        _add_locator(targets, record.get("parent_locator"))
    return targets


def reconcile_internal_references(
    records: Sequence[Mapping[str, Any]],
    *,
    known_section_targets: Iterable[str],
) -> list[dict[str, Any]]:
    """Add explicit resolution reasons and resolve safe section-heading prefixes."""

    known = {str(item) for item in known_section_targets}
    output: list[dict[str, Any]] = []
    for record in records:
        item = dict(record)
        kind = str(item.get("target_kind", ""))
        state = str(item.get("resolution_state", ""))
        raw_target = str(item.get("raw_target", ""))

        if kind == "section" and state == "unresolved":
            if raw_target in known:
                item["resolution_state"] = "resolved"
                item["resolved_target"] = raw_target
                item["resolution_reason"] = "exact_section_target"
            elif raw_target.isdigit() and any(
                candidate.startswith(raw_target + ".") for candidate in known
            ):
                item["resolution_state"] = "resolved"
                item["resolved_target"] = raw_target
                item["resolution_reason"] = "section_heading_prefix"
            else:
                item["resolution_reason"] = "section_target_not_indexed"
        elif state == "ambiguous":
            item["resolution_reason"] = "preserved_contextual_ambiguity"
        elif state == "nonexistent":
            item["resolution_reason"] = "target_not_in_inventory"
        elif state == "resolved":
            item["resolution_reason"] = "preserved_resolved_target"
        elif kind == "section":
            item["resolution_reason"] = "section_target_not_indexed"
        else:
            item["resolution_reason"] = "preserved_resolution_state"
        output.append(item)
    return output
