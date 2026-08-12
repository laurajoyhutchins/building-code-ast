from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

_FORBIDDEN_SOURCE_SUFFIXES = {
    ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp", ".gif"
}


@dataclass(frozen=True)
class VisualObject:
    corpus_id: str
    kind: str
    occurrence_id: str
    label: str
    page: int
    source_sha256: str
    logical_visual_id: str | None = None
    title: str = ""
    structural_context: str = ""
    caption_text_quality: str = "usable"

    def __post_init__(self) -> None:
        if self.logical_visual_id is None:
            object.__setattr__(self, "logical_visual_id", self.occurrence_id)
        if not re.fullmatch(r"[0-9a-fA-F]{64}", self.source_sha256):
            raise ValueError("source_sha256 must be a 64-character hex SHA-256")
        if self.caption_text_quality not in {"usable", "degraded", "unavailable"}:
            raise ValueError("caption_text_quality must be usable, degraded, or unavailable")


@dataclass(frozen=True)
class ViewBox:
    name: str
    x0: int
    y0: int
    x1: int
    y1: int


@dataclass(frozen=True)
class VerificationReport:
    ok: bool
    forbidden_files: list[str]
    errors: list[str]


def _crop_box(width: int, height: int, fraction: float, ax: float, ay: float, name: str) -> ViewBox:
    crop_w = max(1, min(width, int(round(width * fraction))))
    crop_h = max(1, min(height, int(round(height * fraction))))
    max_x = width - crop_w
    max_y = height - crop_h
    x0 = int(round(max_x * ax))
    y0 = int(round(max_y * ay))
    return ViewBox(name, x0, y0, x0 + crop_w, y0 + crop_h)


def multiscale_view_boxes(width: int, height: int, *, include_fine: bool = False) -> list[ViewBox]:
    """Return deterministic global, medium, and optional fine 2-D view boxes.

    Medium views cover 72% of each dimension. Fine views cover 50%. The five anchors
    preserve 2-D locality across portrait, landscape, and roughly square technical figures.
    """
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    anchors = [
        (0.0, 0.0, "ul"),
        (1.0, 0.0, "ur"),
        (0.0, 1.0, "ll"),
        (1.0, 1.0, "lr"),
        (0.5, 0.5, "center"),
    ]
    out = [ViewBox("global", 0, 0, width, height)]
    out.extend(_crop_box(width, height, 0.72, ax, ay, f"medium_{suffix}") for ax, ay, suffix in anchors)
    if include_fine:
        out.extend(_crop_box(width, height, 0.50, ax, ay, f"fine_{suffix}") for ax, ay, suffix in anchors)
    return out


def context_text(obj: VisualObject, *, max_words: int = 60) -> str:
    """Pack CLIP/text context by evidence priority without discarding full metadata.

    Published labels are highest priority, then usable caption text, then structural
    ancestry/context. Degraded or unavailable captions are intentionally omitted.
    """
    if max_words <= 0:
        return ""
    pieces: list[str] = []
    if obj.label:
        pieces.append(obj.label)
    if obj.caption_text_quality == "usable" and obj.title:
        pieces.append(obj.title)
    if obj.structural_context:
        pieces.append(obj.structural_context)
    words = " ".join(pieces).split()
    return " ".join(words[:max_words])


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower().replace("-", " "))


def bm25_scores(documents: Sequence[str], query: str) -> list[float]:
    """Small dependency-free BM25 scorer used for text-first visual retrieval."""
    docs = [_tokens(d) for d in documents]
    n_docs = len(docs)
    if n_docs == 0:
        return []
    df: Counter[str] = Counter()
    for doc in docs:
        df.update(set(doc))
    avg_len = sum(map(len, docs)) / n_docs if n_docs else 0.0
    k1, b = 1.4, 0.75
    q_tokens = _tokens(query)
    normalized_query = " ".join(q_tokens)
    scores: list[float] = []
    for raw, doc in zip(documents, docs):
        tf = Counter(doc)
        score = 0.0
        for token in q_tokens:
            freq = tf[token]
            if not freq:
                continue
            idf = math.log(1.0 + (n_docs - df[token] + 0.5) / (df[token] + 0.5))
            denom = freq + k1 * (1 - b + b * len(doc) / max(avg_len, 1e-9))
            score += idf * freq * (k1 + 1) / denom
        if normalized_query and normalized_query in " ".join(_tokens(raw)):
            score += 8.0
        scores.append(score)
    return scores



def visual_cache_key(
    *,
    render_sha256: str,
    model_sha256: str,
    include_fine: bool,
    context: str,
) -> str:
    """Return a content address for one object's visual/text embedding work."""
    payload = {
        "render_sha256": render_sha256.lower(),
        "model_sha256": model_sha256.lower(),
        "include_fine": bool(include_fine),
        "context": context,
        "contract": "engineering-visual-memory-cache/0.4.0",
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def verify_private_package(root: Path) -> VerificationReport:
    """Verify source-safety invariants for a generated private index package.

    This intentionally does not verify model or source artifact availability. It verifies
    that the package self-declares no embedded sources and that no obvious source media
    have leaked into the package tree.
    """
    root = Path(root)
    errors: list[str] = []
    forbidden: list[str] = []
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        errors.append("manifest.json is missing")
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"manifest.json is unreadable: {exc}")
        else:
            if manifest.get("source_pdfs_included") is not False:
                errors.append("manifest must declare source_pdfs_included=false")
            if manifest.get("source_images_included") is not False:
                errors.append("manifest must declare source_images_included=false")
            model_sha = manifest.get("clip_model_sha256")
            if not isinstance(model_sha, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", model_sha):
                errors.append("clip_model_sha256 must be a 64-character hex SHA-256")
    if root.exists():
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in _FORBIDDEN_SOURCE_SUFFIXES:
                forbidden.append(path.relative_to(root).as_posix())
    if forbidden:
        errors.append("package contains forbidden source-media file types")
    return VerificationReport(ok=not errors, forbidden_files=sorted(forbidden), errors=errors)


def visual_object_from_mapping(data: dict) -> VisualObject:
    return VisualObject(
        corpus_id=str(data["corpus_id"]),
        kind=str(data["kind"]),
        occurrence_id=str(data["occurrence_id"]),
        logical_visual_id=data.get("logical_visual_id"),
        label=str(data.get("label") or ""),
        title=str(data.get("title") or ""),
        structural_context=str(data.get("structural_context") or data.get("context") or ""),
        page=int(data["page"]),
        source_sha256=str(data["source_sha256"]),
        caption_text_quality=str(data.get("caption_text_quality") or "usable"),
    )
