"""Source-safe raster-derived hierarchy observations for ANSI/AISC 360-16.

This module is the explicit boundary between raster text recovery and hierarchy
parsing. Recovered text is transient input: the durable summary retains exact
source/render/recovery provenance, a digest of the recovered text, and only
conservative dotted structural locators. It does not persist protected source
expression or promote any observation into the Document AST.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Sequence


AISC360_DERIVATIVE_SHA256 = (
    "6ba073e6549e0c7408909cde2261f2bc393c7e6bfc63392268bd51399338e126"
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DOTTED_HIERARCHY_RE = re.compile(r"^\s*(\d+(?:\.\d+)+)\.?\s+\S")


@dataclass(frozen=True, slots=True)
class RasterHierarchyPageObservation:
    """One transient full-page raster text recovery observation."""

    page_number: int
    source_derivative_sha256: str
    render_sha256: str
    render_dpi: int
    recovery_backend: str
    recovered_text: str

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("page_number must be positive")
        if not _SHA256_RE.fullmatch(self.source_derivative_sha256):
            raise ValueError("source_derivative_sha256 must be lowercase SHA-256")
        if not _SHA256_RE.fullmatch(self.render_sha256):
            raise ValueError("render_sha256 must be lowercase SHA-256")
        if self.render_dpi < 1:
            raise ValueError("render_dpi must be positive")
        if not self.recovery_backend.strip():
            raise ValueError("recovery_backend must be non-empty")
        if not self.recovered_text:
            raise ValueError("recovered_text must be non-empty")


def _dotted_hierarchy_locators(text: str) -> list[str]:
    locators: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        match = _DOTTED_HIERARCHY_RE.match(line)
        if match is None:
            continue
        locator = match.group(1)
        if locator not in seen:
            seen.add(locator)
            locators.append(locator)
    return locators


def summarize_raster_hierarchy_observations(
    observations: Sequence[RasterHierarchyPageObservation],
) -> dict[str, object]:
    """Return source-safe raster hierarchy evidence without parser promotion.

    Every observation must refer to the exact retained AISC 360 derivative.
    Recovered text never appears in the returned value. Only a SHA-256 digest and
    conservative dotted locator candidates survive this boundary; single-level
    numbering is deliberately left unresolved rather than inferred as hierarchy.
    """

    ordered = tuple(sorted(observations, key=lambda item: item.page_number))
    if not ordered:
        raise ValueError("at least one raster hierarchy observation is required")
    if len({item.page_number for item in ordered}) != len(ordered):
        raise ValueError("each page may have at most one full-page raster observation")
    if any(item.source_derivative_sha256 != AISC360_DERIVATIVE_SHA256 for item in ordered):
        raise ValueError("raster hierarchy observation references the wrong source derivative")

    durable = []
    for item in ordered:
        durable.append(
            {
                "page": item.page_number,
                "source_kind": "raster_recovery",
                "render_sha256": item.render_sha256,
                "render_dpi": item.render_dpi,
                "recovery_backend": item.recovery_backend,
                "recovered_text_sha256": hashlib.sha256(
                    item.recovered_text.encode("utf-8")
                ).hexdigest(),
                "dotted_hierarchy_locators": _dotted_hierarchy_locators(
                    item.recovered_text
                ),
            }
        )

    return {
        "schema": "aisc360-raster-hierarchy-observation-v1",
        "source_derivative_sha256": AISC360_DERIVATIVE_SHA256,
        "observations": durable,
        "parser_promotion_performed": False,
    }
