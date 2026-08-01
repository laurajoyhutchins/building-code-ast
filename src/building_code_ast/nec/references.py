"""Exact code-reference extraction shared by NEC semantic projections."""

from __future__ import annotations

import re
from typing import Iterable

from ..model import SourceSpan
from .model import CodeReference, CodeReferenceKind


_TABLE_RE = re.compile(
    r"\bTable\s+(?P<target>\d{2,3}\.\d+(?:\([A-Za-z0-9]+\))*)",
    re.IGNORECASE,
)
_ARTICLE_RE = re.compile(r"\bArticle\s+(?P<target>\d{2,3})\b", re.IGNORECASE)
_SECTION_RE = re.compile(
    r"(?<![A-Za-z0-9])(?P<target>\d{2,3}\.\d+(?:\([A-Za-z0-9]+\))*)(?![A-Za-z0-9])"
)


def _span(source: str, start: int, end: int) -> SourceSpan:
    return SourceSpan(start, end, source[start:end])


def extract_code_references(
    source: str,
    spans: Iterable[SourceSpan],
) -> tuple[CodeReference, ...]:
    found: list[CodeReference] = []
    occupied: set[tuple[int, int]] = set()
    for span in spans:
        for pattern, kind in (
            (_TABLE_RE, CodeReferenceKind.TABLE),
            (_ARTICLE_RE, CodeReferenceKind.ARTICLE),
        ):
            for match in pattern.finditer(span.text):
                start = span.start + match.start("target")
                end = span.start + match.end("target")
                occupied.add((start, end))
                found.append(CodeReference(kind, match.group("target"), _span(source, start, end)))
        for match in _SECTION_RE.finditer(span.text):
            start = span.start + match.start("target")
            end = span.start + match.end("target")
            if (start, end) in occupied:
                continue
            prefix = source[max(span.start, start - 7) : start].casefold()
            if prefix.endswith("table "):
                continue
            found.append(
                CodeReference(
                    CodeReferenceKind.SECTION,
                    match.group("target"),
                    _span(source, start, end),
                )
            )
    found.sort(key=lambda item: (item.span.start, item.span.end, item.kind.value))
    return tuple(found)
