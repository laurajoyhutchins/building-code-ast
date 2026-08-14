"""Source-safe structural corpus contracts for the 2018 IBC.

This module models derived inventory evidence. It deliberately does not model
legal meaning or compliance. Source text beyond identifiers and short captions
must remain in private generated evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .ibc2018_caption_corrections import apply_caption_corrections

CORPUS_SCHEMA_VERSION = "0.1.0"
COUNTING_POLICY_VERSION = "0.1.0"
SOURCE_SHA256 = "c8f0b75522707a39daf5202edee25d7fdce6c177c382f828a6dc1dfd5cc0b18d"
SOURCE_SIZE_BYTES = 32_608_171
SOURCE_PAGE_COUNT = 761


class ReviewState(StrEnum):
    PROVISIONAL = "provisional"
    VERIFIED = "verified"
    CORRECTED = "corrected"
    SUPERSEDED = "superseded"
    DISPUTED = "disputed"
    REJECTED = "rejected"


class ResolutionState(StrEnum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"
    NONEXISTENT = "nonexistent"


@dataclass(frozen=True, slots=True)
class BoundingBox:
    x0: float
    y0: float
    x1: float
    y1: float

    @classmethod
    def from_values(cls, values: Sequence[float]) -> BoundingBox:
        if len(values) != 4:
            raise ValueError("bounding box must have four coordinates")
        x0, y0, x1, y1 = (float(value) for value in values)
        if x1 < x0 or y1 < y0:
            raise ValueError("bounding box coordinates must be ordered")
        return cls(x0, y0, x1, y1)

    def to_list(self) -> list[float]:
        return [round(self.x0, 3), round(self.y0, 3), round(self.x1, 3), round(self.y1, 3)]


@dataclass(frozen=True, slots=True)
class PageLine:
    pdf_page: int
    text: str
    bbox: BoundingBox
    line_id: str

    @property
    def column(self) -> str:
        if self.bbox.x0 < 300 and self.bbox.x1 <= 330:
            return "left"
        if self.bbox.x0 >= 300:
            return "right"
        return "full"

    def anchor(self) -> dict[str, Any]:
        return source_anchor(self.pdf_page, self.bbox, self.text, self.line_id)


CHAPTER_STARTS: Mapping[str, int] = {
    "1": 28, "2": 40, "3": 72, "4": 82, "5": 130, "6": 146,
    "7": 150, "8": 238, "9": 244, "10": 284, "11": 332,
    "12": 348, "13": 354, "14": 356, "15": 368, "16": 388,
    "17": 442, "18": 456, "19": 486, "20": 492, "21": 494,
    "22": 506, "23": 510, "24": 582, "25": 590, "26": 596,
    "27": 610, "28": 612, "29": 614, "30": 618, "31": 626,
    "32": 632, "33": 634, "34": 638, "35": 640,
}

APPENDIX_STARTS: Mapping[str, int] = {
    "A": 670, "B": 672, "C": 674, "D": 676, "E": 680,
    "F": 686, "G": 688, "H": 694, "I": 698, "J": 700,
    "K": 704, "L": 708, "M": 710, "N": 712,
}

PUBLICATION_SECTIONS: tuple[dict[str, Any], ...] = (
    {"kind": "cover_and_copyright", "pdf_pages": [1, 3], "printed_pages": [None, None]},
    {"kind": "front_matter", "pdf_pages": [4, 27], "printed_pages": ["iii", "xxvi"]},
    {"kind": "chapters", "pdf_pages": [28, 669], "printed_pages": ["1", "642"]},
    {"kind": "appendices", "pdf_pages": [670, 713], "printed_pages": ["643", "686"]},
    {"kind": "subject_index", "pdf_pages": [714, 759], "printed_pages": ["687", "732"]},
    {"kind": "trailing_blank_pages", "pdf_pages": [760, 761], "printed_pages": [None, None]},
)


def printed_page(pdf_page: int) -> str | None:
    if 4 <= pdf_page <= 27:
        romans = (
            "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii",
            "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx", "xxi",
            "xxii", "xxiii", "xxiv", "xxv", "xxvi",
        )
        return romans[pdf_page - 4]
    if 28 <= pdf_page <= 759:
        return str(pdf_page - 27)
    return None


def publication_context(pdf_page: int) -> tuple[str | None, str | None]:
    if 28 <= pdf_page < 670:
        starts = sorted(((page, number) for number, page in CHAPTER_STARTS.items()))
        eligible = [number for page, number in starts if page <= pdf_page]
        return (eligible[-1] if eligible else None), None
    if 670 <= pdf_page <= 713:
        starts = sorted(((page, letter) for letter, page in APPENDIX_STARTS.items()))
        eligible = [letter for page, letter in starts if page <= pdf_page]
        return None, (eligible[-1] if eligible else None)
    return None, None


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_id(kind: str, key: str) -> str:
    digest = hashlib.sha256(f"ibc-2018|{kind}|{key}".encode("utf-8")).hexdigest()
    return f"ibc2018:{kind}:{digest[:24]}"


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def source_anchor(
    pdf_page: int,
    bbox: BoundingBox,
    observed_text: str,
    line_id: str | None = None,
) -> dict[str, Any]:
    chapter, appendix = publication_context(pdf_page)
    return {
        "pdf_page": pdf_page,
        "printed_page": printed_page(pdf_page),
        "chapter": chapter,
        "appendix": appendix,
        "bbox": bbox.to_list(),
        "line_id": line_id,
        "observed_text_sha256": text_sha256(observed_text),
    }


def load_page_lines(path: Path) -> dict[int, tuple[PageLine, ...]]:
    pages: dict[int, tuple[PageLine, ...]] = {}
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            payload = json.loads(raw)
            pdf_page = int(payload["pdf_page"])
            lines = tuple(
                PageLine(
                    pdf_page=pdf_page,
                    text=str(item["text"]),
                    bbox=BoundingBox.from_values(item["bbox"]),
                    line_id=str(item["line_id"]),
                )
                for item in payload["lines"]
            )
            pages[pdf_page] = lines
    if sorted(pages) != list(range(1, SOURCE_PAGE_COUNT + 1)):
        raise ValueError("page-line evidence does not cover all 761 PDF pages")
    return pages


def validate_private_evidence_identity(
    pages: Mapping[int, Sequence[PageLine]],
    chapter_seed: Mapping[str, Any],
    image_regions: Sequence[Mapping[str, Any]],
) -> None:
    """Fail closed unless all private evidence inputs identify the exact source."""

    source = chapter_seed.get("source_manifest")
    if not isinstance(source, Mapping):
        raise ValueError("chapter seed is missing a source manifest")
    if source.get("sha256") != SOURCE_SHA256:
        raise ValueError("chapter seed source SHA-256 does not match the registered IBC source")
    if source.get("size_bytes") != SOURCE_SIZE_BYTES:
        raise ValueError("chapter seed source size does not match the registered IBC source")
    if source.get("page_count") != SOURCE_PAGE_COUNT:
        raise ValueError("chapter seed page count does not match the registered IBC source")
    if source.get("edition") != "2018":
        raise ValueError("chapter seed edition is not 2018")
    expected_pages = list(range(1, SOURCE_PAGE_COUNT + 1))
    if sorted(pages) != expected_pages:
        raise ValueError("page-line evidence does not cover the exact source page range")
    image_pages = sorted(int(item.get("pdf_page", 0)) for item in image_regions)
    if image_pages != expected_pages:
        raise ValueError("image-region evidence does not cover the exact source page range")


_SECTION_RE = re.compile(
    r"^(?:\[[A-Z]{1,3}\]\s*)?"
    r"(?P<locator>(?:[A-N])?\d{1,4}(?:\.\d+[A-Za-z]?(?:\([A-Za-z0-9]+\))*)+)\s+"
)


def normalize_locator(value: str) -> str:
    compact = re.sub(r"(?<=\d)\s+(?=\d)", "", value.strip())
    return compact.replace("(1 )", "(1)").replace("(2 )", "(2)")


def collect_section_targets(pages: Mapping[int, Sequence[PageLine]]) -> set[str]:
    targets: set[str] = set()
    for page_number in range(28, 714):
        for line in pages[page_number]:
            match = _SECTION_RE.match(line.text)
            if match:
                targets.add(normalize_locator(match.group("locator")))
    return targets


def build_line_locator_index(
    pages: Mapping[int, Sequence[PageLine]],
) -> dict[str, str | None]:
    """Map each evidence line to the nearest preceding provision locator."""

    result: dict[str, str | None] = {}
    prior_by_column: dict[str, str | None] = {"left": None, "right": None, "full": None}
    for pdf_page in range(1, SOURCE_PAGE_COUNT + 1):
        running = dict(prior_by_column)
        for line in sorted(pages[pdf_page], key=lambda item: (item.bbox.y0, item.bbox.x0)):
            match = _SECTION_RE.match(line.text)
            if match:
                running[line.column] = normalize_locator(match.group("locator"))
            result[line.line_id] = running.get(line.column) or running.get("full")
        prior_by_column.update(running)
    return result


def union_bbox(lines: Iterable[PageLine]) -> BoundingBox:
    material = tuple(lines)
    if not material:
        raise ValueError("cannot union an empty line set")
    return BoundingBox(
        min(item.bbox.x0 for item in material),
        min(item.bbox.y0 for item in material),
        max(item.bbox.x1 for item in material),
        max(item.bbox.y1 for item in material),
    )

_CAPTION_RE = re.compile(
    r"^(?P<designation>\[[A-Z]{1,3}\]\s*)?"
    r"(?P<kind>TABLE|FIGURE)\s+"
    r"(?P<identifier>(?:\d+-[A-Z]|[A-Z]\d{2,4}(?:\.\d+)*(?:\([A-Za-z0-9]+\))*|"
    r"\d+(?:\.\d+)*(?:\([A-Za-z0-9]+\))*))(?P<suffix>.*)$"
)


def _caption_identifier(text: str, *, pdf_page: int) -> tuple[str, str, str, str] | None:
    match = _CAPTION_RE.match(text)
    if not match:
        return None
    kind = match.group("kind").lower()
    identifier = normalize_locator(match.group("identifier"))
    suffix = match.group("suffix").strip()
    designation = (match.group("designation") or "").strip()
    return apply_caption_corrections(
        text=text,
        pdf_page=pdf_page,
        kind=kind,
        identifier=identifier,
        suffix=suffix,
        designation=designation,
    )


def _short_caption(lines: Sequence[PageLine], index: int) -> str | None:
    marker = lines[index]
    parts: list[str] = []
    for candidate in lines[index + 1:index + 9]:
        if candidate.bbox.y0 - marker.bbox.y1 > 38:
            break
        if (
            candidate.column != marker.column
            and marker.column != "full"
            and candidate.column != "full"
        ):
            continue
        text = candidate.text.strip()
        if _CAPTION_RE.match(text):
            continue
        if _SECTION_RE.match(text):
            break
        if text.startswith(("For SI:", "Exception:", "Exceptions:", "EDUFIRE")):
            break
        if len(text) > 220:
            break
        if text.upper() == text or len(parts) == 0:
            parts.append(text)
        if sum(len(item) for item in parts) > 240:
            break
    caption = " ".join(parts).strip()
    return caption[:280] if caption else None


def inventory_captions(
    pages: Mapping[int, Sequence[PageLine]],
    kind: str,
) -> list[dict[str, Any]]:
    if kind not in {"table", "figure"}:
        raise ValueError("kind must be table or figure")
    locator_by_line = build_line_locator_index(pages)
    occurrences: dict[str, list[tuple[PageLine, str, str]]] = {}
    for pdf_page in range(28, 714):
        lines = tuple(sorted(pages[pdf_page], key=lambda item: (item.bbox.y0, item.bbox.x0)))
        for index, line in enumerate(lines):
            parsed = _caption_identifier(line.text, pdf_page=pdf_page)
            if parsed is None or parsed[0] != kind:
                continue
            _, identifier, suffix, designation = parsed
            occurrences.setdefault(identifier, []).append(
                (line, suffix, _short_caption(lines, index) or "")
            )

    records: list[dict[str, Any]] = []
    for identifier, items in sorted(
        occurrences.items(), key=lambda pair: (pair[1][0][0].pdf_page, pair[0])
    ):
        anchor_lines = [item[0] for item in items]
        pages_seen = sorted({line.pdf_page for line in anchor_lines})
        chapter, appendix = publication_context(pages_seen[0])
        captions = [caption for _, _, caption in items if caption]
        continuation_pages = [
            line.pdf_page
            for line, suffix, _ in items
            if "continued" in suffix.lower()
        ]
        record: dict[str, Any] = {
            "id": stable_id(kind, identifier),
            "record_type": kind,
            "published_identifier": identifier,
            "caption": captions[0] if captions else None,
            "caption_sha256": text_sha256(captions[0]) if captions else None,
            "chapter": chapter,
            "appendix": appendix,
            "section_context": locator_by_line.get(anchor_lines[0].line_id),
            "pdf_page_range": [pages_seen[0], pages_seen[-1]],
            "printed_page_range": [printed_page(pages_seen[0]), printed_page(pages_seen[-1])],
            "anchors": [line.anchor() for line in anchor_lines],
            "continuation_pages": continuation_pages,
            "orientation": "portrait",
            "committee_designation": next(
                (
                    parsed[3]
                    for line, _, _ in items
                    if (parsed := _caption_identifier(line.text, pdf_page=line.pdf_page))
                    and parsed[3]
                ),
                None,
            ),
            "review_state": ReviewState.PROVISIONAL.value,
            "extraction_confidence": 0.99,
            "raw_evidence_links": [line.line_id for line in anchor_lines],
        }
        if kind == "table":
            record.update(
                {
                    "header_hierarchy": "unreviewed",
                    "row_hierarchy": "unreviewed",
                    "merged_cells": "unreviewed",
                    "notes": [],
                    "footnotes": [],
                    "units": [],
                    "nearby_exceptions": [],
                    "internal_references": [],
                    "external_references": [],
                    "semantic_classifications": [],
                }
            )
        else:
            record.update(
                {
                    "subfigure_structure": "unreviewed",
                    "labels": [],
                    "dimensions": [],
                    "referenced_sections": [],
                    "related_tables": [],
                    "notes": [],
                    "nearby_exceptions": [],
                    "semantic_category": "unknown",
                    "interpretation_confidence": 0.0,
                    "accessibility_description_status": "missing",
                }
            )
        records.append(record)
    return records


_EXCEPTION_RE = re.compile(r"^Exceptions?\s*:", re.IGNORECASE)
_NUMBERED_ITEM_RE = re.compile(r"^(?P<number>\d+)\.\s+")


def _nearest_parent_locator(
    ordered: Sequence[PageLine],
    index: int,
    prior_locator: str | None,
) -> str | None:
    marker = ordered[index]
    for candidate in reversed(ordered[:index]):
        if candidate.column not in {marker.column, "full"}:
            continue
        match = _SECTION_RE.match(candidate.text)
        if match:
            return normalize_locator(match.group("locator"))
    return prior_locator


def inventory_exceptions(pages: Mapping[int, Sequence[PageLine]]) -> list[dict[str, Any]]:
    """Inventory one attachment record per explicit Exception(s) marker.

    Numbered children remain nested evidence. They do not inflate the published
    exception-block count.
    """
    records: list[dict[str, Any]] = []
    prior_by_column: dict[str, str | None] = {"left": None, "right": None, "full": None}
    for pdf_page in range(28, 714):
        lines = sorted(pages[pdf_page], key=lambda item: (item.bbox.y0, item.bbox.x0))
        running = dict(prior_by_column)
        for index, line in enumerate(lines):
            section_match = _SECTION_RE.match(line.text)
            if section_match:
                running[line.column] = normalize_locator(section_match.group("locator"))
            if not _EXCEPTION_RE.match(line.text):
                continue
            parent = _nearest_parent_locator(lines, index, running.get(line.column))
            numbered: list[PageLine] = []
            for candidate in lines[index + 1:]:
                if candidate.column != line.column:
                    continue
                if candidate.bbox.y0 - line.bbox.y1 > 240:
                    break
                if _SECTION_RE.match(candidate.text) or _EXCEPTION_RE.match(candidate.text):
                    break
                if _NUMBERED_ITEM_RE.match(candidate.text):
                    numbered.append(candidate)
            key = f"{parent}|{pdf_page}|{line.line_id}"
            records.append(
                {
                    "id": stable_id("exception", key),
                    "record_type": "exception_block",
                    "parent_locator": parent,
                    "exception_number": None,
                    "source_anchor": line.anchor(),
                    "marker_anchor": line.anchor(),
                    "nested_structure": "numbered" if numbered else "single",
                    "nested_exception_numbers": [
                        _NUMBERED_ITEM_RE.match(child.text).group("number")
                        for child in numbered
                        if _NUMBERED_ITEM_RE.match(child.text)
                    ],
                    "nested_exception_anchors": [child.anchor() for child in numbered],
                    "applicability_conditions": "uninterpreted",
                    "internal_references": [],
                    "related_tables": [],
                    "related_figures": [],
                    "extraction_confidence": 0.9 if parent else 0.55,
                    "review_state": ReviewState.PROVISIONAL.value if parent else ReviewState.DISPUTED.value,
                }
            )
        prior_by_column.update(running)
    return records


_EQUATION_ID_RE = re.compile(r"\((?P<identifier>[A-Z]?\d+(?:\.\d+)*)\)\s*$")
_MATH_OPERATOR_RE = re.compile(r"(?:=|≤|≥|<|>|\+|−|\u2212|÷|×|/)" )


_FORMULA_LHS_RE = re.compile(
    r"^(?:For SI:\s*)?(?:[A-Za-zΑ-ωρϕΦΔ][A-Za-z0-9Α-ωρϕΦΔ′'_/]{0,6}|\([^)]{1,20}\)|\d+(?:\.\d+)?)\s*(?:=|≤|≥|<|>)"
)
_VARIABLE_DEFINITION_RE = re.compile(
    r"^(?:where:\s*)?[A-Za-zΑ-ωρϕΦΔ][A-Za-z0-9Α-ωρϕΦΔ′'_/]{0,6}\s*="
)
_DESCRIPTIVE_RHS_RE = re.compile(
    r"\b(?:area|load|width|height|distance|thickness|coefficient|factor|rating|weight|"
    r"temperature|capacity|conductivity|content|perimeter|diameter|spacing|strength|"
    r"defined|accordance|actual|allowable|average|required|total|unit|force|moment|"
    r"resistance|endurance|concrete|density|exhaust|rate|wind|spiral|cross-sectional|"
    r"elastic|modulus|reduction|reinforcement)\b",
    re.IGNORECASE,
)


def _formula_role(text: str) -> str | None:
    """Classify one observed line without normalizing its mathematical meaning."""

    text = text.strip()
    if not 3 <= len(text) <= 180 or text.startswith(("http", "EDUFIRE")):
        return None
    if text.lower().startswith("where:"):
        return "applicability" if re.search(r"[=≤≥<>]", text) else None
    if text.startswith("For ") and re.search(r"[≤≥<>]", text):
        return "applicability"
    if text.startswith("="):
        return "definition" if _DESCRIPTIVE_RHS_RE.search(text) else "continuation"
    if text.startswith(("[", "(", "+", "−", "\u2212")) and re.search(r"[+−\u2212÷×/=≤≥<>]", text):
        return "continuation"
    if text.startswith("For SI:"):
        return "primary" if "=" in text else None

    working = re.sub(r"^\d+\.\s+", "", text)
    if ":" in working and re.search(r"[A-Za-zΑ-ω]/[A-Za-zΑ-ω]", working.split(":", 1)[1]):
        working = working.split(":", 1)[1].strip()

    if _FORMULA_LHS_RE.match(working):
        rhs = working.split("=", 1)[1].strip() if "=" in working else working
        rhs_alpha = [word for word in rhs.split() if re.search(r"[A-Za-z]", word)]
        has_relational_or_arithmetic = bool(re.search(r"[+−\u2212÷×≤≥<>]", rhs))
        if _DESCRIPTIVE_RHS_RE.search(rhs) and not has_relational_or_arithmetic:
            return "definition"
        if len(rhs_alpha) > 6 and not has_relational_or_arithmetic:
            return "definition"
        return "primary"

    if re.search(r"\(Equation\s+[A-Z]?\d+(?:-\d+)?\)\s*$", working, re.I):
        prefix = re.sub(r"\(Equation.*$", "", working).strip()
        if re.search(r"[+−\u2212÷×/=≤≥<>]", prefix) and len(prefix.split()) <= 18:
            return "primary"

    if re.match(r"^Class\s+[IVX]+:", working, re.I) and re.search(r"[≤≥<>]", working):
        return "primary"

    if not re.search(r"[+−\u2212÷×=≤≥<>]", working):
        return None
    alpha_words = re.findall(r"[A-Za-z]+", working)
    nonvariable = [
        word for word in alpha_words
        if len(word) > 4 and word.lower() not in {"equation"}
    ]
    if nonvariable:
        return None
    symbolic_tokens = re.findall(r"\b[A-ZΑ-Ω][A-Za-z0-9′']{0,3}\b", working)
    if symbolic_tokens and len(working.split()) <= 18:
        return "primary"
    return None


def inventory_equations(
    pages: Mapping[int, Sequence[PageLine]],
    tables: Sequence[Mapping[str, Any]],
    figures: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    table_caption_y: dict[int, list[float]] = {}
    figure_caption_y: dict[int, list[float]] = {}
    for record in tables:
        for anchor in record["anchors"]:
            table_caption_y.setdefault(int(anchor["pdf_page"]), []).append(float(anchor["bbox"][1]))
    for record in figures:
        for anchor in record["anchors"]:
            figure_caption_y.setdefault(int(anchor["pdf_page"]), []).append(float(anchor["bbox"][1]))

    blocks: list[dict[str, Any]] = []
    prior_by_column: dict[str, str | None] = {"left": None, "right": None, "full": None}
    for pdf_page in range(28, 714):
        if 640 <= pdf_page <= 669:
            continue
        ordered = sorted(pages[pdf_page], key=lambda item: (item.bbox.y0, item.bbox.x0))
        running = dict(prior_by_column)
        last_block: dict[str, Any] | None = None
        for line in ordered:
            section_match = _SECTION_RE.match(line.text)
            if section_match:
                running[line.column] = normalize_locator(section_match.group("locator"))
            if any(y <= line.bbox.y0 <= y + 600 for y in table_caption_y.get(pdf_page, ())):
                continue
            if any(y - 600 <= line.bbox.y0 <= y + 45 for y in figure_caption_y.get(pdf_page, ())):
                continue
            role = _formula_role(line.text)
            if role is None:
                continue
            if role in {"continuation", "applicability", "definition"}:
                if (
                    last_block is not None
                    and line.column in {last_block["line"].column, "full"}
                    and line.bbox.y0 - last_block["last_y"] <= 105
                ):
                    key = {
                        "continuation": "continuations",
                        "applicability": "applicability",
                        "definition": "definitions",
                    }[role]
                    last_block[key].append(line)
                    last_block["last_y"] = line.bbox.y1
                continue
            source_section = running.get(line.column) or running.get("full")
            last_block = {
                "line": line,
                "source_section": source_section,
                "continuations": [],
                "applicability": [],
                "definitions": [],
                "last_y": line.bbox.y1,
            }
            blocks.append(last_block)
        prior_by_column.update(running)

    records: list[dict[str, Any]] = []
    for block in blocks:
        line: PageLine = block["line"]
        match = _EQUATION_ID_RE.search(line.text)
        equation_label = re.search(r"\(Equation\s+(?P<identifier>[A-Z]?\d+(?:-\d+)?)\)", line.text, re.I)
        identifier = equation_label.group("identifier") if equation_label else (match.group("identifier") if match else None)
        variables = sorted(
            {
                token
                for token in re.findall(r"\b[A-Za-z][A-Za-z0-9_]{0,8}\b", line.text)
                if token.lower() not in {"for", "si", "where", "and", "or", "the", "of", "in", "equation"}
            }
        )
        key = identifier or f"{line.pdf_page}|{line.line_id}"
        records.append(
            {
                "id": stable_id("equation", key),
                "record_type": "equation",
                "equation_identifier": identifier,
                "source_section": block["source_section"],
                "source_anchor": line.anchor(),
                "observed_expression": line.text,
                "observed_expression_sha256": text_sha256(line.text),
                "continuation_anchors": [item.anchor() for item in block["continuations"]],
                "normalized_expression": None,
                "variables": variables,
                "units": [],
                "nearby_variable_definitions": [item.anchor() for item in block["definitions"]],
                "applicability_anchors": [item.anchor() for item in block["applicability"]],
                "applicability_text": None,
                "exceptions": [],
                "referenced_tables": [],
                "referenced_sections": [],
                "external_references": [],
                "extraction_confidence": 0.84,
                "normalized_expression_confidence": 0.0,
                "review_state": ReviewState.PROVISIONAL.value,
            }
        )
    return records

_DEFINITION_LINE_RE = re.compile(
    r"^(?:\[[A-Z]{1,3}\]\s*)?"
    r"(?P<term>[A-Z][A-Z0-9 /,()'’&\-]{2,180})\.\s+(?P<body>.+)$"
)


def _definition_anchor_from_seed(
    node: Mapping[str, Any],
    source_map: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], str]:
    start = int(node["span"]["start"])
    end = int(node["span"]["end"])
    fragments: list[Mapping[str, Any]] = []
    for entry in source_map:
        span = entry["normalized_span"]
        if int(span["end"]) <= start or int(span["start"]) >= end:
            continue
        fragments.extend(entry.get("fragments", ()))
    if not fragments:
        raise ValueError(f"definition {node['locator']} has no source fragments")
    first_page = min(int(item["page_number"]) for item in fragments)
    page_fragments = [item for item in fragments if int(item["page_number"]) == first_page]
    bbox = BoundingBox(
        min(float(item["bbox"][0]) for item in page_fragments),
        min(float(item["bbox"][1]) for item in page_fragments),
        max(float(item["bbox"][2]) for item in page_fragments),
        max(float(item["bbox"][3]) for item in page_fragments),
    )
    text = str(node["span"]["text"])
    return source_anchor(first_page, bbox, text), text_sha256(text)


def inventory_definitions(
    pages: Mapping[int, Sequence[PageLine]],
    chapter2_seed: Mapping[str, Any],
) -> list[dict[str, Any]]:
    root = chapter2_seed["document_ast"]["root"]
    source_map = chapter2_seed["source_map"]

    def walk(node: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
        yield node
        for child in node.get("children", ()):
            yield from walk(child)

    records: list[dict[str, Any]] = []
    for node in walk(root):
        if node.get("type") != "definition_entry":
            continue
        anchor, digest = _definition_anchor_from_seed(node, source_map)
        observed = str(node["label"])
        records.append(
            {
                "id": stable_id("definition", f"chapter2|{observed}|{node['locator']}"),
                "record_type": "definition",
                "normalized_term": re.sub(r"\s+", " ", observed).strip().upper(),
                "observed_term": observed,
                "source_section": "202",
                "scope": "code_wide_unless_context_limits",
                "source_anchor": anchor,
                "definition_text_sha256": digest,
                "internal_references": [],
                "external_references": [],
                "conflicts_or_alternate_definitions": [],
                "review_state": ReviewState.VERIFIED.value,
            }
        )

    # Scope-limited definitions outside Chapter 2. Detection is intentionally
    # bounded to explicit definition-introduction provisions and appendix sections.
    scoped_ranges = (
        (487, "1905.1.1", "chapter_19_aci_modification"),
        (680, "E102.1", "appendix_E"),
        (691, "G201.2", "appendix_G"),
        (694, "H102.1", "appendix_H"),
        (700, "J102.1", "appendix_J"),
        (710, "M101.2", "appendix_M"),
        (712, "N102.1", "appendix_N"),
    )
    for pdf_page, section, scope in scoped_ranges:
        lines = pages[pdf_page]
        started = False
        for line in lines:
            text = line.text.strip()
            if section in text and "definition" in text.lower():
                started = True
                continue
            if not started:
                continue
            if _SECTION_RE.match(text) and not text.startswith(section):
                break
            match = _DEFINITION_LINE_RE.match(text)
            if not match:
                continue
            term = match.group("term").strip()
            if term.isdigit() or len(term) > 120:
                continue
            key = f"{section}|{term}|{line.line_id}"
            records.append(
                {
                    "id": stable_id("definition", key),
                    "record_type": "definition",
                    "normalized_term": re.sub(r"\s+", " ", term).upper(),
                    "observed_term": term,
                    "source_section": section,
                    "scope": scope,
                    "source_anchor": line.anchor(),
                    "definition_text_sha256": text_sha256(text),
                    "internal_references": [],
                    "external_references": [],
                    "conflicts_or_alternate_definitions": [],
                    "review_state": ReviewState.PROVISIONAL.value,
                }
            )
    return records


_AGENCY_RE = re.compile(r"^[A-Z][A-Z0-9/&.\-]{1,29}$")


def _chapter35_row_start(line: PageLine) -> bool:
    if line.bbox.x0 > 70.2 or ":" not in line.text:
        return False
    if line.text.startswith(("User note:", "About this chapter:")):
        return False
    before = line.text.split(":", 1)[0]
    return bool(re.search(r"\d", before)) or before.startswith("Intumescent Fire-resistive Materials")


def _split_standard_identity(prefix: str) -> tuple[str, str | None]:
    pieces = prefix.split("—")
    for index, piece in enumerate(pieces[1:], start=1):
        if re.match(r"\d", piece):
            return "—".join(pieces[:index]).strip(), "—".join(pieces[index:]).strip()
    return prefix.strip(), None


def inventory_chapter35(
    pages: Mapping[int, Sequence[PageLine]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    agency: str | None = None
    for pdf_page in range(640, 669):
        lines = pages[pdf_page]
        for index, line in enumerate(lines):
            text = line.text.strip()
            if (
                line.bbox.x0 <= 70.2
                and len(text) <= 30
                and _AGENCY_RE.fullmatch(text)
                and index + 1 < len(lines)
                and not text.startswith(("CHAPTER", "REFERENCED", "EDUFIRE"))
            ):
                agency = text
                continue
            if not _chapter35_row_start(line):
                continue
            prefix, title = text.split(":", 1)
            designation, edition = _split_standard_identity(prefix.strip())
            referenced_lines: list[PageLine] = []
            for candidate in lines[index + 1:]:
                if _chapter35_row_start(candidate):
                    break
                candidate_text = candidate.text.strip()
                if (
                    candidate.bbox.x0 <= 70.2
                    and len(candidate_text) <= 30
                    and _AGENCY_RE.fullmatch(candidate_text)
                ):
                    break
                if candidate.bbox.y0 - line.bbox.y1 > 95:
                    break
                if candidate.bbox.x0 >= 100 and re.search(r"(?:\d{3,4}|Table|Chapter|Appendix)", candidate_text):
                    referenced_lines.append(candidate)
            referenced_text = " ".join(item.text for item in referenced_lines)
            references = sorted(
                {
                    normalize_locator(value)
                    for value in re.findall(
                        r"(?:[A-N])?\d{1,4}(?:\.\d+[A-Za-z]?(?:\([A-Za-z0-9]+\))*)+",
                        referenced_text,
                    )
                }
            )
            family_key = f"{agency or 'UNKNOWN'}|{designation}"
            records.append(
                {
                    "id": stable_id("chapter35-row", f"{pdf_page}|{line.line_id}"),
                    "record_type": "chapter35_referenced_standard_entry",
                    "promulgating_agency": agency,
                    "observed_designation": designation,
                    "observed_edition": edition,
                    "observed_designation_with_edition": prefix.strip(),
                    "observed_title": title.strip()[:300],
                    "title_sha256": text_sha256(title.strip()),
                    "referenced_ibc_sections": references,
                    "source_anchor": line.anchor(),
                    "continuation_state": "starts_on_page",
                    "row_geometry": line.bbox.to_list(),
                    "notes": [],
                    "normalized_document_family_id": stable_id("external-family", family_key),
                    "review_state": ReviewState.PROVISIONAL.value,
                }
            )
    return records


def normalize_external_families(
    chapter35_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in chapter35_rows:
        grouped.setdefault(str(row["normalized_document_family_id"]), []).append(row)
    families: list[dict[str, Any]] = []
    for family_id, rows in sorted(grouped.items()):
        first = rows[0]
        families.append(
            {
                "id": family_id,
                "record_type": "external_document_family",
                "issuing_organization": first["promulgating_agency"],
                "document_family": first["observed_designation"],
                "observed_designations": sorted({str(row["observed_designation_with_edition"]) for row in rows}),
                "observed_editions": sorted({str(row["observed_edition"]) for row in rows if row["observed_edition"]}),
                "observed_titles": sorted({str(row["observed_title"]) for row in rows}),
                "chapter35_entry_ids": [row["id"] for row in rows],
                "citation_purpose": classify_citation_purpose(
                    str(first["promulgating_agency"] or ""), str(first["observed_designation"])
                ),
                "normalization_confidence": 0.95 if first["promulgating_agency"] else 0.5,
                "review_state": ReviewState.PROVISIONAL.value,
            }
        )
    return families

def classify_citation_purpose(agency: str, designation: str) -> str:
    observed = f"{agency} {designation}".upper()
    if "A117.1" in observed:
        return "accessibility standard"
    if agency in {"ASCE", "ASCE/SEI", "ACI", "AISC", "AISI", "TMS", "AWS"}:
        return "structural design standard"
    if agency == "ASTM":
        return "material specification"
    if agency in {"UL", "ULC", "FM"}:
        return "product qualification"
    if agency == "NFPA":
        return "fire-test standard" if re.search(r"(?:251|252|253|257|268|285)", designation) else "installation standard"
    if agency in {"ICC", "CFR", "USC"}:
        return "related code"
    if agency == "CPSC":
        return "performance classification"
    return "unknown"


_GENERIC_EXTERNAL_RE = re.compile(
    r"\b(?P<agency>ASTM|NFPA|ASCE(?:/SEI)?|ACI|ICC|ULC?|ANSI|AISC|AISI|AWS|ASME|TMS|CSA|FM|FEMA|CPSC|CFR|USC)\s+"
    r"(?P<designation>[A-Z0-9][A-Z0-9./\-]*(?:\s+[A-Z0-9][A-Z0-9./\-]*){0,2})"
)


def inventory_external_citations(
    pages: Mapping[int, Sequence[PageLine]],
    chapter35_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    family_lookup: dict[tuple[str, str], str] = {}
    for row in chapter35_rows:
        agency = str(row["promulgating_agency"] or "")
        designation = str(row["observed_designation"])
        family_lookup[(agency.upper(), designation.upper())] = str(row["normalized_document_family_id"])

    locator_by_line = build_line_locator_index(pages)
    occurrences: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    seen: set[tuple[int, str, str]] = set()
    for pdf_page in range(28, 714):
        if 640 <= pdf_page <= 669:
            continue
        for line in pages[pdf_page]:
            for match in _GENERIC_EXTERNAL_RE.finditer(line.text):
                agency = match.group("agency").upper()
                designation = match.group("designation").strip(".,;:)")
                # Trim prose words captured after a compact designation.
                designation = re.split(r"\s+(?:and|or|shall|for|where|with|as|of|to)\b", designation, maxsplit=1, flags=re.I)[0]
                key = (pdf_page, line.line_id, f"{agency} {designation}")
                if key in seen:
                    continue
                seen.add(key)
                family_id = family_lookup.get((agency, designation.upper()))
                record = {
                    "id": stable_id("citation", f"{pdf_page}|{line.line_id}|{agency}|{designation}"),
                    "record_type": "external_citation_occurrence",
                    "issuing_organization": agency,
                    "observed_designation": designation,
                    "observed_edition": None,
                    "normalized_document_family_id": family_id,
                    "source_section": locator_by_line.get(line.line_id),
                    "source_anchor": line.anchor(),
                    "citation_context_sha256": text_sha256(line.text),
                    "citation_purpose": classify_citation_purpose(agency, designation),
                    "normative_or_informational_context": "unreviewed",
                    "normalization_confidence": 0.9 if family_id else 0.45,
                    "review_state": ReviewState.PROVISIONAL.value if family_id else ReviewState.DISPUTED.value,
                }
                occurrences.append(record)
                if family_id is None:
                    unmatched.append(record)
    return occurrences, unmatched


_CROSS_REF_RE = re.compile(
    r"\b(?P<kind>Sections?|Tables?|Figures?|Chapters?|Appendices?|Appendix)\s+"
    r"(?P<raw>(?:[A-N])?\d{1,4}(?:\.\d+[A-Za-z]?(?:\([A-Za-z0-9]+\))*)?(?:\s*(?:,|and|through|to)\s*(?:[A-N])?\d{1,4}(?:\.\d+[A-Za-z]?(?:\([A-Za-z0-9]+\))*)?)*)",
    re.IGNORECASE,
)
_TARGET_TOKEN_RE = re.compile(
    r"(?:[A-N])?\d{1,4}(?:\.\d+[A-Za-z]?(?:\([A-Za-z0-9]+\))*)?"
)
_APPENDIX_REF_RE = re.compile(r"\bAppendix\s+(?P<target>[A-N])\b", re.IGNORECASE)
_EQUATION_REF_RE = re.compile(
    r"\bEquation\s+(?P<target>[A-Z]?\d+(?:[-.]\d+)+)", re.IGNORECASE
)
_EXCEPTION_REF_RE = re.compile(
    r"\bException(?:s)?\s+(?P<target>\d+(?:\.\d+)?(?:\([A-Za-z0-9]+\))*)",
    re.IGNORECASE,
)


def inventory_cross_references(
    pages: Mapping[int, Sequence[PageLine]],
    tables: Sequence[Mapping[str, Any]],
    figures: Sequence[Mapping[str, Any]],
    equations: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    section_targets = collect_section_targets(pages)
    locator_by_line = build_line_locator_index(pages)
    table_targets = {str(item["published_identifier"]) for item in tables}
    figure_targets = {str(item["published_identifier"]) for item in figures}
    equation_targets = {
        str(item["equation_identifier"])
        for item in equations
        if item["equation_identifier"]
    }
    records: list[dict[str, Any]] = []

    def add(
        *,
        line: PageLine,
        match_start: int,
        raw: str,
        kind: str,
        token: str,
        target: str,
        state: ResolutionState,
        ordinal: int = 0,
    ) -> None:
        records.append(
            {
                "id": stable_id(
                    "cross-reference",
                    f"{line.pdf_page}|{line.line_id}|{kind}|{target}|{match_start}|{ordinal}",
                ),
                "record_type": "internal_cross_reference",
                "source_anchor": line.anchor(),
                "source_section": locator_by_line.get(line.line_id),
                "raw_citation": raw,
                "target_kind": kind,
                "raw_target": token,
                "resolved_target": target if state == ResolutionState.RESOLVED else None,
                "resolution_state": state.value,
                "resolution_notes": None,
                "review_state": ReviewState.PROVISIONAL.value,
            }
        )

    for pdf_page in range(28, 714):
        if 640 <= pdf_page <= 669:
            # Chapter 35 referenced-section cells have their own row contract.
            continue
        for line in pages[pdf_page]:
            if _caption_identifier(line.text, pdf_page=pdf_page) is not None:
                # A declaration caption is not an outbound citation to itself.
                continue
            covered_spans: list[tuple[int, int]] = []
            for match in _CROSS_REF_RE.finditer(line.text):
                kind_word = match.group("kind").lower()
                if kind_word.startswith("section"):
                    kind = "section"
                    known = section_targets
                elif kind_word.startswith("table"):
                    kind = "table"
                    known = table_targets
                elif kind_word.startswith("figure"):
                    kind = "figure"
                    known = figure_targets
                elif kind_word.startswith("chapter"):
                    kind = "chapter"
                    known = set(CHAPTER_STARTS)
                else:
                    kind = "appendix"
                    known = set(APPENDIX_STARTS)
                raw = match.group(0)
                covered_spans.append(match.span())
                for token_index, token in enumerate(_TARGET_TOKEN_RE.findall(match.group("raw"))):
                    target = normalize_locator(token)
                    if kind == "appendix":
                        target = target[0] if target and target[0].isalpha() else target
                    if target in known:
                        state = ResolutionState.RESOLVED
                    elif kind in {"table", "figure", "chapter", "appendix"}:
                        state = ResolutionState.NONEXISTENT
                    else:
                        state = ResolutionState.UNRESOLVED
                    if re.search(r"\b(?:ACI|ASCE|ASTM|NFPA|ICC|UL)\b", line.text[: match.start()]):
                        state = ResolutionState.AMBIGUOUS
                    add(
                        line=line,
                        match_start=match.start(),
                        raw=raw,
                        kind=kind,
                        token=token,
                        target=target,
                        state=state,
                        ordinal=token_index,
                    )

            def span_is_covered(span: tuple[int, int]) -> bool:
                return any(start <= span[0] and span[1] <= end for start, end in covered_spans)

            for match in _APPENDIX_REF_RE.finditer(line.text):
                if span_is_covered(match.span()):
                    continue
                target = match.group("target").upper()
                add(
                    line=line,
                    match_start=match.start(),
                    raw=match.group(0),
                    kind="appendix",
                    token=match.group("target"),
                    target=target,
                    state=(
                        ResolutionState.RESOLVED
                        if target in APPENDIX_STARTS
                        else ResolutionState.NONEXISTENT
                    ),
                )
            for match in _EQUATION_REF_RE.finditer(line.text):
                target = normalize_locator(match.group("target").replace("-", "."))
                # Printed equation labels commonly use a hyphen. Preserve the raw token,
                # while the normalized target uses the inventory's dot form where possible.
                alternatives = {match.group("target"), target}
                resolved = next((item for item in alternatives if item in equation_targets), None)
                add(
                    line=line,
                    match_start=match.start(),
                    raw=match.group(0),
                    kind="equation",
                    token=match.group("target"),
                    target=resolved or target,
                    state=ResolutionState.RESOLVED if resolved else ResolutionState.NONEXISTENT,
                )
            for match in _EXCEPTION_REF_RE.finditer(line.text):
                add(
                    line=line,
                    match_start=match.start(),
                    raw=match.group(0),
                    kind="exception",
                    token=match.group("target"),
                    target=match.group("target"),
                    state=ResolutionState.AMBIGUOUS,
                )
    return records


def inventory_incidental_layouts(
    pages: Mapping[int, Sequence[PageLine]],
    tables: Sequence[Mapping[str, Any]],
    figures: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    locator_by_line = build_line_locator_index(pages)
    formal_regions: dict[int, list[tuple[float, str]]] = {}
    for item in (*tables, *figures):
        for anchor in item["anchors"]:
            formal_regions.setdefault(int(anchor["pdf_page"]), []).append(
                (float(anchor["bbox"][1]), str(item["record_type"]))
            )
    candidates: list[dict[str, Any]] = []
    for pdf_page in range(28, 714):
        if 640 <= pdf_page <= 669:
            continue
        body = [
            line for line in pages[pdf_page]
            if 52 <= line.bbox.y0 <= 742
            and not line.text.startswith(("EDUFIRE", "Telegram"))
            and len(line.text) > 1
        ]
        rows: list[list[PageLine]] = []
        for line in sorted(body, key=lambda item: (item.bbox.y0, item.bbox.x0)):
            if rows and abs(rows[-1][0].bbox.y0 - line.bbox.y0) <= 2.4:
                rows[-1].append(line)
            else:
                rows.append([line])
        tabular_rows = [
            row for row in rows
            if len(row) >= 3
            and max(item.bbox.x0 for item in row) - min(item.bbox.x0 for item in row) >= 90
            and sum(len(item.text) <= 80 for item in row) >= 3
        ]
        groups: list[list[list[PageLine]]] = []
        for row in tabular_rows:
            if groups and row[0].bbox.y0 - groups[-1][-1][0].bbox.y0 <= 30:
                groups[-1].append(row)
            else:
                groups.append([row])
        for group in groups:
            if len(group) < 3:
                continue
            flat = [line for row in group for line in row]
            bbox = union_bbox(flat)
            overlaps_formal = any(
                y <= bbox.y0 <= y + 560 for y, _ in formal_regions.get(pdf_page, ())
            )
            if overlaps_formal:
                continue
            x_bins: dict[int, int] = {}
            for row in group:
                for line in row:
                    bucket = round(line.bbox.x0 / 10) * 10
                    x_bins[bucket] = x_bins.get(bucket, 0) + 1
            repeated_columns = sum(count >= 3 for count in x_bins.values())
            strict = len(group) >= 4 and repeated_columns >= 3
            key = f"{pdf_page}|{round(bbox.y0,1)}|{round(bbox.y1,1)}"
            candidates.append(
                {
                    "id": stable_id("incidental-layout", key),
                    "record_type": "incidental_layout",
                    "source_page": pdf_page,
                    "printed_page": printed_page(pdf_page),
                    "chapter": publication_context(pdf_page)[0],
                    "appendix": publication_context(pdf_page)[1],
                    "surrounding_section": locator_by_line.get(flat[0].line_id),
                    "bbox": bbox.to_list(),
                    "geometry": {
                        "row_count": len(group),
                        "line_fragment_count": len(flat),
                        "repeated_x_columns": repeated_columns,
                    },
                    "inferred_relationships": "aligned_rows_and_columns",
                    "broad_classification": True,
                    "strict_classification": strict,
                    "confidence": 0.78 if strict else 0.55,
                    "reason_for_inclusion": "three_or_more aligned multi-fragment rows without a formal caption",
                    "review_state": ReviewState.PROVISIONAL.value,
                    "raw_evidence_links": [line.line_id for line in flat],
                }
            )
    return candidates


def inventory_vector_graphic_regions(
    vector_evidence: Mapping[str, Any],
    *,
    figures: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Classify private vector-region evidence without asserting graphic meaning."""

    if vector_evidence.get("source_sha256") != SOURCE_SHA256:
        raise ValueError("vector evidence source SHA-256 does not match the registered IBC source")
    if vector_evidence.get("source_size_bytes") != SOURCE_SIZE_BYTES:
        raise ValueError("vector evidence source size does not match the registered IBC source")
    if vector_evidence.get("source_page_count") != SOURCE_PAGE_COUNT:
        raise ValueError("vector evidence source page count does not match the registered IBC source")
    pages = vector_evidence.get("pages")
    if not isinstance(pages, Sequence):
        raise ValueError("vector evidence pages must be a sequence")
    if [int(item.get("pdf_page", 0)) for item in pages] != list(range(1, SOURCE_PAGE_COUNT + 1)):
        raise ValueError("vector evidence must cover all 761 PDF pages in order")

    figure_y: dict[int, list[float]] = {}
    for figure in figures:
        for anchor in figure.get("anchors", ()):
            figure_y.setdefault(int(anchor["pdf_page"]), []).append(float(anchor["bbox"][1]))

    records: list[dict[str, Any]] = []
    for page in pages:
        pdf_page = int(page["pdf_page"] )
        for region in page.get("regions", ()):
            bbox = BoundingBox.from_values(region["bbox"] )
            width = bbox.x1 - bbox.x0
            height = bbox.y1 - bbox.y0
            fingerprint = str(region["geometry_fingerprint"] )
            if not 28 <= pdf_page <= 713:
                disposition = "rejected_outside_normative_and_appendix_pages"
                reason = "region falls outside the chapter and appendix page range"
                state = ReviewState.REJECTED
            elif (
                bbox.x0 <= 30
                and bbox.y0 <= 30
                and bbox.x1 >= 570
                and bbox.y1 >= 760
            ) or width > 540 or height > 720:
                disposition = "rejected_page_furniture"
                reason = "region is page-sized or aligned with the recurring page frame"
                state = ReviewState.REJECTED
            elif any(
                abs(y - bbox.y1) <= 170 or bbox.y0 <= y <= bbox.y1 + 170
                for y in figure_y.get(pdf_page, ())
            ):
                disposition = "rejected_captioned_figure_region"
                reason = "region overlaps or directly precedes a formally captioned figure"
                state = ReviewState.REJECTED
            elif (
                int(region.get("curve_count", 0)) == 0
                and int(region.get("rect_count", 0)) >= 4
                and width >= 100
                and height >= 60
            ):
                disposition = "candidate_tabular_or_background_geometry"
                reason = "dense rectangle-only geometry is more consistent with table or background construction"
                state = ReviewState.DISPUTED
            elif (
                width >= 100
                and height >= 80
                and width * height >= 10_000
                and (
                    int(region.get("curve_count", 0)) >= 4
                    or int(region.get("line_count", 0)) >= 2
                )
            ):
                disposition = "candidate_vector_technical_graphic"
                reason = "materially sized non-tabular vector geometry requires visual classification"
                state = ReviewState.DISPUTED
            else:
                disposition = "candidate_vector_region_unclassified"
                reason = "surviving vector geometry is source-backed but insufficient for automatic classification"
                state = ReviewState.DISPUTED

            records.append(
                {
                    "id": stable_id("vector-region", f"{pdf_page}|{fingerprint}"),
                    "record_type": "vector_graphic_region_detection",
                    "candidate_source": "pdf_vector_paths",
                    "published_identifier": None,
                    "caption": None,
                    "chapter": publication_context(pdf_page)[0],
                    "appendix": publication_context(pdf_page)[1],
                    "source_anchor": source_anchor(pdf_page, bbox, f"vector-region:{fingerprint}"),
                    "geometry": {
                        "drawing_count": int(region.get("drawing_count", 0)),
                        "line_count": int(region.get("line_count", 0)),
                        "curve_count": int(region.get("curve_count", 0)),
                        "rect_count": int(region.get("rect_count", 0)),
                        "fill_count": int(region.get("fill_count", 0)),
                        "stroke_count": int(region.get("stroke_count", 0)),
                        "geometry_fingerprint": fingerprint,
                    },
                    "disposition": disposition,
                    "classification_reason": reason,
                    "semantic_category": "unknown",
                    "interpretation_confidence": 0.0,
                    "review_state": state.value,
                }
            )
    return records


