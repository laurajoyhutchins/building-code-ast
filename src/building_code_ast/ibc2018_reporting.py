"""Source-safe Markdown reporting for the IBC 2018 corpus."""

from __future__ import annotations

from typing import Any, Mapping


def _count_lines(values: Mapping[str, Any]) -> list[str]:
    return [f"- {key}: **{value}**" for key, value in sorted(values.items())]


def render_coverage_markdown(coverage: Mapping[str, Any]) -> str:
    lines = [
        "# IBC 2018 Structural Coverage Report",
        "",
        f"Source SHA-256: `{coverage.get('source_sha256', '')}`",
        "",
        "## Counts",
        "",
        *_count_lines(coverage.get("counts", {})),
    ]

    incidental = coverage.get("incidental_layout_counts") or {}
    if incidental:
        lines.extend(
            [
                "",
                "## Incidental layouts",
                "",
                f"- Broad geometry policy: **{incidental.get('broad', 0)}**",
                f"- Strict row-keyed policy: **{incidental.get('strict', 0)}**",
            ]
        )

    lines.extend(["", "## Internal-reference resolution", ""])
    lines.extend(_count_lines(coverage.get("internal_reference_resolution", {})))

    chapter35 = coverage.get("chapter35", {})
    external = coverage.get("external_references", {})
    lines.extend(
        [
            "",
            "## Chapter 35 and external references",
            "",
            f"- Chapter 35 rows: **{chapter35.get('row_count', 0)}**",
            f"- Distinct observed designations with editions: **{chapter35.get('individual_designation_count', 0)}**",
            f"- Normalized external-document families: **{chapter35.get('normalized_family_count', 0)}**",
            f"- Families not detected elsewhere: **{chapter35.get('families_not_detected_elsewhere_count', 0)}**",
            f"- External citation occurrences outside Chapter 35: **{external.get('citation_occurrence_count', 0)}**",
            f"- Families matched by citation occurrences: **{external.get('matched_family_count', 0)}**",
            f"- Newly alias-matched citation occurrences: **{external.get('newly_alias_matched_occurrence_count', 0)}**",
            f"- Unmatched citation occurrences: **{external.get('unmatched_occurrence_count', 0)}**",
        ]
    )

    vector = coverage.get("vector_regions", {})
    if vector:
        lines.extend(
            [
                "",
                "## Vector drawing regions",
                "",
                f"- Source-safe vector regions: **{vector.get('record_count', 0)}**",
                f"- PDF pages containing vector regions: **{vector.get('page_count_with_regions', 0)}**",
                "- Review-state counts:",
            ]
        )
        lines.extend(f"  - {key}: **{value}**" for key, value in sorted(vector.get("review_state_counts", {}).items()))
        lines.append("- Disposition counts:")
        lines.extend(f"  - {key}: **{value}**" for key, value in sorted(vector.get("disposition_counts", {}).items()))

    review = coverage.get("review_queue", {})
    if review:
        lines.extend(
            [
                "",
                "## Human-review queue",
                "",
                f"- Total records: **{review.get('record_count', 0)}**",
            ]
        )
        lines.extend(f"- {key}: **{value}**" for key, value in sorted(review.get("priority_counts", {}).items()))

    contexts = coverage.get("counts_by_context", {})
    for name in ("tables", "figures", "incidental_layouts", "equations", "definitions", "exceptions", "vector_regions"):
        values = contexts.get(name)
        if not values:
            continue
        lines.extend(["", f"## {name.replace('_', ' ').title()} by chapter and appendix", ""])
        lines.extend(_count_lines(values))

    limitations = coverage.get("known_limitations", [])
    lines.extend(["", "## Known limitations", ""])
    lines.extend(f"- {item}" for item in limitations)
    lines.append("")
    return "\n".join(lines)
