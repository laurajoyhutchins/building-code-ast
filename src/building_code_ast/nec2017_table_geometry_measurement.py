"""Source-safe whole-publication table-geometry measurement for NEC 2017.

This module measures the already-landed publication-neutral geometry stack. It
records table starts, geometry rows, candidate envelopes, vector-rule evidence,
and caption ownership without reconstructing protected table content or adding
NEC-specific parsing behavior.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Sequence

from .ingest.layout_analysis import CleanedPage, ReadingOrderMode, infer_page_order
from .ingest.table_candidate_ownership import (
    TableCandidateEnvelope,
    TableCaptionAnchor,
    associate_table_candidates,
)
from .ingest.table_geometry import (
    TableCandidate,
    _rule_regions,
    detect_ruled_tables,
    detect_table_rows,
    group_table_candidates,
)

MEASUREMENT_VERSION = "0.1.0"
NEC2017_SHA256 = "603ef5c461247bacd716e3953222bfb227f1ddc780fffdbfcb90756b02c237c7"
NEC2017_SIZE_BYTES = 7_422_245
NEC2017_PAGE_COUNT = 881
IMPLEMENTATION_BASE_COMMIT = "b195c7a695b9e00ef8993fa1a4a23f8be60b5abb"
LAYOUT_ANALYSIS_BLOB = "69c9d139fa0c3272122331eda3be1a3e7181e352"
TABLE_GEOMETRY_BLOB = "6549710d958ff5ea6b0a782496ca15d8acbe20f0"
CANDIDATE_OWNERSHIP_BLOB = "bca59beea96a23743cef9f5d89b5999d75036a1f"


def _candidate_bbox(candidate: TableCandidate) -> tuple[float, float, float, float]:
    fragments = [fragment for row in candidate.rows for fragment in row.fragments]
    if fragments:
        return (
            min(fragment.bbox[0] for fragment in fragments),
            min(fragment.bbox[1] for fragment in fragments),
            max(fragment.bbox[2] for fragment in fragments),
            max(fragment.bbox[3] for fragment in fragments),
        )
    return (
        min(row.bbox[0] for row in candidate.rows),
        min(row.bbox[1] for row in candidate.rows),
        max(row.bbox[2] for row in candidate.rows),
        max(row.bbox[3] for row in candidate.rows),
    )


def _measurement_digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def measure_nec2017_table_geometry(
    pages: Sequence[CleanedPage],
    captions: Sequence[TableCaptionAnchor],
    *,
    source_sha256: str,
    source_size: int,
    unsupported_nonhorizontal_caption_starts: int = 0,
) -> dict[str, Any]:
    """Measure the exact retained NEC 2017 source with shared geometry only."""

    if source_sha256.lower() != NEC2017_SHA256 or source_size != NEC2017_SIZE_BYTES:
        raise ValueError("NEC 2017 table measurement requires the exact registered source")
    if len(pages) != NEC2017_PAGE_COUNT:
        raise ValueError(f"NEC 2017 table measurement requires {NEC2017_PAGE_COUNT} pages")
    expected_pages = tuple(range(1, NEC2017_PAGE_COUNT + 1))
    if tuple(page.page_number for page in pages) != expected_pages:
        raise ValueError("NEC 2017 table measurement requires contiguous one-based pages")
    if unsupported_nonhorizontal_caption_starts < 0:
        raise ValueError("unsupported_nonhorizontal_caption_starts must be non-negative")
    caption_ids = tuple(caption.caption_id for caption in captions)
    if len(caption_ids) != len(set(caption_ids)):
        raise ValueError("caption ids must be unique")

    row_total = 0
    grouped_rows = 0
    ruled_rows = 0
    rule_region_count = 0
    row_pages = 0
    two_column_pages = 0
    grouped: list[TableCandidate] = []
    ruled: list[TableCandidate] = []

    for page in pages:
        profile = infer_page_order(page)
        if profile.mode is ReadingOrderMode.TWO_COLUMN:
            two_column_pages += 1
        rows = detect_table_rows(page, profile)
        row_total += len(rows)
        if rows:
            row_pages += 1
        grouped_page = group_table_candidates(rows)
        grouped.extend(grouped_page)
        grouped_rows += sum(len(candidate.rows) for candidate in grouped_page)
        regions = _rule_regions(page)
        rule_region_count += len(regions)
        ruled_page = detect_ruled_tables(page)
        ruled.extend(ruled_page)
        ruled_rows += sum(len(candidate.rows) for candidate in ruled_page)

    envelopes: list[TableCandidateEnvelope] = []
    for family, candidates in (("grouped_geometry", grouped), ("vector_rule", ruled)):
        for index, candidate in enumerate(candidates):
            envelopes.append(
                TableCandidateEnvelope(
                    candidate_id=f"{family}:p{candidate.page_number}:{index}",
                    page_number=candidate.page_number,
                    bbox=_candidate_bbox(candidate),
                )
            )

    ownership = associate_table_candidates(tuple(captions), tuple(envelopes))
    assigned = {
        candidate_id
        for _caption_id, candidate_ids in ownership.assignments
        for candidate_id in candidate_ids
    }
    assignment_map = dict(ownership.assignments)
    caption_with_candidate = sum(bool(assignment_map[caption_id]) for caption_id in caption_ids)
    caption_without_candidate = len(caption_ids) - caption_with_candidate
    caption_with_multiple = sum(len(assignment_map[caption_id]) > 1 for caption_id in caption_ids)
    all_caption_occurrences = len(captions) + unsupported_nonhorizontal_caption_starts

    payload: dict[str, Any] = {
        "measurement_version": MEASUREMENT_VERSION,
        "source": {
            "file_name": "nec-2017.pdf",
            "sha256": NEC2017_SHA256,
            "size_bytes": NEC2017_SIZE_BYTES,
            "page_count": NEC2017_PAGE_COUNT,
        },
        "implementation": {
            "base_commit": IMPLEMENTATION_BASE_COMMIT,
            "layout_analysis_blob": LAYOUT_ANALYSIS_BLOB,
            "table_geometry_blob": TABLE_GEOMETRY_BLOB,
            "candidate_ownership_blob": CANDIDATE_OWNERSHIP_BLOB,
        },
        "denominators": {
            "publication_pages": NEC2017_PAGE_COUNT,
            "table_caption_occurrences": all_caption_occurrences,
            "horizontal_caption_occurrences": len(captions),
            "detected_geometry_rows": row_total,
            "rule_regions": rule_region_count,
            "candidate_envelopes": len(envelopes),
        },
        "page_measurement": {
            "caption_pages": len({caption.page_number for caption in captions}),
            "pages_completed_geometry": NEC2017_PAGE_COUNT,
            "pages_detector_error": 0,
            "pages_detector_timeout": 0,
            "pages_scanned": NEC2017_PAGE_COUNT,
            "pages_with_detected_rows": row_pages,
            "two_column_pages_completed": two_column_pages,
        },
        "table_start_family": {
            "recognized_caption_starts": all_caption_occurrences,
            "unsupported_nonhorizontal_caption_starts": unsupported_nonhorizontal_caption_starts,
        },
        "row_family": {
            "recognized_geometry_rows": row_total,
            "rows_promoted_into_grouped_candidates": grouped_rows,
            "ambiguous_ungrouped_rows": row_total - grouped_rows,
        },
        "rule_family": {
            "observed_rule_regions": rule_region_count,
            "recognized_ruled_candidates": len(ruled),
            "unsupported_rule_regions_without_reconstruction": max(0, rule_region_count - len(ruled)),
            "recognized_ruled_rows": ruled_rows,
        },
        "candidate_family": {
            "grouped_geometry_candidates": len(grouped),
            "vector_rule_candidates": len(ruled),
            "candidate_envelopes_total": len(envelopes),
            "recognized_owned_candidates": len(assigned),
            "unsupported_unresolved_candidates": len(ownership.unresolved_candidate_ids),
            "ambiguous_candidate_ownership": len(ownership.ambiguous_candidate_ids),
        },
        "caption_ownership": {
            "recognized_caption_with_candidate": caption_with_candidate,
            "unsupported_caption_without_candidate": caption_without_candidate,
            "ambiguous_caption_with_multiple_candidates": caption_with_multiple,
        },
        "limitations": [
            "geometry evidence only; no table semantics or protected table reconstruction",
            "grouped-row and vector-rule candidate families are reported separately and are not semantically deduplicated",
            "caption-to-candidate ownership assigns geometry only and does not infer continuation, headers, cells, lookup meaning, or compliance semantics",
        ],
        "parser_promotion_performed": False,
        "protected_source_expression_retained": False,
        "private_source_locator_retained": False,
    }
    payload["measurement_sha256"] = _measurement_digest(payload)
    return payload
