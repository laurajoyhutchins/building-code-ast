"""Conservative mixed-source hierarchy promotion for ANSI/AISC 360-16.

This stage combines embedded-text top-level hierarchy anchors with the durable,
source-safe raster hierarchy observations produced by
``aisc360_raster_hierarchy_observation``. It deliberately does not accept or
persist recovered raster prose and does not yet materialize promoted candidates
as Document AST nodes.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from .aisc360_hierarchy_characterization import (
    HierarchyPageObservation,
    characterize_hierarchy,
)
from .aisc360_raster_hierarchy_observation import (
    AISC360_DERIVATIVE_SHA256,
    AISC360_REPRESENTATIVE_RENDER_RECIPE,
)


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DOTTED_LOCATOR_RE = re.compile(r"^\d+(?:\.\d+)+$")
_RASTER_SCHEMA = "aisc360-raster-hierarchy-observation-v1"


def _require_pages(
    observations: Sequence[HierarchyPageObservation],
    *,
    expected_page_count: int,
) -> tuple[HierarchyPageObservation, ...]:
    if expected_page_count < 1:
        raise ValueError("expected_page_count must be positive")
    ordered = tuple(sorted(observations, key=lambda item: item.page_number))
    expected = tuple(range(1, expected_page_count + 1))
    if tuple(item.page_number for item in ordered) != expected:
        raise ValueError("observations must cover each one-based component page exactly once")
    return ordered


def _raster_items(
    raster_summary: Mapping[str, object],
    *,
    image_only_pages: set[int],
) -> tuple[Mapping[str, object], ...]:
    if raster_summary.get("schema") != _RASTER_SCHEMA:
        raise ValueError("unsupported raster hierarchy observation schema")
    if raster_summary.get("source_derivative_sha256") != AISC360_DERIVATIVE_SHA256:
        raise ValueError("raster hierarchy summary references the wrong source derivative")
    if raster_summary.get("render_recipe") != AISC360_REPRESENTATIVE_RENDER_RECIPE:
        raise ValueError("raster hierarchy summary does not match the declared render recipe")
    if raster_summary.get("parser_promotion_performed") is not False:
        raise ValueError("raster hierarchy summary must be the unpromoted observation boundary")

    raw_items = raster_summary.get("observations")
    if not isinstance(raw_items, list):
        raise ValueError("raster hierarchy summary observations must be a list")

    items: list[Mapping[str, object]] = []
    seen_pages: set[int] = set()
    for raw in raw_items:
        if not isinstance(raw, Mapping):
            raise ValueError("raster hierarchy summary observations must be mappings")
        if "recovered_text" in raw:
            raise ValueError("raster hierarchy summary must not retain recovered source text")

        page = raw.get("page")
        if not isinstance(page, int) or page < 1:
            raise ValueError("raster hierarchy observation page must be positive")
        if page in seen_pages:
            raise ValueError("each page may have at most one durable raster hierarchy observation")
        seen_pages.add(page)
        if page not in image_only_pages:
            raise ValueError("raster hierarchy observation must reference an image-only page")
        if raw.get("source_kind") != "raster_recovery":
            raise ValueError("raster hierarchy observation source kind must remain explicit")

        render_sha256 = raw.get("render_sha256")
        recovered_sha256 = raw.get("recovered_text_sha256")
        if not isinstance(render_sha256, str) or _SHA256_RE.fullmatch(render_sha256) is None:
            raise ValueError("raster hierarchy render SHA-256 is invalid")
        if not isinstance(recovered_sha256, str) or _SHA256_RE.fullmatch(recovered_sha256) is None:
            raise ValueError("raster hierarchy recovered-text SHA-256 is invalid")
        if raw.get("render_recipe") != AISC360_REPRESENTATIVE_RENDER_RECIPE:
            raise ValueError("raster hierarchy observation does not match the declared render recipe")

        backend = raw.get("recovery_backend")
        if not isinstance(backend, str) or not backend.strip():
            raise ValueError("raster hierarchy recovery backend must be non-empty")

        locators = raw.get("dotted_hierarchy_locators")
        if not isinstance(locators, list) or any(
            not isinstance(locator, str) or _DOTTED_LOCATOR_RE.fullmatch(locator) is None
            for locator in locators
        ):
            raise ValueError("raster hierarchy locators must remain conservative dotted locators")
        if len(set(locators)) != len(locators):
            raise ValueError("raster hierarchy locators must be unique within a page observation")
        items.append(raw)

    return tuple(sorted(items, key=lambda item: int(item["page"])))


def promote_aisc360_hierarchy(
    observations: Sequence[HierarchyPageObservation],
    *,
    raster_summary: Mapping[str, object],
    expected_page_count: int = 674,
) -> dict[str, object]:
    """Promote source-safe hierarchy candidates across both evidence paths.

    Embedded text contributes only the already-characterized top-level chapter
    and appendix anchors. Raster recovery contributes only durable dotted
    locator candidates plus provenance hashes. Recovered raster prose and
    embedded body prose never appear in the returned value.

    ``combined_hierarchy_complete`` is a coverage claim only: it becomes true
    when every image-only source page has a durable raster observation. It does
    not claim semantic completeness or Document AST integration.
    """

    ordered = _require_pages(observations, expected_page_count=expected_page_count)
    image_only_pages = {
        item.page_number for item in ordered if item.embedded_text is None
    }
    raster_items = _raster_items(raster_summary, image_only_pages=image_only_pages)
    raster_pages = {int(item["page"]) for item in raster_items}

    characterization = characterize_hierarchy(
        ordered,
        raster_hierarchy_pages=tuple(sorted(raster_pages)),
    )

    candidates: list[dict[str, object]] = []
    for item in characterization["chapter_anchors"]:
        candidates.append(
            {
                "page": item["page"],
                "kind": "chapter",
                "locator": str(item["identifier"]),
                "source_kind": "embedded_text",
            }
        )
    for item in characterization["appendix_anchors"]:
        candidates.append(
            {
                "page": item["page"],
                "kind": "appendix",
                "locator": str(item["identifier"]),
                "source_kind": "embedded_text",
            }
        )
    for item in raster_items:
        for locator in item["dotted_hierarchy_locators"]:
            candidates.append(
                {
                    "page": int(item["page"]),
                    "kind": "numbered_hierarchy",
                    "locator": locator,
                    "source_kind": "raster_recovery",
                    "render_sha256": item["render_sha256"],
                    "recovered_text_sha256": item["recovered_text_sha256"],
                    "recovery_backend": item["recovery_backend"],
                }
            )

    kind_order = {"chapter": 0, "appendix": 1, "numbered_hierarchy": 2}
    candidates.sort(
        key=lambda item: (
            int(item["page"]),
            kind_order[str(item["kind"])],
            str(item["locator"]),
        )
    )

    unobserved_image_only = image_only_pages - raster_pages
    return {
        "schema": "aisc360-hierarchy-promotion-v1",
        "source_derivative_sha256": AISC360_DERIVATIVE_SHA256,
        "page_measurement": {
            "page_count": len(ordered),
            "embedded_text_page_count": len(ordered) - len(image_only_pages),
            "image_only_page_count": len(image_only_pages),
            "raster_observed_image_only_page_count": len(raster_pages),
            "unobserved_image_only_page_count": len(unobserved_image_only),
        },
        "candidates": candidates,
        "combined_hierarchy_complete": not bool(unobserved_image_only),
        "hierarchy_candidate_promotion_performed": True,
        "document_ast_promotion_performed": False,
        "next_parser_boundary": (
            "document_ast_hierarchy_promotion_review"
            if not unobserved_image_only
            else "expand_raster_observation_coverage_before_complete_hierarchy_measurement"
        ),
        "provenance": {
            "embedded_text_candidates_remain_native_pdf_text": True,
            "raster_candidates_remain_raster_recovery": True,
            "recovered_source_text_retained": False,
            "single_level_raster_numbering_promoted": False,
        },
    }
