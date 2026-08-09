"""Publication-neutral structural metadata for retrieval evidence.

This layer adds source measurements and explicitly derived structural candidates.
It does not assign provision semantics, authority, or publication roles.
"""

from __future__ import annotations

import math

from .model import SourceEvidence


def annotate_structural_metadata(
    evidence: SourceEvidence,
    *,
    page_width: float,
    page_height: float,
    font_size: float | None = None,
    body_font_size: float | None = None,
    font_name: str | None = None,
) -> SourceEvidence:
    """Return ``evidence`` enriched with observed and derived structural metadata.

    Evidence identity is unchanged because metadata is not part of the physical
    source-coordinate identity established by the retrieval evidence contract.
    """

    if not isinstance(evidence, SourceEvidence):
        raise ValueError("evidence must be SourceEvidence")
    width = _positive_float(page_width, "page_width")
    height = _positive_float(page_height, "page_height")
    normalized_font_size = (
        None if font_size is None else _positive_float(font_size, "font_size")
    )
    normalized_body_font_size = (
        None
        if body_font_size is None
        else _positive_float(body_font_size, "body_font_size")
    )
    if normalized_body_font_size is not None and normalized_font_size is None:
        raise ValueError("body_font_size requires font_size")
    if font_name is not None:
        if not isinstance(font_name, str) or not font_name.strip() or font_name != font_name.strip():
            raise ValueError("font_name must be a non-empty trimmed string")

    observed = dict(evidence.observed_metadata)
    derived = dict(evidence.derived_metadata)

    observed_additions: dict[str, str | int | float | bool | None] = {
        "layout.page_width": width,
        "layout.page_height": height,
    }
    if evidence.bbox is not None:
        x0, y0, x1, y1 = evidence.bbox
        observed_additions.update(
            {
                "layout.bbox_width": x1 - x0,
                "layout.bbox_height": y1 - y0,
                "layout.bbox_x0": x0,
                "layout.bbox_y0": y0,
            }
        )
    if normalized_font_size is not None:
        observed_additions["font.size"] = normalized_font_size
    if font_name is not None:
        observed_additions["font.name"] = font_name

    derived_additions: dict[str, str | int | float | bool | None] = {}
    if evidence.bbox is not None:
        x0, y0, x1, y1 = evidence.bbox
        derived_additions.update(
            {
                "layout.x_fraction": round(x0 / width, 6),
                "layout.y_fraction": round(y0 / height, 6),
                "layout.width_fraction": round((x1 - x0) / width, 6),
                "layout.height_fraction": round((y1 - y0) / height, 6),
            }
        )
    if normalized_font_size is not None and normalized_body_font_size is not None:
        derived_additions["font.relative_size"] = round(
            normalized_font_size / normalized_body_font_size,
            6,
        )

    text = evidence.text.strip()
    folded = text.casefold()
    if _is_heading_candidate(
        text,
        font_size=normalized_font_size,
        body_font_size=normalized_body_font_size,
    ):
        derived_additions["candidate.heading"] = True
    if folded.startswith("table ") or folded.startswith("table\n"):
        derived_additions["candidate.table"] = True
    if (
        folded.startswith("figure ")
        or folded.startswith("figure\n")
        or folded.startswith("fig. ")
    ):
        derived_additions["candidate.figure"] = True
    if folded.startswith("equation ") or folded.startswith("equation\n"):
        derived_additions["candidate.equation"] = True

    _merge_without_conflict(observed, observed_additions)
    _merge_without_conflict(derived, derived_additions)

    return SourceEvidence(
        evidence_id=evidence.evidence_id,
        source_id=evidence.source_id,
        publication_key=evidence.publication_key,
        source_sha256=evidence.source_sha256,
        pdf_page=evidence.pdf_page,
        block_index=evidence.block_index,
        text=evidence.text,
        bbox=evidence.bbox,
        extraction_method=evidence.extraction_method,
        printed_page=evidence.printed_page,
        observed_metadata=tuple(sorted(observed.items())),
        derived_metadata=tuple(sorted(derived.items())),
    )


def _positive_float(value: float, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a positive finite number")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized <= 0:
        raise ValueError(f"{label} must be a positive finite number")
    return normalized


def _merge_without_conflict(
    target: dict[str, object],
    additions: dict[str, object],
) -> None:
    for key, value in additions.items():
        if key in target and target[key] != value:
            raise ValueError(f"metadata conflict for {key}")
        target[key] = value


def _is_heading_candidate(
    text: str,
    *,
    font_size: float | None,
    body_font_size: float | None,
) -> bool:
    if not text or len(text) > 120 or text.count("\n") > 1:
        return False
    if font_size is not None and body_font_size is not None:
        if font_size / body_font_size >= 1.15:
            return True
    letters = [character for character in text if character.isalpha()]
    if not letters:
        return False
    uppercase_fraction = sum(character.isupper() for character in letters) / len(letters)
    return uppercase_fraction >= 0.8
