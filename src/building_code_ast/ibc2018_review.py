"""Deterministic, source-safe prioritization for IBC 2018 human review."""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence


_PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def _assignment(
    row: Mapping[str, str], record: Mapping[str, Any] | None
) -> tuple[str, str, str, str]:
    record_type = str(row.get("record_type") or (record or {}).get("record_type") or "unknown")
    if record is None:
        return "P3", "unindexed_record", "locate source-safe inventory record", str(row.get("reason") or "unindexed_record")

    if record_type == "semantic_pilot_record":
        return (
            "P0",
            "semantic_interpretation",
            "perform domain review and record explicit reviewer sign-off",
            "semantic_interpretation_unverified",
        )

    if record_type == "vector_graphic_region_detection":
        disposition = str(record.get("disposition") or row.get("reason") or "")
        if disposition == "candidate_vector_region_unclassified":
            return (
                "P0",
                "vector_graphic_candidate",
                "inspect private page render and classify as technical graphic, tabular geometry, furniture, or rejected",
                disposition,
            )
        if disposition == "candidate_tabular_or_background_geometry":
            return (
                "P1",
                "vector_tabular_candidate",
                "compare with table inventory and reject duplicates or promote missing structures",
                disposition,
            )
        return (
            "P2",
            "vector_region",
            "confirm deterministic disposition against private page render",
            disposition or "vector_region_review",
        )

    if record_type == "external_citation_occurrence":
        if record.get("normalized_document_family_id") is None:
            return (
                "P1",
                "external_reference",
                "resolve citation alias or preserve as explicitly unmatched",
                str(record.get("normalization_reason") or "unmatched_external_citation"),
            )
        return (
            "P3",
            "external_reference",
            "spot-check normalized family linkage",
            str(record.get("normalization_reason") or "matched_external_citation"),
        )

    if record_type == "internal_cross_reference":
        state = str(record.get("resolution_state") or "unreviewed")
        if state in {"unresolved", "ambiguous", "nonexistent"}:
            return (
                "P1",
                "internal_reference",
                "inspect cited target and classify parser gap, contextual ambiguity, source defect, or valid absence",
                f"internal_reference_{state}",
            )
        return (
            "P3",
            "internal_reference",
            "spot-check resolved target",
            str(record.get("resolution_reason") or "internal_reference_resolved"),
        )

    if record_type == "incidental_layout":
        return (
            "P1",
            "incidental_layout",
            "inspect geometry and confirm broad or strict row-keyed classification",
            "incidental_layout_visual_review",
        )

    if record_type in {"table", "figure", "equation", "uncaptioned_technical_graphic_candidate"}:
        return (
            "P2",
            "primary_structure",
            "verify boundary, identifier, continuation, notes, and source attachment",
            f"{record_type}_structural_review",
        )

    if record_type in {
        "exception_block",
        "definition",
        "chapter35_referenced_standard_entry",
        "external_document_family",
        "detected_structure",
    }:
        return (
            "P2",
            "normalized_structure",
            "verify source scope, parentage, normalization, and review state",
            f"{record_type}_normalization_review",
        )

    return (
        "P3",
        "relationship_or_routine_record",
        "sample for source-anchor and relationship integrity",
        str(row.get("reason") or "routine_review"),
    )


def prioritize_review_queue(
    rows: Sequence[Mapping[str, str]],
    records_by_id: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    prioritized: list[dict[str, str]] = []
    for row in rows:
        record_id = str(row.get("record_id") or "")
        record = records_by_id.get(record_id)
        priority, category, action, reason = _assignment(row, record)
        review_state = str((record or {}).get("review_state") or row.get("review_state") or "provisional")
        prioritized.append(
            {
                "priority_band": priority,
                "evidence_category": category,
                "recommended_action": action,
                "reason": reason,
                "record_id": record_id,
                "record_type": str(row.get("record_type") or (record or {}).get("record_type") or "unknown"),
                "review_state": review_state,
            }
        )

    prioritized.sort(
        key=lambda item: (
            _PRIORITY_ORDER[item["priority_band"]],
            item["record_type"],
            item["record_id"],
        )
    )
    summary = {
        "record_count": len(prioritized),
        "priority_counts": dict(sorted(Counter(item["priority_band"] for item in prioritized).items())),
        "review_state_counts": dict(sorted(Counter(item["review_state"] for item in prioritized).items())),
        "record_type_counts": dict(sorted(Counter(item["record_type"] for item in prioritized).items())),
        "evidence_category_counts": dict(sorted(Counter(item["evidence_category"] for item in prioritized).items())),
        "policy": "deterministic risk ordering; review state is synchronized from current source-safe inventories",
    }
    return prioritized, summary
