"""IBC-specific text reconstruction and logical block classification."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
import re
import statistics
from typing import Any, Iterable, Mapping, Sequence

from .models import CHAPTER_SPECS, _DEFINITION_RE, _LIST_RE, _PROVISION_RE
from ..layout_analysis import (
    BodyFontProfile,
    CleanedPage,
    PageLines,
    RuleSegment,
    SourceFragment,
    VisualLine,
    infer_page_order,
    order_page_lines as order_analyzed_page_lines,
)


_MORPHOLOGICAL_PREFIXES = frozenset(
    {
        "com", "con", "de", "dis", "em", "en", "il", "im", "in",
        "inter", "ir", "non", "per", "pre", "pro", "re", "sub",
        "trans", "un",
    }
)


def _source_spacing_repairs(
    pages: Sequence[PageLines],
) -> dict[str, tuple[str, str]]:
    word_counts: Counter[str] = Counter()
    pair_counts: Counter[tuple[str, str]] = Counter()
    for page in pages:
        for line in page.lines:
            for fragment in line.fragments:
                tokens = [
                    token.casefold()
                    for token in re.findall(r"[A-Za-z]+", fragment.raw_text)
                ]
                word_counts.update(tokens)
                pair_counts.update(zip(tokens, tokens[1:]))

    repairs: dict[str, tuple[str, str]] = {}
    for token, token_count in word_counts.items():
        if len(token) < 5:
            continue
        candidates: list[tuple[int, int, str, str]] = []
        for split in range(2, len(token) - 1):
            left, right = token[:split], token[split:]
            pair_count = pair_counts[(left, right)]
            if (
                pair_count >= 2
                and pair_count >= token_count * 2
                and left not in _MORPHOLOGICAL_PREFIXES
            ):
                candidates.append((pair_count, min(len(left), len(right)), left, right))
        if candidates:
            _pair_count, _balance, left, right = max(candidates)
            repairs[token] = (left, right)
    return repairs


def repair_source_spacing(pages: Sequence[PageLines]) -> tuple[PageLines, ...]:
    """Repair repeated missing word boundaries using evidence in the same source slice."""

    repairs = _source_spacing_repairs(pages)
    if not repairs:
        return tuple(pages)

    patterns = [
        (
            re.compile(rf"\b{re.escape(token)}(?P<suffix>s)?\b", re.IGNORECASE),
            left,
            right,
        )
        for token, (left, right) in sorted(repairs.items(), key=lambda item: -len(item[0]))
    ]

    def repair_text(text: str) -> str:
        for pattern, left, right in patterns:
            def replacement(match: re.Match[str]) -> str:
                source = match.group(0)
                suffix = match.group("suffix") or ""
                left_text = source[: len(left)]
                right_text = source[len(left) : len(left) + len(right)]
                return left_text + " " + right_text + suffix
            text = pattern.sub(replacement, text)
        return text

    repaired_pages: list[PageLines] = []
    for page in pages:
        repaired_lines: list[VisualLine] = []
        for line in page.lines:
            fragments = tuple(
                replace(fragment, raw_text=repair_text(fragment.raw_text))
                for fragment in line.fragments
            )
            repaired_lines.append(
                replace(
                    line,
                    text=repair_text(line.text),
                    fragments=fragments,
                    line_id="",
                )
            )
        repaired_pages.append(replace(page, lines=tuple(repaired_lines)))
    return tuple(repaired_pages)


def parse_chapter_numbers(values: Iterable[str]) -> tuple[str, ...]:
    chapters = tuple(str(value).strip() for value in values if str(value).strip())
    if not chapters:
        raise ValueError("at least one chapter number is required")
    if len(set(chapters)) != len(chapters):
        raise ValueError("chapter numbers must not be duplicated")
    unsupported = [number for number in chapters if number not in CHAPTER_SPECS]
    if unsupported:
        supported = ", ".join(CHAPTER_SPECS)
        raise ValueError(
            f"unsupported IBC 2018 chapter(s): {', '.join(unsupported)}; "
            f"this bounded adapter supports {supported}"
        )
    return chapters


def _normalize_visual_text(text: str) -> str:
    normalized = (
        text.replace("\u00ad", "")
        .replace("¬", "")
        .replace("\uf0a3", "≤")
        .replace("\r", " ")
        .replace("\n", " ")
    )
    normalized = re.sub(r"\s+([.,;:!?)}\]])", r"\1", normalized)
    normalized = re.sub(r"([({\[])\s+", r"\1", normalized)
    normalized = re.sub(r"([’'])\s+([sS])\b", r"\1\2", normalized)
    normalized = re.sub(r"([A-Za-z])\s+([’'])", r"\1\2", normalized)
    normalized = re.sub(r"\s+°", "°", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _characters_gap_requires_space(
    left: str,
    right: str,
    *,
    gap: float,
    body_threshold: float,
    digit_threshold: float,
) -> bool:
    if gap <= 0.0:
        return False
    if left.isdigit() and right.isdigit():
        return gap > digit_threshold
    if left.isdigit() and right == "-":
        return gap > digit_threshold
    if right in ".,;:!?)}]°" or left in "({[":
        return gap > digit_threshold
    if left in "’'" and right.isalpha():
        return gap > digit_threshold
    if left.isalpha() and right in "’'":
        return gap > digit_threshold
    if left.casefold() == "j" and right.islower():
        return gap > digit_threshold
    if left == "B" and right == "u":
        return gap > digit_threshold
    return gap > body_threshold


def reconstruct_glyph_line(chars: Sequence[Mapping[str, Any]]) -> str:
    retained = [char for char in chars if str(char.get("c", "")).strip()]
    if not retained:
        return ""
    retained.sort(key=lambda char: float(char["bbox"][0]))
    heights = [float(char["bbox"][3]) - float(char["bbox"][1]) for char in retained]
    median_height = statistics.median(heights)
    body_threshold = max(0.75, median_height * 0.10)
    digit_threshold = max(2.0, median_height * 0.22)
    output = [str(retained[0]["c"])]
    previous = retained[0]
    for char in retained[1:]:
        gap = float(char["bbox"][0]) - float(previous["bbox"][2])
        if _characters_gap_requires_space(
            str(previous.get("c", "")),
            str(char.get("c", "")),
            gap=gap,
            body_threshold=body_threshold,
            digit_threshold=digit_threshold,
        ):
            output.append(" ")
        output.append(str(char["c"]))
        previous = char
    return _normalize_visual_text("".join(output))


def _block_text_font(block: Mapping[str, Any]) -> tuple[str, float, str | None]:
    chars: list[Mapping[str, Any]] = []
    weighted_sizes: list[float] = []
    font_names: Counter[str] = Counter()
    for line in block.get("lines", ()):
        for span in line.get("spans", ()):
            span_chars = list(span.get("chars", ()))
            chars.extend(span_chars)
            size = float(span.get("size", 0.0) or 0.0)
            if size < 1.0 and span_chars:
                heights = [
                    float(char["bbox"][3]) - float(char["bbox"][1])
                    for char in span_chars
                    if "bbox" in char
                ]
                if heights:
                    size = float(statistics.median(heights))
            if size > 0.0:
                weighted_sizes.extend([size] * max(1, len(span_chars)))
            font = str(span.get("font", "")).strip()
            if font:
                font_names[font] += max(1, len(span_chars))
    text = reconstruct_glyph_line(chars)
    font_size = float(statistics.median(weighted_sizes)) if weighted_sizes else 0.0
    font_name = font_names.most_common(1)[0][0] if font_names else None
    return text, font_size, font_name


def _same_baseline(left: VisualLine, right: VisualLine) -> bool:
    overlap = min(left.bbox[3], right.bbox[3]) - max(left.bbox[1], right.bbox[1])
    minimum_height = min(
        max(0.1, left.bbox[3] - left.bbox[1]),
        max(0.1, right.bbox[3] - right.bbox[1]),
    )
    return overlap >= minimum_height * 0.60


def _line_height(line: VisualLine) -> float:
    return max(0.1, line.bbox[3] - line.bbox[1])


def _merge_row_parts(parts: Sequence[VisualLine]) -> tuple[VisualLine, ...]:
    ordered = sorted(parts, key=lambda item: (item.bbox[0], item.line_id))
    normal_height = max(_line_height(item) for item in ordered)
    output: list[VisualLine] = []
    for index, line in enumerate(ordered):
        if output:
            previous = output[-1]
            gap = line.bbox[0] - previous.bbox[2]
            overlap_limit = max(
                1.5,
                min(
                    previous.font_size or _line_height(previous),
                    line.font_size or _line_height(line),
                )
                * 0.20,
            )
            if -overlap_limit <= gap < 8.0:
                next_part = ordered[index + 1] if index + 1 < len(ordered) else None
                is_small_script = _line_height(line) <= normal_height * 0.72
                fraction_numerator = bool(
                    is_small_script
                    and previous.text[-1:].isdigit()
                    and line.text.isdigit()
                    and next_part is not None
                    and next_part.text.startswith("/")
                )
                separator = " " if fraction_numerator else ""
                if not separator and previous.text and line.text:
                    body_threshold = max(0.75, normal_height * 0.10)
                    digit_threshold = max(2.0, normal_height * 0.22)
                    if _characters_gap_requires_space(
                        previous.text[-1],
                        line.text[0],
                        gap=gap,
                        body_threshold=body_threshold,
                        digit_threshold=digit_threshold,
                    ):
                        separator = " "
                fragments = previous.fragments + line.fragments
                output[-1] = VisualLine(
                    page_number=line.page_number,
                    bbox=(
                        min(previous.bbox[0], line.bbox[0]),
                        min(previous.bbox[1], line.bbox[1]),
                        max(previous.bbox[2], line.bbox[2]),
                        max(previous.bbox[3], line.bbox[3]),
                    ),
                    text=_normalize_visual_text(previous.text + separator + line.text),
                    fragments=fragments,
                    font_size=max(previous.font_size, line.font_size),
                    font_name=previous.font_name or line.font_name,
                )
                continue
        output.append(line)
    return tuple(output)


def merge_visual_fragments(
    lines: Iterable[VisualLine],
    *,
    page_width: float,
) -> tuple[VisualLine, ...]:
    """Merge adjacent positioned fragments into visual rows.

    Small superscript and subscript blocks are connected through the normal
    baseline block they overlap, while distant page columns remain separate.
    """

    del page_width
    material = sorted(
        lines,
        key=lambda line: (
            line.page_number,
            (line.bbox[1] + line.bbox[3]) / 2.0,
            line.bbox[0],
            line.line_id,
        ),
    )
    baseline_groups: list[list[VisualLine]] = []
    for line in material:
        group = next(
            (
                candidate
                for candidate in reversed(baseline_groups)
                if candidate[0].page_number == line.page_number
                and any(_same_baseline(member, line) for member in candidate)
            ),
            None,
        )
        if group is None:
            baseline_groups.append([line])
        else:
            group.append(line)

    merged = [part for group in baseline_groups for part in _merge_row_parts(group)]
    return tuple(
        sorted(merged, key=lambda line: (line.bbox[1], line.bbox[0], line.line_id))
    )


def order_page_lines(
    lines: Iterable[VisualLine],
    *,
    page_width: float,
) -> tuple[VisualLine, ...]:
    """Compatibility wrapper around adaptive page-local ordering."""

    material = tuple(lines)
    if not material:
        return ()
    page_number = material[0].page_number
    height = max(line.bbox[3] for line in material) + 1.0
    page = CleanedPage(page_number, page_width, height, material, ())
    return order_analyzed_page_lines(page, infer_page_order(page))


def _extract_page_rules(page: Any, page_number: int) -> tuple[RuleSegment, ...]:
    rules: dict[tuple[float, float, float, float], RuleSegment] = {}

    def add(x0: float, y0: float, x1: float, y1: float) -> None:
        if abs(y1 - y0) <= 1.0 and abs(x1 - x0) >= 10.0:
            y = (y0 + y1) / 2.0
            x0, x1 = sorted((x0, x1))
            key = (round(x0, 2), round(y, 2), round(x1, 2), round(y, 2))
        elif abs(x1 - x0) <= 1.0 and abs(y1 - y0) >= 10.0:
            x = (x0 + x1) / 2.0
            y0, y1 = sorted((y0, y1))
            key = (round(x, 2), round(y0, 2), round(x, 2), round(y1, 2))
        else:
            return
        rules[key] = RuleSegment(page_number, *key)

    for drawing in page.get_drawings():
        for item in drawing.get("items", ()):
            kind = item[0]
            if kind == "l":
                start, end = item[1], item[2]
                add(float(start.x), float(start.y), float(end.x), float(end.y))
            elif kind == "re":
                rectangle = item[1]
                width = float(rectangle.x1 - rectangle.x0)
                height = float(rectangle.y1 - rectangle.y0)
                if width >= 10.0 and height <= 2.0:
                    add(
                        float(rectangle.x0),
                        float((rectangle.y0 + rectangle.y1) / 2.0),
                        float(rectangle.x1),
                        float((rectangle.y0 + rectangle.y1) / 2.0),
                    )
                elif height >= 10.0 and width <= 2.0:
                    add(
                        float((rectangle.x0 + rectangle.x1) / 2.0),
                        float(rectangle.y0),
                        float((rectangle.x0 + rectangle.x1) / 2.0),
                        float(rectangle.y1),
                    )
    return tuple(sorted(rules.values(), key=lambda rule: (rule.y0, rule.x0, rule.y1, rule.x1)))


def _extract_page_lines(page: Any, page_number: int) -> PageLines:
    raw = page.get_text("rawdict")
    candidates: list[VisualLine] = []
    for block in raw.get("blocks", ()):
        if int(block.get("type", 0)) != 0:
            continue
        bbox = tuple(float(value) for value in block["bbox"])
        text, font_size, font_name = _block_text_font(block)
        if not text:
            continue
        fragment = SourceFragment(
            page_number=page_number,
            bbox=bbox,
            block_number=int(block.get("number", len(candidates))),
            raw_text=text,
            font_size=font_size,
            font_name=font_name,
        )
        candidates.append(
            VisualLine(
                page_number=page_number,
                bbox=bbox,
                text=text,
                fragments=(fragment,),
                font_size=font_size,
                font_name=font_name,
            )
        )
    merged = merge_visual_fragments(candidates, page_width=float(page.rect.width))
    return PageLines(
        page_number=page_number,
        width=float(page.rect.width),
        height=float(page.rect.height),
        lines=merged,
        rules=(
            _extract_page_rules(page, page_number)
            if any(re.search(r"(?:^|\s)TABLE\s+\d", line.text) for line in merged)
            else ()
        ),
    )


def _is_heading(text: str) -> bool:
    if text.startswith(("CHAPTER ", "PART ", "SECTION ")):
        return True
    letters = [char for char in text if char.isalpha()]
    return bool(letters) and len(text) <= 120 and all(char.isupper() for char in letters)


def _line_is_heading(line: VisualLine, body_font: BodyFontProfile | None) -> bool:
    if _is_heading(line.text):
        return True
    threshold = body_font.heading_threshold if body_font else None
    return bool(
        threshold
        and line.font_size >= threshold
        and len(line.text) <= 120
        and not line.text.endswith((".", "!", "?"))
    )


def _is_definition_start(text: str, chapter_number: str) -> bool:
    return chapter_number == "2" and _DEFINITION_RE.match(text) is not None


def _starts_new_block(
    line: VisualLine,
    chapter_number: str,
    body_font: BodyFontProfile | None,
) -> bool:
    text = line.text
    return (
        _line_is_heading(line, body_font)
        or text.startswith(("Exception:", "Exceptions:", "Informational Note", "Note:"))
        or _PROVISION_RE.match(text) is not None
        or _LIST_RE.match(text) is not None
        or _is_definition_start(text, chapter_number)
        or text.startswith(("TABLE ", "FIGURE "))
    )


_WORD_TOKEN_RE = re.compile(r"[A-Za-z]+(?:-[A-Za-z]+)*-?")
_PRESERVED_COMPOUND_PAIRS = frozenset(
    {
        ("double", "pivoted"),
        ("field", "assembled"),
        ("free", "burning"),
        ("hydrogen", "containing"),
        ("pressure", "regulating"),
        ("water", "resistant"),
    }
)


@dataclass(frozen=True, slots=True)
class HyphenationLexicon:
    joined_words: frozenset[str]
    hyphen_pairs: frozenset[tuple[str, str]]
    space_pairs: frozenset[tuple[str, str]]


def build_hyphenation_lexicon(lines: Sequence[VisualLine]) -> HyphenationLexicon:
    joined_words: set[str] = set()
    hyphen_pairs: set[tuple[str, str]] = set()
    space_pairs: set[tuple[str, str]] = set()
    for line in lines:
        tokens = [token.casefold() for token in _WORD_TOKEN_RE.findall(line.text)]
        complete = [token for token in tokens if not token.endswith("-")]
        for token in complete:
            if "-" not in token:
                joined_words.add(token)
            components = token.split("-")
            hyphen_pairs.update(zip(components, components[1:]))
        for left, right in zip(complete, complete[1:]):
            if "-" not in left and "-" not in right:
                space_pairs.add((left, right))
    return HyphenationLexicon(
        frozenset(joined_words),
        frozenset(hyphen_pairs),
        frozenset(space_pairs),
    )


def _join_text(
    previous: str,
    current: str,
    lexicon: HyphenationLexicon | None = None,
) -> str:
    if not (previous.endswith(("-", "‐")) and current[:1].isalpha()):
        return previous + " " + current

    trailing = re.search(r"([A-Za-z-]+)[-‐]$", previous)
    leading = re.match(r"([A-Za-z-]+)", current)
    if trailing is None or leading is None:
        return previous[:-1] + current

    trailing_token = trailing.group(1).casefold()
    leading_token = leading.group(1).casefold()
    left = trailing_token.rsplit("-", 1)[-1]
    right = leading_token.split("-", 1)[0]
    pair = (left, right)
    joined = left + right
    vocabulary = lexicon or HyphenationLexicon(frozenset(), frozenset(), frozenset())

    if joined in vocabulary.joined_words:
        return previous[:-1] + current
    if pair in vocabulary.hyphen_pairs or pair in _PRESERVED_COMPOUND_PAIRS:
        return previous + current
    if "-" in trailing_token or "-" in leading_token:
        return previous + current
    if pair in vocabulary.space_pairs:
        return previous[:-1] + " " + current
    return previous[:-1] + current


def _opening_commentary_indexes(lines: Sequence[VisualLine]) -> set[int]:
    if not lines:
        return set()
    chapter_index = next(
        (index for index, line in enumerate(lines) if line.text.startswith("CHAPTER ")),
        0,
    )
    body_index = next(
        (
            index
            for index, line in enumerate(lines[chapter_index + 1 :], start=chapter_index + 1)
            if line.text.startswith(("PART ", "SECTION "))
        ),
        len(lines),
    )
    commentary_index = next(
        (
            index
            for index, line in enumerate(lines[chapter_index:body_index], start=chapter_index)
            if line.text.startswith(("User note", "User notes"))
        ),
        body_index,
    )
    return set(range(commentary_index, body_index))


def _trim_opening_commentary(lines: Sequence[VisualLine]) -> tuple[VisualLine, ...]:
    if not lines:
        return ()
    chapter_index = next(
        (index for index, line in enumerate(lines) if line.text.startswith("CHAPTER ")),
        0,
    )
    removed = _opening_commentary_indexes(lines)
    return tuple(line for index, line in enumerate(lines) if index >= chapter_index and index not in removed)


def _block_evidence(
    lines: Sequence[VisualLine],
    body_font: BodyFontProfile | None,
    chapter_number: str,
) -> tuple[float, tuple[str, ...]]:
    first = lines[0]
    evidence: list[str] = []
    confidence = 0.75
    if first.text.startswith("CHAPTER "):
        evidence.append("chapter_anchor")
        confidence = 0.98
    elif first.text.startswith("PART "):
        evidence.append("part_anchor")
        confidence = 0.95
    elif first.text.startswith("SECTION "):
        evidence.append("section_anchor")
        confidence = 0.95
    elif _PROVISION_RE.match(first.text):
        evidence.append("numbered_provision")
        confidence = 0.94
    elif _is_definition_start(first.text, chapter_number):
        evidence.append("definition_pattern")
        confidence = 0.92
    elif _line_is_heading(first, body_font):
        if body_font and body_font.heading_threshold and first.font_size >= body_font.heading_threshold:
            evidence.append("font_heading")
        if _is_heading(first.text):
            evidence.append("all_caps_heading")
        confidence = 0.85
    else:
        evidence.append("paragraph_assembly")
    evidence.append(f"lines:{len(lines)}")
    return confidence, tuple(evidence)
