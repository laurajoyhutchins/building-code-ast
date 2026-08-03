"""Private vector-region evidence extraction for the exact 2018 IBC PDF.

The extractor emits geometry summaries only. It deliberately excludes page text,
page images, and path coordinates detailed enough to reconstruct the source.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

SOURCE_SHA256 = "c8f0b75522707a39daf5202edee25d7fdce6c177c382f828a6dc1dfd5cc0b18d"
SOURCE_SIZE_BYTES = 32_608_171
SOURCE_PAGE_COUNT = 761

BBox = tuple[float, float, float, float]


def _bbox(value: Sequence[float]) -> BBox:
    if len(value) != 4:
        raise ValueError("vector drawing bbox must have four coordinates")
    x0, y0, x1, y1 = (float(item) for item in value)
    if x1 < x0 or y1 < y0:
        raise ValueError("vector drawing bbox coordinates must be ordered")
    return (x0, y0, x1, y1)


def _area(box: BBox) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def _intersection_area(first: BBox, second: BBox) -> float:
    x0 = max(first[0], second[0])
    y0 = max(first[1], second[1])
    x1 = min(first[2], second[2])
    y1 = min(first[3], second[3])
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def _near_or_overlapping(first: BBox, second: BBox, gap: float) -> bool:
    return not (
        first[2] + gap < second[0]
        or second[2] + gap < first[0]
        or first[3] + gap < second[1]
        or second[3] + gap < first[1]
    )


def _round_bbox(box: BBox) -> list[float]:
    return [round(value, 3) for value in box]


def normalize_drawing(
    drawing: Mapping[str, Any],
    *,
    page_width: float,
    page_height: float,
    text_boxes: Sequence[Sequence[float]],
) -> dict[str, Any] | None:
    """Reduce one PyMuPDF drawing path to source-safe geometry statistics."""

    if "rect" not in drawing:
        return None
    box = _bbox(drawing["rect"])
    width = box[2] - box[0]
    height = box[3] - box[1]
    area = _area(box)
    page_area = page_width * page_height

    # White page backgrounds and near-page-size clipping rectangles are not content.
    if page_area and area >= page_area * 0.85:
        return None

    item_types = [str(item[0]) for item in drawing.get("items", ()) if item]
    line_count = item_types.count("l")
    curve_count = item_types.count("c")
    rect_count = item_types.count("re") + item_types.count("qu")
    fill_count = int(drawing.get("fill") is not None or "f" in str(drawing.get("type", "")))
    stroke_count = int(drawing.get("color") is not None or "s" in str(drawing.get("type", "")))

    # This PDF outlines most glyphs as vector paths. Suppress small paths that sit
    # inside text blocks, while retaining long rules and materially sized graphics.
    within_text = False
    for raw_text_box in text_boxes:
        text_box = _bbox(raw_text_box)
        overlap = _intersection_area(box, text_box)
        if area and overlap / area >= 0.9:
            within_text = True
            break
    long_rule = max(width, height) >= 24.0 and min(width, height) <= 2.5
    materially_sized = area >= 400.0 or (width >= 20.0 and height >= 20.0)
    if within_text and not long_rule:
        return None
    if not (long_rule or materially_sized):
        return None

    return {
        "bbox": _round_bbox(box),
        "line_count": line_count,
        "curve_count": curve_count,
        "rect_count": rect_count,
        "fill_count": fill_count,
        "stroke_count": stroke_count,
    }


def geometry_fingerprint(drawings: Iterable[Mapping[str, Any]]) -> str:
    material = []
    for drawing in drawings:
        material.append(
            {
                "bbox": [round(float(value), 3) for value in drawing["bbox"]],
                "line_count": int(drawing.get("line_count", 0)),
                "curve_count": int(drawing.get("curve_count", 0)),
                "rect_count": int(drawing.get("rect_count", 0)),
                "fill_count": int(drawing.get("fill_count", 0)),
                "stroke_count": int(drawing.get("stroke_count", 0)),
            }
        )
    material.sort(key=lambda item: (item["bbox"], item["line_count"], item["curve_count"], item["rect_count"]))
    payload = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def cluster_vector_drawings(
    drawings: Sequence[Mapping[str, Any]],
    *,
    pdf_page: int,
    gap: float = 8.0,
) -> list[dict[str, Any]]:
    """Cluster nearby drawing paths into deterministic page-local regions."""

    material = sorted(
        (dict(item) for item in drawings),
        key=lambda item: tuple(float(value) for value in item["bbox"]),
    )
    parent = list(range(len(material)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    boxes = [_bbox(item["bbox"]) for item in material]
    for left in range(len(material)):
        for right in range(left + 1, len(material)):
            if boxes[right][0] > boxes[left][2] + gap and boxes[right][1] > boxes[left][3] + gap:
                continue
            if _near_or_overlapping(boxes[left], boxes[right], gap):
                union(left, right)

    groups: dict[int, list[dict[str, Any]]] = {}
    for index, drawing in enumerate(material):
        groups.setdefault(find(index), []).append(drawing)

    regions: list[dict[str, Any]] = []
    for group in groups.values():
        group_boxes = [_bbox(item["bbox"]) for item in group]
        union_box = (
            min(box[0] for box in group_boxes),
            min(box[1] for box in group_boxes),
            max(box[2] for box in group_boxes),
            max(box[3] for box in group_boxes),
        )
        regions.append(
            {
                "pdf_page": pdf_page,
                "bbox": _round_bbox(union_box),
                "drawing_count": len(group),
                "line_count": sum(int(item.get("line_count", 0)) for item in group),
                "curve_count": sum(int(item.get("curve_count", 0)) for item in group),
                "rect_count": sum(int(item.get("rect_count", 0)) for item in group),
                "fill_count": sum(int(item.get("fill_count", 0)) for item in group),
                "stroke_count": sum(int(item.get("stroke_count", 0)) for item in group),
                "geometry_fingerprint": geometry_fingerprint(group),
            }
        )
    return sorted(regions, key=lambda item: (item["bbox"], item["geometry_fingerprint"]))


def extract_page_vector_regions(page: Any, *, pdf_page: int) -> dict[str, Any]:
    text_boxes = [tuple(float(value) for value in block[:4]) for block in page.get_text("blocks")]
    drawings = []
    for drawing in page.get_cdrawings():
        normalized = normalize_drawing(
            drawing,
            page_width=float(page.rect.width),
            page_height=float(page.rect.height),
            text_boxes=text_boxes,
        )
        if normalized is not None:
            drawings.append(normalized)
    return {
        "pdf_page": pdf_page,
        "page_size_points": [round(float(page.rect.width), 3), round(float(page.rect.height), 3)],
        "regions": cluster_vector_drawings(drawings, pdf_page=pdf_page),
    }


def extract_document_vector_evidence(
    document: Any,
    *,
    source_sha256: str,
    source_size_bytes: int,
) -> dict[str, Any]:
    page_count = int(document.page_count)
    return {
        "schema_version": "0.1.0",
        "source_sha256": source_sha256,
        "source_size_bytes": int(source_size_bytes),
        "source_page_count": page_count,
        "pages": [
            extract_page_vector_regions(document[index], pdf_page=index + 1)
            for index in range(page_count)
        ],
    }


def validate_vector_evidence(evidence: Mapping[str, Any]) -> None:
    if evidence.get("source_sha256") != SOURCE_SHA256:
        raise ValueError("vector evidence source SHA-256 does not match the registered IBC source")
    if evidence.get("source_size_bytes") != SOURCE_SIZE_BYTES:
        raise ValueError("vector evidence source size does not match the registered IBC source")
    if evidence.get("source_page_count") != SOURCE_PAGE_COUNT:
        raise ValueError("vector evidence source page count does not match 761")
    pages = evidence.get("pages")
    if not isinstance(pages, Sequence):
        raise ValueError("vector evidence pages must be a sequence")
    page_numbers = [int(item["pdf_page"]) for item in pages]
    if page_numbers != list(range(1, SOURCE_PAGE_COUNT + 1)):
        raise ValueError("vector evidence must cover all 761 PDF pages in order")
