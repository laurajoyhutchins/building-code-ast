"""Publication-neutral ownership evidence for table candidate envelopes.

All bounding boxes supplied here are already expressed in a common writing
frame for their page. The module assigns geometry only; it does not infer table
continuation, headers, cells, lookup meaning, or compliance semantics.
"""

from __future__ import annotations

from dataclasses import dataclass


BBox = tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class TableCaptionAnchor:
    caption_id: str
    page_number: int
    bbox: BBox


@dataclass(frozen=True, slots=True)
class TableCandidateEnvelope:
    candidate_id: str
    page_number: int
    bbox: BBox
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TableCandidateOwnershipResult:
    assignments: tuple[tuple[str, tuple[str, ...]], ...]
    unresolved_candidate_ids: tuple[str, ...]
    ambiguous_candidate_ids: tuple[str, ...]

    def assigned_to(self, caption_id: str) -> tuple[str, ...]:
        for owner_id, candidate_ids in self.assignments:
            if owner_id == caption_id:
                return candidate_ids
        return ()


def _validate_bbox(bbox: BBox) -> None:
    x0, y0, x1, y1 = bbox
    if x1 < x0 or y1 < y0:
        raise ValueError("bbox must be ordered as (x0, y0, x1, y1)")


def _overlaps_block_axis(caption: TableCaptionAnchor, candidate: TableCandidateEnvelope, tolerance: float) -> bool:
    return (
        caption.bbox[1] <= candidate.bbox[3] + tolerance
        and caption.bbox[3] >= candidate.bbox[1] - tolerance
    )


def associate_table_candidates(
    captions: tuple[TableCaptionAnchor, ...],
    candidates: tuple[TableCandidateEnvelope, ...],
    *,
    inline_tolerance: float = 3.0,
) -> TableCandidateOwnershipResult:
    """Assign candidate envelopes by writing-frame anchor and block flow.

    A candidate first requires a caption on the same page whose inline-start
    coordinate matches within ``inline_tolerance``. A unique matching caption
    owns the candidate even when their block-axis spans overlap, which is
    necessary for captions embedded along a rotated rule frame.

    When multiple captions share the same inline anchor, an observed vector
    rule grid may disambiguate ownership when exactly one matched caption
    overlaps the candidate on the block axis. If multiple matched captions
    overlap, ownership remains ambiguous. Otherwise block-flow order partitions
    the already-matched anchor family: the latest caption ending no later than
    the candidate start wins. Ties are ambiguous. Candidates with no matching
    inline anchor remain unresolved.
    """

    if inline_tolerance < 0.0:
        raise ValueError("inline_tolerance must be non-negative")

    caption_ids = [caption.caption_id for caption in captions]
    candidate_ids = [candidate.candidate_id for candidate in candidates]
    if len(caption_ids) != len(set(caption_ids)):
        raise ValueError("caption ids must be unique")
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("candidate ids must be unique")

    for caption in captions:
        _validate_bbox(caption.bbox)
    for candidate in candidates:
        _validate_bbox(candidate.bbox)

    owned: dict[str, list[str]] = {caption.caption_id: [] for caption in captions}
    unresolved: list[str] = []
    ambiguous: list[str] = []

    for candidate in candidates:
        inline_start = candidate.bbox[0]
        anchor_matches = [
            caption
            for caption in captions
            if caption.page_number == candidate.page_number
            and abs(caption.bbox[0] - inline_start) <= inline_tolerance
        ]

        if not anchor_matches:
            unresolved.append(candidate.candidate_id)
            continue

        if len(anchor_matches) == 1:
            owned[anchor_matches[0].caption_id].append(candidate.candidate_id)
            continue

        if "vector_rule_grid" in candidate.evidence:
            overlapping = [
                caption
                for caption in anchor_matches
                if _overlaps_block_axis(caption, candidate, inline_tolerance)
            ]
            if len(overlapping) == 1:
                owned[overlapping[0].caption_id].append(candidate.candidate_id)
                continue
            if len(overlapping) > 1:
                ambiguous.append(candidate.candidate_id)
                continue

        candidate_block_start = candidate.bbox[1]
        eligible = [
            caption
            for caption in anchor_matches
            if caption.bbox[3] <= candidate_block_start + inline_tolerance
        ]
        if not eligible:
            ambiguous.append(candidate.candidate_id)
            continue

        latest_block_start = max(caption.bbox[1] for caption in eligible)
        winners = [
            caption
            for caption in eligible
            if caption.bbox[1] == latest_block_start
        ]
        if len(winners) != 1:
            ambiguous.append(candidate.candidate_id)
            continue

        owned[winners[0].caption_id].append(candidate.candidate_id)

    return TableCandidateOwnershipResult(
        assignments=tuple(
            (caption.caption_id, tuple(owned[caption.caption_id]))
            for caption in captions
        ),
        unresolved_candidate_ids=tuple(unresolved),
        ambiguous_candidate_ids=tuple(ambiguous),
    )
