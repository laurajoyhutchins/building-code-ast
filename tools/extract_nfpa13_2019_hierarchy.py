#!/usr/bin/env python3
"""Extract an NFPA 13 (2019) clause hierarchy from a locally supplied PDF.

The output contains clause identifiers, headings, hierarchy, and PDF anchors.
Clause bodies, tables, figures, and the source PDF are intentionally excluded.
PyMuPDF is required only when the extractor is executed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    import fitz  # type: ignore[import-untyped]
except ModuleNotFoundError:
    fitz = None  # type: ignore[assignment]

ARTIFACT_ID = "nfpa:13"
EDITION_ID = "2019"
SCHEMA = "nfpa-clause-hierarchy/0.1.0"
CLAUSE_RE = re.compile(
    r"^(?P<locator>(?:[A-F]\.\d+(?:\.\d+)*|\d+(?:\.\d+)+))"
    r"(?P<star>\*)?(?=\s|$)"
)
BOOKMARK_RE = re.compile(
    r"^(?P<locator>(?:[A-F]\.\d+(?:\.\d+)*|\d+(?:\.\d+)+))"
    r"(?P<star>\*)?\s+(?P<title>.+?)\s*$"
)
CHAPTER_RE = re.compile(r"^Chapter\s+(?P<locator>\d+)\s+(?P<title>.+?)\s*$")
ANNEX_RE = re.compile(r"^Annex\s+(?P<locator>[A-F])\s+(?P<title>.+?)\s*$")
PRINTED_PAGE_RE = re.compile(r"\b13-(?P<number>\d+)\b")
ALLOWED_X = (36.0, 48.0, 54.0, 66.0, 309.0, 321.0, 327.0, 339.0)


@dataclass
class Line:
    text: str
    bbox: tuple[float, float, float, float]
    spans: list[dict[str, Any]]
    column: int

    @property
    def first_span(self) -> dict[str, Any] | None:
        return next((span for span in self.spans if str(span.get("text", "")).strip()), None)


def _pdf_module() -> Any:
    if fitz is None:
        raise RuntimeError(
            "NFPA 13 extraction requires PyMuPDF; install it with "
            "`python -m pip install pymupdf`."
        )
    return fitz


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _node_id(locator: str, node_type: str) -> str:
    payload = {
        "artifact_id": ARTIFACT_ID,
        "edition_id": EDITION_ID,
        "locator": locator,
        "node_type": node_type,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "docnode:" + hashlib.sha256(canonical.encode()).hexdigest()


def _node_type(locator: str) -> str:
    depth = len(locator.split("."))
    return "chapter" if depth == 1 else "section" if depth == 2 else "subsection" if depth == 3 else "paragraph"


def _parent(locator: str) -> str:
    parts = locator.split(".")
    return "document" if len(parts) == 1 else ".".join(parts[:-1])


def _clean_heading(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    return value[:-1].rstrip() if value.endswith(".") else value


def _initial_bold(line: Line) -> str:
    pieces: list[str] = []
    for span in line.spans:
        if str(span.get("font", "")).startswith("NewBaskervilleStd-Bold"):
            pieces.append(str(span.get("text", "")))
        else:
            break
    return "".join(pieces).strip()


def _revision_marker(line: Line) -> bool:
    first = line.first_span
    return bool(
        first
        and len(_initial_bold(line)) <= 2
        and "BoldIt" in str(first.get("font", ""))
    )


def _join(left: str, right: str) -> str:
    left, right = left.rstrip(), right.lstrip()
    if left.endswith(("‐", "\u00ad")):
        return left[:-1] + right
    if left.endswith("-"):
        return left + right
    return f"{left} {right}" if left else right


def _finished(value: str) -> bool:
    return value.rstrip().endswith((".", ":", "(Reserved)"))


def _page_lines(page: Any) -> list[Line]:
    lines: list[Line] = []
    for block in page.get_text("dict", sort=False).get("blocks", []):
        for raw in block.get("lines", []):
            spans = [span for span in raw.get("spans", []) if span.get("text")]
            text = "".join(str(span["text"]) for span in spans).strip()
            if not text:
                continue
            bbox = tuple(float(value) for value in raw["bbox"])
            lines.append(Line(text, bbox, spans, 0 if bbox[0] < 306 else 1))
    return sorted(lines, key=lambda item: (item.column, item.bbox[1], item.bbox[0]))


def _heading(lines: list[Line], index: int) -> str | None:
    source = lines[index]
    heading = CLAUSE_RE.sub("", _initial_bold(source), count=1).strip()
    if not heading:
        return None

    cursor = index
    while cursor + 1 < len(lines):
        current, following = lines[cursor], lines[cursor + 1]
        gap = following.bbox[0] - current.bbox[2]
        if (
            following.column != source.column
            or abs(following.bbox[1] - current.bbox[1]) > 1.5
            or not -1.0 <= gap <= 18.0
            or CLAUSE_RE.match(following.text)
            or _revision_marker(following)
        ):
            break
        prefix = _initial_bold(following)
        if not prefix:
            break
        heading = _join(heading, prefix)
        cursor += 1

    while not _finished(heading) and cursor + 1 < len(lines):
        following = lines[cursor + 1]
        if following.column != source.column or CLAUSE_RE.match(following.text):
            break
        if following.bbox[1] - lines[cursor].bbox[3] > 8.0:
            break
        if _revision_marker(following):
            cursor += 1
            continue
        prefix = _initial_bold(following)
        if not prefix or abs(following.bbox[0] - source.bbox[0]) > 3.0:
            break
        heading = _join(heading, prefix)
        cursor += 1
    return _clean_heading(heading)


def _outline(doc: Any) -> tuple[list[dict[str, Any]], dict[str, str], int, int]:
    toc = doc.get_toc(simple=True)
    root = next(i for i, row in enumerate(toc) if row[0] == 1 and row[1].strip() == "NFPA 13")
    end = next(i for i in range(root + 1, len(toc)) if toc[i][0] == 1)
    containers: list[dict[str, Any]] = []
    headings: dict[str, str] = {}
    index_page: int | None = None

    for level, raw_title, page in toc[root + 1 : end]:
        title = " ".join(raw_title.split())
        if level == 3 and (match := BOOKMARK_RE.match(title)):
            headings[match.group("locator")] = _clean_heading(match.group("title")) or ""
        if level != 2:
            continue
        match = CHAPTER_RE.match(title) or ANNEX_RE.match(title)
        if match:
            containers.append(
                {
                    "locator": match.group("locator"),
                    "title": match.group("title").strip(),
                    "pdf_page": page,
                    "kind": "chapter" if title.startswith("Chapter") else "annex",
                }
            )
        elif title == "Index":
            index_page = page

    if not containers or index_page is None:
        raise RuntimeError("NFPA 13 bookmark boundaries were not found")
    return containers, headings, min(item["pdf_page"] for item in containers), index_page - 1


def _records(doc: Any, first_page: int, last_page: int, bookmark_headings: dict[str, str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for pdf_page in range(first_page, last_page + 1):
        page = doc[pdf_page - 1]
        page_text = page.get_text("text")[:400]
        printed_match = PRINTED_PAGE_RE.search(page_text)
        printed_page = f"13-{printed_match.group('number')}" if printed_match else None
        lines = _page_lines(page)
        for index, line in enumerate(lines):
            match = CLAUSE_RE.match(line.text)
            first = line.first_span
            if not match or not first:
                continue
            if not str(first.get("font", "")).startswith("NewBaskervilleStd-Bold"):
                continue
            if abs(float(first.get("size", 0.0)) - 9.0) > 0.05:
                continue
            if not any(abs(line.bbox[0] - x) <= 2.2 for x in ALLOWED_X):
                continue
            first_match = CLAUSE_RE.match(str(first.get("text", "")).strip())
            if not first_match or first_match.group("locator") != match.group("locator"):
                continue

            locator = match.group("locator")
            heading = bookmark_headings.get(locator, _heading(lines, index))
            references: list[str] = []
            if heading and (bracket := re.fullmatch(r"\[(.+)]", heading)):
                references = [
                    part.strip()
                    for part in re.split(r"\s+(?:and|or)\s+|,", bracket.group(1))
                    if part.strip()
                ]
                heading = None
            records.append(
                {
                    "locator": locator,
                    "starred": bool(match.group("star")),
                    "heading": heading,
                    "references": references,
                    "source": {
                        "pdf_page": pdf_page,
                        "printed_page": printed_page,
                        "bbox": [round(value, 3) for value in line.bbox],
                    },
                }
            )
    duplicates = [key for key, count in Counter(r["locator"] for r in records).items() if count > 1]
    if duplicates:
        raise RuntimeError(f"Duplicate clause locators: {sorted(duplicates)[:20]}")
    return records


def _node(locator: str, label: str | None, attributes: dict[str, str], source: Any = None) -> dict[str, Any]:
    node_type = _node_type(locator)
    return {
        "node_id": _node_id(locator, node_type),
        "type": node_type,
        "locator": locator,
        "label": label,
        "parent_locator": _parent(locator),
        "children": [],
        "attributes": attributes,
        "source": source,
    }


def extract(pdf_path: Path) -> dict[str, Any]:
    pdf = _pdf_module()
    doc = pdf.open(pdf_path)
    containers, bookmark_headings, first_page, last_page = _outline(doc)
    records = _records(doc, first_page, last_page, bookmark_headings)
    source_pages = doc.page_count
    doc.close()

    nodes: dict[str, dict[str, Any]] = {
        "document": {
            "node_id": _node_id("document", "document"),
            "type": "document",
            "locator": "document",
            "label": "NFPA 13: Standard for the Installation of Sprinkler Systems",
            "parent_locator": None,
            "children": [],
            "attributes": {"artifact_id": ARTIFACT_ID, "edition_id": EDITION_ID},
        }
    }
    for item in containers:
        nodes[item["locator"]] = _node(
            item["locator"],
            item["title"],
            {"container_kind": item["kind"]},
            {"pdf_page": item["pdf_page"]},
        )

    explicit = {record["locator"] for record in records}
    implicit: set[str] = set()
    for record in records:
        locator = record["locator"]
        if not locator.startswith("A."):
            continue
        parts = locator.split(".")
        implicit.update(".".join(parts[:length]) for length in range(2, len(parts)) if ".".join(parts[:length]) not in explicit)
    for locator in implicit:
        nodes[locator] = _node(
            locator,
            None,
            {"implicit": "true", "annex": "A", "corresponds_to": locator.removeprefix("A.")},
        )

    for record in records:
        locator = record["locator"]
        attributes = {"explicit": "true", "starred": str(record["starred"]).lower()}
        if locator[0].isalpha():
            attributes["annex"] = locator[0]
        if locator.startswith("A."):
            attributes["corresponds_to"] = locator.removeprefix("A.")
        nodes[locator] = _node(locator, record["heading"], attributes, record["source"])
        nodes[locator]["references"] = record["references"]

    missing: list[tuple[str, str]] = []
    for locator, node in nodes.items():
        parent = node["parent_locator"]
        if parent is None:
            continue
        if parent not in nodes:
            missing.append((locator, parent))
        else:
            nodes[parent]["children"].append(node)
    if missing:
        raise RuntimeError(f"Missing hierarchy parents: {missing[:20]}")

    def key(node: dict[str, Any]) -> tuple[tuple[int, Any], ...]:
        return tuple((0, int(part)) if part.isdigit() else (1, part) for part in node["locator"].split("."))

    def sort(node: dict[str, Any]) -> None:
        node["children"].sort(key=key)
        for child in node["children"]:
            sort(child)

    sort(nodes["document"])
    statistics = {
        "chapters": sum(item["kind"] == "chapter" for item in containers),
        "annexes": sum(item["kind"] == "annex" for item in containers),
        "explicit_clauses": len(records),
        "implicit_annex_a_containers": len(implicit),
        "total_nodes_including_root": len(nodes),
        "starred_clauses": sum(record["starred"] for record in records),
        "clauses_with_headings": sum(record["heading"] is not None for record in records),
    }
    catalog = {
        "schema": SCHEMA,
        "source": {
            "artifact_id": ARTIFACT_ID,
            "edition_id": EDITION_ID,
            "title": "NFPA 13: Standard for the Installation of Sprinkler Systems",
            "file_name": pdf_path.name,
            "source_pdf_sha256": _sha256(pdf_path),
            "source_pdf_pages": source_pages,
            "nfpa13_first_pdf_page": first_page,
            "nfpa13_last_clause_pdf_page": last_page,
        },
        "statistics": statistics,
        "root": nodes["document"],
    }
    validation = validate(catalog)
    if not validation["passed"]:
        raise RuntimeError(f"Hierarchy validation failed: {validation}")
    return catalog


def _walk(node: dict[str, Any]) -> Iterable[dict[str, Any]]:
    yield node
    for child in node.get("children", []):
        yield from _walk(child)


def validate(catalog: dict[str, Any]) -> dict[str, Any]:
    nodes = list(_walk(catalog["root"]))
    by_locator = {node["locator"]: node for node in nodes}
    duplicate_locators = [key for key, count in Counter(node["locator"] for node in nodes).items() if count > 1]
    duplicate_ids = [key for key, count in Counter(node["node_id"] for node in nodes).items() if count > 1]
    missing_parents = [
        (node["locator"], node["parent_locator"])
        for node in nodes
        if node["parent_locator"] is not None and node["parent_locator"] not in by_locator
    ]
    bad_ids = [
        node["locator"]
        for node in nodes
        if node["node_id"] != _node_id(node["locator"], node["type"])
    ]
    bad_annex_links = [
        node["locator"]
        for node in nodes
        if node["locator"].startswith("A.")
        and node["attributes"].get("corresponds_to") not in by_locator
    ]
    passed = not (duplicate_locators or duplicate_ids or missing_parents or bad_ids or bad_annex_links)
    return {
        "passed": passed,
        "node_count": len(nodes),
        "duplicate_locators": duplicate_locators,
        "duplicate_node_ids": duplicate_ids,
        "missing_parents": missing_parents,
        "invalid_deterministic_ids": bad_ids,
        "annex_a_links_without_normative_target": bad_annex_links,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output", type=Path, default=Path("nfpa13-2019-clause-hierarchy.json"))
    args = parser.parse_args()
    catalog = extract(args.pdf)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(catalog["statistics"], indent=2))
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
