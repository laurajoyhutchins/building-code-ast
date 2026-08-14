"""Whole-document ASHRAE 90.1-2016 corpus measurements.

The measurement layer records only counts, locators, pages, and classification
status. It does not persist source expression from the retained standard.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import re
from typing import Any

from .ingest.ashrae901_2016 import (
    ASHRAE_90_1_2016_ARTIFACT,
    Ashrae901Observation,
    _appendix_heading,
    _appendix_match,
    _expand_appendix_observations,
    _numbered_nonprose,
    _numeric_heading,
    parse_ashrae901_2016_observations,
)
from .ingest.pdf_layout import PdfLayoutDocument, normalize_block_text


ASHRAE_90_1_2016_SOURCE_SHA256 = ASHRAE_90_1_2016_ARTIFACT.artifact_id.removeprefix("sha256:")
ASHRAE_90_1_2016_SOURCE_SIZE = 3_475_675
ASHRAE_90_1_2016_PAGE_COUNT = 388
MEASUREMENT_VERSION = "0.3.0"

_OUTLINE_NUMERIC_RE = re.compile(r"^(?P<locator>\d+(?:\.\d+)*)(?:\.)?(?:\s|$)")
_OUTLINE_APPENDIX_RE = re.compile(
    r"^(?:NORMATIVE|INFORMATIVE)\s+APPENDIX\s+(?P<letter>[A-H])\b",
    re.IGNORECASE,
)
_APPENDIX_NATIVE_OUTLINE_RE = re.compile(
    r"^(?P<locator>[A-H]\d+(?:\.\d+)*)\.?(?:\s|$)",
    re.IGNORECASE,
)


def _page_distance(candidate_pages: set[int], outline_page: int) -> tuple[int, int, int]:
    exact = 1 if outline_page in candidate_pages else 0
    near = 1 if any(abs(page - outline_page) <= 1 for page in candidate_pages) else 0
    far_only = 1 if candidate_pages and not near else 0
    return exact, near, far_only


def _classify(
    observation: Ashrae901Observation,
    text: str,
    *,
    current_appendix: str | None,
) -> tuple[str, str | None]:
    if match := _appendix_match(observation, text):
        return "appendix", match.group("letter").upper()

    appendix_heading = _appendix_heading(
        observation,
        text,
        appendix_letter=current_appendix,
    )
    if appendix_heading is not None:
        locator, _ = appendix_heading
        return "subsection", locator

    heading = _numeric_heading(
        observation,
        text,
        inside_appendix=current_appendix is not None,
    )
    if heading is not None:
        locator, _ = heading
        return ("section" if locator.count(".") == 0 else "subsection"), locator

    numbered = _numbered_nonprose(observation, text)
    if numbered is not None:
        node_type, locator = numbered
        return node_type.value, locator
    if observation.structure_hint == "graphical_region":
        return "graphical_region", None
    return "paragraph", None


def measure_ashrae901_2016_corpus(
    layout: PdfLayoutDocument,
    *,
    source_sha256: str,
    source_size: int,
) -> dict[str, Any]:
    """Measure exact-source structure without persisting source text."""

    if source_sha256 != ASHRAE_90_1_2016_SOURCE_SHA256:
        raise ValueError("measurement requires exact retained ASHRAE 90.1-2016 SHA-256")
    if source_size != ASHRAE_90_1_2016_SOURCE_SIZE:
        raise ValueError("measurement requires exact retained ASHRAE 90.1-2016 size")
    if len(layout.pages) != ASHRAE_90_1_2016_PAGE_COUNT:
        raise ValueError("measurement requires the exact 388 PDF pages")

    outline_numeric_pages: dict[str, set[int]] = defaultdict(set)
    outline_appendices: set[str] = set()
    outline_appendix_sublocators: set[str] = set()
    for item in layout.outline:
        normalized = normalize_block_text(item.title)
        if match := _OUTLINE_NUMERIC_RE.match(normalized):
            outline_numeric_pages[match.group("locator")].add(item.page_number)
        if match := _OUTLINE_APPENDIX_RE.match(normalized):
            outline_appendices.add(match.group("letter").upper())
        if match := _APPENDIX_NATIVE_OUTLINE_RE.match(normalized):
            outline_appendix_sublocators.add(match.group("locator").upper())

    raw_observations = [
        Ashrae901Observation(block=block)
        for page in layout.pages
        for block in page.blocks
    ]
    observations = _expand_appendix_observations(raw_observations)
    classifier_counts: Counter[str] = Counter()
    candidate_pages: dict[str, set[int]] = defaultdict(set)
    candidate_occurrences: Counter[str] = Counter()
    recognized_appendices: set[str] = set()
    current_appendix_sublocators: set[str] = set()
    current_appendix: str | None = None

    for observation in observations:
        block = observation.block
        text = normalize_block_text(block.text)
        if not text:
            continue
        kind, locator = _classify(
            observation,
            text,
            current_appendix=current_appendix,
        )
        classifier_counts[kind] += 1
        if kind == "appendix" and locator is not None:
            recognized_appendices.add(locator)
            current_appendix = locator
        if locator is None:
            continue
        if kind in {"section", "subsection"}:
            if locator[0].isdigit():
                candidate_pages[locator].add(block.page_number)
                candidate_occurrences[locator] += 1
            elif _APPENDIX_NATIVE_OUTLINE_RE.match(locator):
                current_appendix_sublocators.add(locator.upper())

    ast = parse_ashrae901_2016_observations(raw_observations)
    ast_numeric_locators = {
        node.locator.removeprefix("section:")
        for node in ast.walk()
        if node.locator.startswith("section:")
        and node.locator.removeprefix("section:")[:1].isdigit()
    }

    duplicate_locators = sorted(
        (locator, count)
        for locator, count in candidate_occurrences.items()
        if count > 1
    )
    matched = set(outline_numeric_pages) & set(candidate_pages)
    missing = set(outline_numeric_pages) - set(candidate_pages)
    unexpected = set(candidate_pages) - set(outline_numeric_pages)
    exact_page_matches = 0
    near_page_matches = 0
    far_only_matches = 0
    for locator in matched:
        exact, near, far_only = _page_distance(candidate_pages[locator], min(outline_numeric_pages[locator]))
        exact_page_matches += exact
        near_page_matches += near
        far_only_matches += far_only

    return {
        "measurement_version": MEASUREMENT_VERSION,
        "source_sha256": source_sha256,
        "source_size": source_size,
        "page_count": len(layout.pages),
        "source_block_count": len(raw_observations),
        "classifier_counts": {
            kind: classifier_counts.get(kind, 0)
            for kind in (
                "appendix",
                "equation",
                "figure",
                "graphical_region",
                "paragraph",
                "section",
                "subsection",
                "table",
            )
            if kind != "graphical_region" or classifier_counts.get(kind, 0)
        },
        "numeric_hierarchy": {
            "outline_unique_locators": len(outline_numeric_pages),
            "candidate_occurrences": sum(candidate_occurrences.values()),
            "candidate_unique_locators": len(candidate_pages),
            "duplicate_candidate_occurrences": sum(count - 1 for count in candidate_occurrences.values()),
            "matched_unique_locators": len(matched),
            "missing_outline_locators": len(missing),
            "unexpected_candidate_locators": len(unexpected),
            "exact_outline_page_matches": exact_page_matches,
            "near_outline_page_matches": near_page_matches,
            "far_only_outline_matches": far_only_matches,
            "first_duplicate": (
                {"locator": duplicate_locators[0][0], "occurrences": duplicate_locators[0][1]}
                if duplicate_locators
                else None
            ),
        },
        "appendix_hierarchy": {
            "outline_top_level_appendices": len(outline_appendices),
            "recognized_top_level_appendices": len(recognized_appendices),
            "outline_native_sublocators": len(outline_appendix_sublocators),
            "current_appendix_sublocator_candidates": len(current_appendix_sublocators),
        },
        "ast": {
            "node_count": sum(1 for _ in ast.walk()),
            "numeric_locator_count": len(ast_numeric_locators),
            "diagnostic_count": len(ast.diagnostics),
        },
        "whole_document_status": {
            "duplicate_locator_free": not duplicate_locators,
            "blocker": "duplicate-numeric-heading-candidate" if duplicate_locators else None,
            "locator": duplicate_locators[0][0] if duplicate_locators else None,
        },
    }