def inventory_diagrams(
    pages: Mapping[int, Sequence[PageLine]],
    image_regions: Sequence[Mapping[str, Any]],
    figures: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    figure_y: dict[int, list[float]] = {}
    for figure in figures:
        for anchor in figure["anchors"]:
            figure_y.setdefault(int(anchor["pdf_page"]), []).append(float(anchor["bbox"][1]))
    records: list[dict[str, Any]] = []
    for page in image_regions:
        pdf_page = int(page["pdf_page"])
        if not 28 <= pdf_page <= 713:
            continue
        for index, image in enumerate(page.get("images", ())):
            bbox = BoundingBox.from_values(image["bbox"])
            width = bbox.x1 - bbox.x0
            height = bbox.y1 - bbox.y0
            if width < 100 or height < 80 or width * height < 10_000:
                continue
            if any(abs(y - bbox.y1) <= 170 or bbox.y0 <= y <= bbox.y1 + 170 for y in figure_y.get(pdf_page, ())):
                continue
            key = f"{pdf_page}|{index}|{bbox.to_list()}"
            records.append(
                {
                    "id": stable_id("diagram", key),
                    "record_type": "uncaptioned_technical_graphic_candidate",
                    "published_identifier": None,
                    "caption": None,
                    "chapter": publication_context(pdf_page)[0],
                    "appendix": publication_context(pdf_page)[1],
                    "source_anchor": source_anchor(pdf_page, bbox, f"image-xref:{image.get('xref')}") ,
                    "image_dimensions": [image.get("width"), image.get("height")],
                    "subfigure_structure": "unreviewed",
                    "labels": [],
                    "dimensions": [],
                    "referenced_sections": [],
                    "related_tables": [],
                    "semantic_category": "unknown",
                    "extraction_confidence": 0.7,
                    "interpretation_confidence": 0.0,
                    "accessibility_description_status": "missing",
                    "review_state": ReviewState.PROVISIONAL.value,
                }
            )
    return records


def attach_table_context(
    pages: Mapping[int, Sequence[PageLine]],
    tables: list[dict[str, Any]],
    exceptions: Sequence[Mapping[str, Any]],
) -> None:
    """Attach source-safe nearby note, unit, and exception relationships."""

    exceptions_by_page: dict[int, list[Mapping[str, Any]]] = {}
    for item in exceptions:
        anchor = item.get("source_anchor") or {}
        if anchor.get("pdf_page") is not None:
            exceptions_by_page.setdefault(int(anchor["pdf_page"]), []).append(item)
    line_by_id = {line.line_id: line for page in pages.values() for line in page}
    for table in tables:
        note_anchors: list[dict[str, Any]] = []
        footnote_anchors: list[dict[str, Any]] = []
        units: set[str] = set()
        nearby_exception_ids: set[str] = set()
        for anchor in table["anchors"]:
            marker_line = line_by_id.get(anchor.get("line_id"))
            if marker_line is None:
                continue
            page_lines = sorted(pages[marker_line.pdf_page], key=lambda item: (item.bbox.y0, item.bbox.x0))
            for candidate in page_lines:
                if candidate.bbox.y0 <= marker_line.bbox.y1:
                    continue
                if candidate.bbox.y0 - marker_line.bbox.y1 > 620:
                    break
                if _CAPTION_RE.match(candidate.text) and candidate.line_id != marker_line.line_id:
                    break
                text = candidate.text.strip()
                if text.startswith("For SI:"):
                    note_anchors.append(candidate.anchor())
                    units.update(re.findall(r"\b(?:mm|m|cm|in\.|ft|psf|psi|kPa|MPa|N|kN|kg|lb|pcf|°C|°F)\b", text))
                elif re.match(r"^[a-z]\.\s+", text):
                    footnote_anchors.append(candidate.anchor())
            for exception in exceptions_by_page.get(marker_line.pdf_page, ()):
                ex_anchor = exception.get("source_anchor") or {}
                ex_y = float((ex_anchor.get("bbox") or [0, 0, 0, 0])[1])
                if abs(ex_y - marker_line.bbox.y0) <= 240:
                    nearby_exception_ids.add(str(exception["id"]))
        table["notes"] = note_anchors
        table["footnotes"] = footnote_anchors
        table["units"] = sorted(units)
        table["nearby_exceptions"] = sorted(nearby_exception_ids)


def classify_figures(figures: list[dict[str, Any]]) -> None:
    for figure in figures:
        chapter = str(figure.get("chapter") or "")
        caption = str(figure.get("caption") or "")
        category = "unknown"
        confidence = 0.0
        if chapter == "7":
            category, confidence = "fire-resistance assembly", 0.72
        elif chapter == "10":
            category, confidence = "means-of-egress configuration", 0.72
        elif chapter == "11":
            category, confidence = "accessibility clearance", 0.72
        elif chapter == "16":
            category = "administrative map" if re.search(r"MAP|WIND SPEED|SEISMIC", caption, re.I) else "structural configuration"
            confidence = 0.68
        elif chapter in {"18", "21", "23", "26"}:
            category, confidence = "structural configuration", 0.65
        elif chapter == "30":
            category, confidence = "building geometry", 0.55
        elif figure.get("appendix") == "J":
            category, confidence = "building geometry", 0.55
        figure["semantic_category"] = category
        figure["interpretation_confidence"] = confidence


def build_detection_inventory(
    pages: Mapping[int, Sequence[PageLine]],
    tables: Sequence[Mapping[str, Any]],
    figures: Sequence[Mapping[str, Any]],
    incidental: Sequence[Mapping[str, Any]],
    equations: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for kind, normalized in (("table", tables), ("figure", figures)):
        for item in normalized:
            for ordinal, anchor in enumerate(item.get("anchors", ())):
                records.append({
                    "id": stable_id("detection", f"{kind}|{item['id']}|{ordinal}"),
                    "record_type": "detected_structure",
                    "candidate_kind": f"{kind}_candidate",
                    "source_anchor": anchor,
                    "disposition": "accepted" if ordinal == 0 else "merged_continuation_or_repeat",
                    "normalized_record_id": item["id"],
                    "parser_confidence": item.get("extraction_confidence", 0.0),
                    "review_state": ReviewState.PROVISIONAL.value,
                })
    # Preserve four table-looking labels embedded in Figure 2308.6.7.2 as rejected detections.
    for line in pages[556]:
        if line.text.startswith("TABLE 2304.1 0.1"):
            records.append({
                "id": stable_id("detection", f"rejected-embedded-table|{line.line_id}"),
                "record_type": "detected_structure",
                "candidate_kind": "table_candidate",
                "source_anchor": line.anchor(),
                "disposition": "rejected_embedded_in_figure",
                "normalized_record_id": None,
                "parser_confidence": 0.99,
                "review_state": ReviewState.REJECTED.value,
            })
    for kind, collection in (("incidental_layout", incidental), ("equation", equations), ("diagram", diagrams)):
        for item in collection:
            anchor = item.get("source_anchor") or {
                "pdf_page": item.get("source_page"),
                "printed_page": item.get("printed_page"),
                "chapter": item.get("chapter"),
                "appendix": item.get("appendix"),
                "bbox": item.get("bbox"),
                "line_id": None,
                "observed_text_sha256": None,
            }
            records.append({
                "id": stable_id("detection", f"{kind}|{item['id']}"),
                "record_type": "detected_structure",
                "candidate_kind": f"{kind}_candidate",
                "source_anchor": anchor,
                "disposition": "accepted_provisional",
                "normalized_record_id": item["id"],
                "parser_confidence": item.get("extraction_confidence", item.get("confidence", 0.0)),
                "review_state": item.get("review_state", ReviewState.PROVISIONAL.value),
            })
    return records

def build_reference_crosschecks(
    chapter35_rows: Sequence[Mapping[str, Any]],
    external_families: Sequence[Mapping[str, Any]],
    external_citations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    cited_family_ids = {
        str(item["normalized_document_family_id"])
        for item in external_citations
        if item.get("normalized_document_family_id")
    }
    chapter35_family_ids = {str(item["id"]) for item in external_families}
    aliases = [
        {"family_id": item["id"], "observed_designations": item["observed_designations"]}
        for item in external_families
        if len(item.get("observed_designations", ())) > 1
    ]
    return {
        "chapter35_families_not_detected_elsewhere": sorted(chapter35_family_ids - cited_family_ids),
        "citation_occurrences_without_chapter35_match": [
            item["id"] for item in external_citations if not item.get("normalized_document_family_id")
        ],
        "duplicate_or_alias_families": aliases,
        "designation_or_edition_mismatches": [],
        "unresolved_organizations_or_titles": [
            item["id"]
            for item in chapter35_rows
            if not item.get("promulgating_agency") or not item.get("observed_title")
        ],
    }


def attach_figure_context(
    pages: Mapping[int, Sequence[PageLine]],
    figures: list[dict[str, Any]],
    exceptions: Sequence[Mapping[str, Any]],
) -> None:
    exceptions_by_page: dict[int, list[Mapping[str, Any]]] = {}
    for item in exceptions:
        anchor = item.get("source_anchor") or {}
        if anchor.get("pdf_page") is not None:
            exceptions_by_page.setdefault(int(anchor["pdf_page"]), []).append(item)
    line_by_id = {line.line_id: line for page in pages.values() for line in page}
    for figure in figures:
        notes: list[dict[str, Any]] = []
        nearby_exception_ids: set[str] = set()
        for anchor in figure.get("anchors", ()):
            marker = line_by_id.get(anchor.get("line_id"))
            if marker is None:
                continue
            for candidate in pages[marker.pdf_page]:
                if abs(candidate.bbox.y0 - marker.bbox.y0) > 130:
                    continue
                text = candidate.text.strip()
                if text.startswith("For SI:") or re.match(r"^[a-z]\.\s+", text):
                    notes.append(candidate.anchor())
            for exception in exceptions_by_page.get(marker.pdf_page, ()):
                ex_anchor = exception.get("source_anchor") or {}
                ex_y = float((ex_anchor.get("bbox") or [0, 0, 0, 0])[1])
                if abs(ex_y - marker.bbox.y0) <= 240:
                    nearby_exception_ids.add(str(exception["id"]))
        figure["notes"] = notes
        figure["nearby_exceptions"] = sorted(nearby_exception_ids)


def attach_reference_relationships(
    tables: list[dict[str, Any]],
    figures: list[dict[str, Any]],
    equations: list[dict[str, Any]],
    exceptions: list[dict[str, Any]],
    cross_references: Sequence[Mapping[str, Any]],
    external_citations: Sequence[Mapping[str, Any]],
) -> None:
    internal_by_line: dict[str, list[str]] = {}
    external_by_line: dict[str, list[str]] = {}
    for item in cross_references:
        line_id = (item.get("source_anchor") or {}).get("line_id")
        if line_id:
            internal_by_line.setdefault(str(line_id), []).append(str(item["id"]))
    for item in external_citations:
        line_id = (item.get("source_anchor") or {}).get("line_id")
        if line_id:
            external_by_line.setdefault(str(line_id), []).append(str(item["id"]))

    def line_ids(record: Mapping[str, Any]) -> set[str]:
        anchors: list[Mapping[str, Any]] = list(record.get("anchors", ()))
        if record.get("source_anchor"):
            anchors.append(record["source_anchor"])
        for key in ("notes", "footnotes", "continuation_anchors", "nearby_variable_definitions", "applicability_anchors", "nested_exception_anchors"):
            anchors.extend(record.get(key, ()))
        return {str(anchor["line_id"]) for anchor in anchors if anchor.get("line_id")}

    for record in (*tables, *figures, *equations, *exceptions):
        ids = line_ids(record)
        internal = sorted({reference for line_id in ids for reference in internal_by_line.get(line_id, ())})
        external = sorted({reference for line_id in ids for reference in external_by_line.get(line_id, ())})
        if record.get("record_type") == "figure":
            record["referenced_sections"] = internal
        else:
            record["internal_references"] = internal
        record["external_references"] = external


def build_attachment_inventory(
    tables: Sequence[Mapping[str, Any]],
    figures: Sequence[Mapping[str, Any]],
    equations: Sequence[Mapping[str, Any]],
    exceptions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    attachments: list[dict[str, Any]] = []

    def add(parent: Mapping[str, Any], kind: str, anchors: Sequence[Mapping[str, Any]], target: str | None = None) -> None:
        for ordinal, anchor in enumerate(anchors):
            attachments.append({
                "id": stable_id("attachment", f"{parent['id']}|{kind}|{ordinal}|{target or ''}"),
                "record_type": "attachment_relationship",
                "parent_record_id": parent["id"],
                "attachment_kind": kind,
                "target_record_id": target,
                "source_anchor": anchor,
                "review_state": parent.get("review_state", ReviewState.PROVISIONAL.value),
            })

    for table in tables:
        add(table, "continuation_caption", table.get("anchors", ())[1:])
        add(table, "table_note", table.get("notes", ()))
        add(table, "table_footnote", table.get("footnotes", ()))
        for target in table.get("nearby_exceptions", ()):
            attachments.append({
                "id": stable_id("attachment", f"{table['id']}|nearby-exception|{target}"),
                "record_type": "attachment_relationship",
                "parent_record_id": table["id"],
                "attachment_kind": "nearby_exception",
                "target_record_id": target,
                "source_anchor": table["anchors"][0],
                "review_state": ReviewState.PROVISIONAL.value,
            })
    for figure in figures:
        add(figure, "repeated_or_continued_caption", figure.get("anchors", ())[1:])
        add(figure, "figure_note", figure.get("notes", ()))
    for equation in equations:
        add(equation, "equation_continuation", equation.get("continuation_anchors", ()))
        add(equation, "variable_definition", equation.get("nearby_variable_definitions", ()))
        add(equation, "applicability", equation.get("applicability_anchors", ()))
    for exception in exceptions:
        add(exception, "nested_exception_item", exception.get("nested_exception_anchors", ()))
        attachments.append({
            "id": stable_id("attachment", f"{exception['id']}|parent-provision|{exception.get('parent_locator')}"),
            "record_type": "attachment_relationship",
            "parent_record_id": exception["id"],
            "attachment_kind": "parent_provision",
            "target_record_id": None,
            "target_locator": exception.get("parent_locator"),
            "source_anchor": exception["source_anchor"],
            "review_state": exception.get("review_state", ReviewState.PROVISIONAL.value),
        })
    return attachments


def build_cross_reference_summary(
    cross_references: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    indegree: dict[str, int] = {}
    edges: set[tuple[str, str]] = set()
    for item in cross_references:
        target = item.get("resolved_target")
        source = item.get("source_section")
        if target:
            indegree[str(target)] = indegree.get(str(target), 0) + 1
        if source and target and item.get("target_kind") == "section":
            edges.add((str(source), str(target)))
    circular_pairs = sorted({tuple(sorted((source, target))) for source, target in edges if source != target and (target, source) in edges})
    resolution: dict[str, int] = {}
    for item in cross_references:
        state = str(item["resolution_state"])
        resolution[state] = resolution.get(state, 0) + 1
    return {
        "resolution_counts": resolution,
        "highly_connected_targets": [
            {"target": target, "incoming_reference_count": count}
            for target, count in sorted(indegree.items(), key=lambda pair: (-pair[1], pair[0]))[:50]
        ],
        "circular_section_reference_pairs": [list(pair) for pair in circular_pairs],
        "appendix_target_reference_count": sum(item.get("target_kind") == "appendix" for item in cross_references),
    }

_TABLE_CLASS_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("occupancy classification", re.compile(r"OCCUPANC|HAZARDOUS MATERIAL", re.I)),
    ("allowable height and area", re.compile(r"ALLOWABLE (?:HEIGHT|AREA)|HEIGHT AND AREA", re.I)),
    ("construction type", re.compile(r"TYPE[S]? OF CONSTRUCTION|BUILDING ELEMENT", re.I)),
    ("fire-resistance rating", re.compile(r"FIRE[- ]RESISTANCE|FIRE RATING", re.I)),
    ("fire separation distance", re.compile(r"FIRE SEPARATION DISTANCE", re.I)),
    ("means-of-egress capacity", re.compile(r"EGRESS CAPACITY|STAIRWAY WIDTH", re.I)),
    ("occupant load", re.compile(r"OCCUPANT LOAD", re.I)),
    ("travel distance", re.compile(r"TRAVEL DISTANCE|COMMON PATH", re.I)),
    ("accessibility dimension", re.compile(r"ACCESSIBLE|WHEELCHAIR|CLEARANCE", re.I)),
    ("structural load", re.compile(r"LOAD|WIND|SNOW|SEISMIC", re.I)),
    ("material property", re.compile(r"MATERIAL|STRENGTH|DENSITY|THICKNESS", re.I)),
    ("inspection requirement", re.compile(r"SPECIAL INSPECTION|INSPECTION", re.I)),
    ("testing requirement", re.compile(r"TEST|TESTING", re.I)),
    ("weather or environmental criterion", re.compile(r"CLIMATE|WEATHER|TEMPERATURE|RAINFALL", re.I)),
)


def classify_tables(tables: list[dict[str, Any]]) -> None:
    for table in tables:
        caption = str(table.get("caption") or "")
        classifications = [name for name, pattern in _TABLE_CLASS_RULES if pattern.search(caption)]
        if not classifications:
            classifications = ["unknown"]
        table["semantic_classifications"] = [
            {
                "classification": name,
                "confidence": 0.8 if name != "unknown" else 0.0,
                "review_state": ReviewState.PROVISIONAL.value,
            }
            for name in classifications
        ]


def _pilot_structural_verification(item: Mapping[str, Any], semantic_type: str) -> dict[str, Any]:
    """Describe exercised structural features without asserting regulatory meaning."""
    record_type = str(item.get("record_type"))
    features: list[str] = []
    qualifications: list[str] = []

    if record_type == "table":
        if item.get("continuation_pages"):
            features.append("multi_page_continuation")
        if item.get("units"):
            features.append("dimensional_units")
        if item.get("footnotes") or item.get("notes"):
            features.append("footnotes_or_notes")
        if item.get("nearby_exceptions"):
            features.append("nearby_exception_relationship")
        if item.get("internal_references"):
            features.append("internal_cross_reference")
        if item.get("external_references"):
            features.append("external_standard_relationship")
        if item.get("section_context"):
            features.append("table_to_prose_applicability_anchor")
        if item.get("published_identifier") == "307.1(1)":
            features.append("hierarchical_or_merged_headers")
            qualifications.append(
                "The representative source geometry exercises a multi-level header candidate; "
                "semantic row-span and column-span meaning remains unreviewed."
            )
    elif record_type == "figure":
        if item.get("section_context"):
            features.append("figure_to_prose_relationship")
        if item.get("nearby_exceptions"):
            features.append("nearby_exception_relationship")
        if item.get("related_tables") or item.get("referenced_sections"):
            features.append("internal_cross_reference")
        if item.get("notes"):
            features.append("footnotes_or_notes")
        if item.get("dimensions"):
            features.append("dimensional_units")
    elif record_type == "equation":
        features.append("displayed_formula")
        if item.get("units"):
            features.append("dimensional_units")
        if item.get("internal_references") or item.get("referenced_sections") or item.get("referenced_tables"):
            features.append("internal_cross_reference")
        if item.get("external_references"):
            features.append("external_standard_relationship")
        if item.get("exceptions"):
            features.append("nearby_exception_relationship")
        if item.get("applicability_anchors") or item.get("nearby_variable_definitions"):
            features.append("table_to_prose_applicability_anchor")
    elif record_type == "chapter35_referenced_standard_entry":
        features.append("external_standard_relationship")
        if item.get("referenced_ibc_sections"):
            features.append("internal_cross_reference")
    elif record_type == "definition":
        features.append("chapter_specific_terminology")
        if item.get("internal_references"):
            features.append("internal_cross_reference")
        if item.get("external_references"):
            features.append("external_standard_relationship")
    elif record_type == "exception_block":
        features.append("nearby_exception_relationship")
        if item.get("internal_references"):
            features.append("internal_cross_reference")

    if semantic_type not in {"unknown", "displayed_equation_or_formula_block", "referenced_standard_entry"}:
        features.append("chapter_specific_terminology")

    if not qualifications:
        qualifications.append(
            "Source identity, location, and structural attachment are checked; legal effect and applicability are not."
        )
    return {
        "features": sorted(set(features)),
        "source_anchor_verified": True,
        "record_shape_verified": True,
        "semantic_interpretation_verified": False,
        "qualifications": qualifications,
    }


def build_semantic_pilot(
    tables: Sequence[Mapping[str, Any]],
    figures: Sequence[Mapping[str, Any]],
    equations: Sequence[Mapping[str, Any]],
    chapter35_rows: Sequence[Mapping[str, Any]],
    definitions: Sequence[Mapping[str, Any]],
    exceptions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    target_chapters = ("3", "5", "6", "7", "10", "11", "16", "17", "35")
    pilot: list[dict[str, Any]] = []
    for chapter in target_chapters:
        if chapter == "35":
            candidates: list[Mapping[str, Any]] = list(chapter35_rows[:3])
        else:
            collections = (
                [item for item in tables if item.get("chapter") == chapter],
                [item for item in figures if item.get("chapter") == chapter],
                [item for item in equations if item.get("source_anchor", {}).get("chapter") == chapter],
            )
            candidates = [collection[0] for collection in collections if collection]
            if len(candidates) < 3:
                seen = {item["id"] for item in candidates}
                remainder = [item for collection in collections for item in collection if item["id"] not in seen]
                candidates.extend(remainder[: 3 - len(candidates)])
        for item in candidates[:3]:
            if item["record_type"] == "table":
                semantic_type = item.get("semantic_classifications", [{}])[0].get("classification", "unknown")
            elif item["record_type"] == "figure":
                semantic_type = item.get("semantic_category", "unknown")
            elif item["record_type"] == "equation":
                semantic_type = "displayed_equation_or_formula_block"
            elif item["record_type"] == "chapter35_referenced_standard_entry":
                semantic_type = "referenced_standard_entry"
            else:
                semantic_type = "unknown"
            pilot.append(
                {
                    "id": stable_id("semantic-pilot", f"{chapter}|{item['id']}"),
                    "record_type": "semantic_pilot_record",
                    "chapter": chapter,
                    "source_record_id": item["id"],
                    "source_record_type": item["record_type"],
                    "interpretation": {
                        "semantic_type": semantic_type,
                        "applicability": "not_interpreted",
                        "normative_status": "unreviewed",
                        "requirement_interpretation": None,
                        "model_checking_projection": None,
                    },
                    "structural_verification": _pilot_structural_verification(item, semantic_type),
                    "evidence": [item["id"]],
                    "confidence": 0.45,
                    "review_state": ReviewState.PROVISIONAL.value,
                    "reviewer_notes": "Representative structural record only; no legal or compliance interpretation asserted.",
                }
            )
    # Exercise definition scope and exception attachment explicitly.
    for collection, label in ((definitions, "definition"), (exceptions, "exception")):
        for item in collection[:1]:
            semantic_type = label
            pilot.append(
                {
                    "id": stable_id("semantic-pilot", f"{label}|{item['id']}"),
                    "record_type": "semantic_pilot_record",
                    "chapter": item.get("source_anchor", {}).get("chapter"),
                    "source_record_id": item["id"],
                    "source_record_type": item["record_type"],
                    "interpretation": {"semantic_type": label, "applicability": "not_interpreted"},
                    "structural_verification": _pilot_structural_verification(item, semantic_type),
                    "evidence": [item["id"]],
                    "confidence": 0.5,
                    "review_state": ReviewState.PROVISIONAL.value,
                    "reviewer_notes": "Attachment and scope preservation pilot.",
                }
            )
    return pilot


def build_source_manifest(
    *,
    pdf_metadata: Mapping[str, Any],
    ingestion_timestamp: str,
    parser_version: str,
) -> dict[str, Any]:
    return {
        "schema_version": CORPUS_SCHEMA_VERSION,
        "record_type": "source_artifact",
        "code_family": "IBC",
        "edition": "2018",
        "publication_title": "2018 International Building Code",
        "publisher": "International Code Council, Inc.",
        "first_printing": "August 2017",
        "date_of_first_publication": "2017-08-31",
        "source_filename": "icc-2018.pdf",
        "sha256": SOURCE_SHA256,
        "file_size_bytes": SOURCE_SIZE_BYTES,
        "pdf_page_count": SOURCE_PAGE_COUNT,
        "pdf_metadata": dict(pdf_metadata),
        "printed_page_mapping": {
            "front_matter": {"pdf_pages": [4, 27], "printed_pages": ["iii", "xxvi"]},
            "arabic": {"pdf_pages": [28, 759], "formula": "printed_page = pdf_page - 27"},
            "unprinted": [1, 2, 3, 760, 761],
        },
        "publication_sections": list(PUBLICATION_SECTIONS),
        "acquisition_provenance": {
            "source": "user-connected private file storage",
            "retrieved_for_local_analysis": True,
            "private_connector_identifier_retained": False,
            "substitution": None,
            "source_observation": "The supplied bytes contain recurring EDUFIRE.IR / Telegram EDUFIRE_IR marks not identified as ICC publication furniture.",
            "official_copy_comparison": {
                "status": "not_performed",
                "reason": "No independently obtained official byte-identical copy was available in the execution environment.",
                "future_comparison_policy": "Preserve this exact processed artifact and register any comparison copy as a separate source artifact.",
            },
            "artifact_custody": {
                "raw_source_location": "private_local_uncommitted",
                "derived_reconstructive_evidence": "private_local_uncommitted",
                "public_derivatives": "source_safe_only",
                "replacement_policy": "new source artifact record required",
            },
        },
        "identity_assurance": {
            "exact_bytes": "verified",
            "publication_identity_from_artifact": "verified",
            "official_copy_equivalence": "unverified",
            "source_copy_markings": "observed_and_not_treated_as_official_furniture",
        },
        "access_restrictions": {
            "copyright_owner": "International Code Council, Inc.",
            "copyright_year": 2017,
            "redistribution": "restricted",
            "public_repository_policy": "PDF, page images, substantial text, and reconstructive extracts remain local/private and uncommitted.",
            "pdf_permissions": {
                "encrypted": True,
                "algorithm": "AES-128 Standard V4 R4",
                "print": True,
                "copy": False,
                "modify": True,
                "annotate": True,
            },
        },
        "ingestion_timestamp": ingestion_timestamp,
        "parser": {
            "corpus_builder_version": parser_version,
            "positioned_source_backend": "Poppler pdftotext -bbox-layout",
            "source_audit_backend": "PyMuPDF geometry-aware IBC layout branch",
            "evidence_layer": "derived page-line evidence; semantic promotion requires review",
        },
        "verification_state": ReviewState.VERIFIED.value,
    }


def count_by_context(records: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        chapter = record.get("chapter")
        appendix = record.get("appendix")
        anchor = record.get("source_anchor") or {}
        chapter = chapter or anchor.get("chapter")
        appendix = appendix or anchor.get("appendix")
        key = f"chapter:{chapter}" if chapter else (f"appendix:{appendix}" if appendix else "other")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def build_coverage_report(
    inventories: Mapping[str, Sequence[Mapping[str, Any]]],
    cross_references: Sequence[Mapping[str, Any]],
    chapter35_rows: Sequence[Mapping[str, Any]],
    external_families: Sequence[Mapping[str, Any]],
    external_citations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    resolution_counts: dict[str, int] = {}
    for record in cross_references:
        state = str(record["resolution_state"])
        resolution_counts[state] = resolution_counts.get(state, 0) + 1
    tables = inventories.get("tables", ())
    figures = inventories.get("figures", ())
    exceptions = inventories.get("exceptions", ())
    matched_family_ids = {
        str(item["normalized_document_family_id"])
        for item in external_citations
        if item.get("normalized_document_family_id")
    }
    all_family_ids = {str(item["id"]) for item in external_families}
    return {
        "schema_version": CORPUS_SCHEMA_VERSION,
        "record_type": "coverage_report",
        "source_sha256": SOURCE_SHA256,
        "counting_policy_version": COUNTING_POLICY_VERSION,
        "counts": {name: len(records) for name, records in inventories.items()},
        "caption_occurrences": {
            "table": sum(len(item.get("anchors", ())) for item in tables),
            "figure": sum(len(item.get("anchors", ())) for item in figures),
        },
        "exception_structure": {
            "explicit_marker_block_count": len(exceptions),
            "nested_numbered_child_count": sum(
                len(item.get("nested_exception_numbers", ())) for item in exceptions
            ),
        },
        "counts_by_context": {
            name: count_by_context(records)
            for name, records in inventories.items()
            if name not in {"cross_references", "external_citations", "detections"}
        },
        "chapter35": {
            "row_count": len(chapter35_rows),
            "individual_designation_count": len({str(row["observed_designation_with_edition"]) for row in chapter35_rows}),
            "normalized_family_count": len(external_families),
            "families_not_detected_elsewhere_count": len(all_family_ids - matched_family_ids),
        },
        "external_references": {
            "citation_occurrence_count": len(external_citations),
            "matched_family_count": len(matched_family_ids),
            "unmatched_occurrence_count": sum(item["normalized_document_family_id"] is None for item in external_citations),
            "alias_family_candidate_count": sum(
                len(item.get("observed_designations", ())) > 1 for item in external_families
            ),
        },
        "internal_reference_resolution": resolution_counts,
        "validation_state": ReviewState.PROVISIONAL.value,
        "known_limitations": [
            "Inventory acceptance is structural; semantic meaning remains unreviewed unless explicitly stated.",
            "The normalized uncaptioned-diagram inventory currently accepts raster technical-graphic candidates; vector-only drawing regions remain an explicit review backlog rather than being silently classified.",
            "Equation candidates intentionally exclude formula-like cells inside detected formal table and figure regions.",
            "External citation occurrence matching is lexical and preserves unresolved normalizations for review.",
            "Printed source text is retained only in private evidence. Public records use identifiers, coordinates, hashes, and constrained captions.",
        ],
    }


def validate_inventory(
    source_manifest: Mapping[str, Any],
    inventories: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    discrepancies: list[dict[str, Any]] = []
    if source_manifest.get("sha256") != SOURCE_SHA256:
        discrepancies.append({"code": "source-hash-mismatch", "severity": "error"})
    if source_manifest.get("pdf_page_count") != SOURCE_PAGE_COUNT:
        discrepancies.append({"code": "page-count-mismatch", "severity": "error"})
    for name, records in inventories.items():
        ids = [str(item.get("id")) for item in records]
        for duplicate in sorted({item for item in ids if ids.count(item) > 1}):
            discrepancies.append(
                {"code": "duplicate-logical-structure", "severity": "error", "inventory": name, "record_id": duplicate}
            )
        for item in records:
            if not item.get("id"):
                discrepancies.append({"code": "missing-id", "severity": "error", "inventory": name})
    for table in inventories.get("tables", ()):
        pages = table.get("pdf_page_range")
        if pages and pages[0] > pages[1]:
            discrepancies.append({"code": "split-continuation", "severity": "error", "record_id": table["id"]})
    for exception in inventories.get("exceptions", ()):
        if not exception.get("parent_locator"):
            discrepancies.append({"code": "exception-detachment", "severity": "review", "record_id": exception["id"]})
    for figure in inventories.get("figures", ()):
        if not figure.get("caption"):
            discrepancies.append({"code": "figure-caption-detachment", "severity": "review", "record_id": figure["id"]})
    return discrepancies
