"""Conservative mixed-source hierarchy promotion for ANSI/AISC 360-16.

This stage combines embedded-text top-level hierarchy anchors with the durable,
source-safe raster hierarchy observations produced by
``aisc360_raster_hierarchy_observation``. Generic recovery provenance is
validated by the shared recovery-observation contract; this module owns only
AISC component and locator semantics.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from .aisc360_hierarchy_characterization import (
    HierarchyPageObservation,
    characterize_hierarchy,
)
from .aisc360_raster_hierarchy_observation import (
    AISC360_COMPONENT_PAGE_COUNT,
    AISC360_DERIVATIVE_SHA256,
    AISC360_DERIVATIVE_SIZE_BYTES,
    AISC360_REPRESENTATIVE_RENDER_RECIPE,
    recovery_observation_from_source_safe_fields,
)


_DOTTED_LOCATOR_RE = re.compile(r"^\d+(?:\.\d+)+$")
_RASTER_SCHEMA = "aisc360-raster-hierarchy-observation-v1"
_AISC360_COMPONENT = "ansi-aisc-360-16"


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


def _durable_receipt_as_summary(
    raster_evidence: Mapping[str, object],
    *,
    expected_page_count: int,
) -> Mapping[str, object]:
    """Normalize the committed AISC receipt to the legacy in-memory summary shape."""

    if "observations" in raster_evidence:
        return raster_evidence
    if raster_evidence.get("schema") != _RASTER_SCHEMA:
        raise ValueError("unsupported raster hierarchy observation schema")
    if raster_evidence.get("component") != _AISC360_COMPONENT:
        raise ValueError("raster hierarchy receipt references the wrong component")

    source = raster_evidence.get("source_derivative")
    if not isinstance(source, Mapping):
        raise ValueError("raster hierarchy receipt requires source derivative identity")
    if source.get("sha256") != AISC360_DERIVATIVE_SHA256:
        raise ValueError("raster hierarchy receipt references the wrong source derivative")
    if source.get("byte_count") != AISC360_DERIVATIVE_SIZE_BYTES:
        raise ValueError("raster hierarchy receipt source derivative size is not exact")
    if source.get("page_count") != AISC360_COMPONENT_PAGE_COUNT:
        raise ValueError("raster hierarchy receipt source derivative page count is not exact")
    if expected_page_count > AISC360_COMPONENT_PAGE_COUNT:
        raise ValueError("component coverage exceeds the exact retained AISC derivative")

    boundary = raster_evidence.get("observation_boundary")
    if not isinstance(boundary, Mapping):
        raise ValueError("raster hierarchy receipt requires an observation boundary")
    if boundary.get("source_kind") != "raster_recovery":
        raise ValueError("raster hierarchy receipt source kind must remain explicit")
    if boundary.get("render_recipe") != AISC360_REPRESENTATIVE_RENDER_RECIPE:
        raise ValueError("raster hierarchy receipt does not match the declared render recipe")
    backend = boundary.get("recovery_backend")
    if not isinstance(backend, str) or not backend.strip():
        raise ValueError("raster hierarchy receipt recovery backend must be non-empty")
    if boundary.get("protected_source_text_retained") is not False:
        raise ValueError("raster hierarchy receipt must not retain protected source text")
    if boundary.get("parser_promotion_performed") is not False:
        raise ValueError("raster hierarchy receipt must be the unpromoted observation boundary")

    raw_items = raster_evidence.get("representative_observations")
    if not isinstance(raw_items, list):
        raise ValueError("raster hierarchy receipt observations must be a list")

    observations: list[dict[str, object]] = []
    for raw in raw_items:
        if not isinstance(raw, Mapping):
            raise ValueError("raster hierarchy receipt observations must be mappings")
        if "recovered_text" in raw:
            raise ValueError("raster hierarchy receipt must not retain recovered source text")
        observations.append(
            {
                "page": raw.get("page"),
                "source_kind": "raster_recovery",
                "render_sha256": raw.get("render_sha256"),
                "render_recipe": dict(AISC360_REPRESENTATIVE_RENDER_RECIPE),
                "recovery_backend": backend,
                "recovered_text_sha256": raw.get("recovered_text_sha256"),
                "dotted_hierarchy_locators": raw.get("dotted_hierarchy_locators"),
            }
        )

    return {
        "schema": _RASTER_SCHEMA,
        "source_derivative_sha256": AISC360_DERIVATIVE_SHA256,
        "render_recipe": dict(AISC360_REPRESENTATIVE_RENDER_RECIPE),
        "observations": observations,
        "parser_promotion_performed": False,
    }


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

        render_recipe = raw.get("render_recipe")
        if not isinstance(render_recipe, Mapping):
            raise ValueError("raster hierarchy observation requires a render recipe")
        backend = raw.get("recovery_backend")
        if not isinstance(backend, str) or not backend.strip():
            raise ValueError("raster hierarchy recovery backend must be non-empty")
        render_sha256 = raw.get("render_sha256")
        recovered_sha256 = raw.get("recovered_text_sha256")
        if not isinstance(render_sha256, str) or not isinstance(recovered_sha256, str):
            raise ValueError("raster hierarchy observation requires render and recovered-text digests")

        recovery_observation_from_source_safe_fields(
            page_number=page,
            source_derivative_sha256=AISC360_DERIVATIVE_SHA256,
            source_size_bytes=AISC360_DERIVATIVE_SIZE_BYTES,
            source_page_count=AISC360_COMPONENT_PAGE_COUNT,
            render_sha256=render_sha256,
            render_recipe=render_recipe,
            recovery_backend=backend,
            recovered_text_sha256=recovered_sha256,
        )

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

    ``raster_summary`` may be either the direct source-safe summary emitted by
    ``summarize_raster_hierarchy_observations`` or the durable repository receipt
    shape committed for the same observation boundary.

    Generic raster recovery identity and tooling are validated by the shared
    recovery contract. This module adds only AISC-specific image-only-page and
    dotted-locator rules. Recovered raster prose and embedded body prose never
    appear in the returned value.
    """

    ordered = _require_pages(observations, expected_page_count=expected_page_count)
    image_only_pages = {item.page_number for item in ordered if item.embedded_text is None}
    normalized_raster_summary = _durable_receipt_as_summary(
        raster_summary,
        expected_page_count=expected_page_count,
    )
    raster_items = _raster_items(
        normalized_raster_summary,
        image_only_pages=image_only_pages,
    )
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
