# PDF Layout Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add publication-neutral PDF layout analysis, geometry-backed table reconstruction, and exact line-consumption validation to the bounded IBC 2018 ingestion pipeline.

**Architecture:** Extract generic positioned-page records and layout algorithms from `ibc2018.py` into three focused modules. Analyze recurring margins, font evidence, and page-local reading order before IBC-specific classification; identify table rows and cells from geometry; then validate that every retained line and source fragment is represented exactly once. Keep the public Document AST unchanged and serialize richer evidence only in private ChapterSeed output.

**Tech Stack:** Python 3.12, standard-library dataclasses/statistics/hashlib/regular expressions, optional PyMuPDF 1.x through the existing `ibc-pdf` extra, unittest, existing Document AST and provenance validators.

## Global Constraints

- The base runtime dependency set remains empty.
- PyMuPDF remains isolated behind `ibc-pdf = ["PyMuPDF>=1.24,<2"]`.
- Public Git contains no IBC source text, page images, or generated ChapterSeed output.
- The production slice remains bounded to Chapters `1`, `2`, and `3`.
- The public Document AST contract and `DOCUMENT_AST_VERSION = "0.1.0"` remain unchanged.
- Private ChapterSeed serialization advances from `0.1.0` to `0.2.0` because it gains layout-analysis and table-evidence fields.
- Generic modules contain no IBC chapter numbers, physical page ranges, committee designations, or publication-specific regular expressions.
- Every normalized span must round-trip exactly.
- Every retained visual line must be consumed exactly once.
- Removed lines must carry an explicit removal reason.
- Weak layout evidence falls back conservatively and never causes silent text loss.
- All public tests use synthetic project-authored text and geometry.

---

## File Map

- Create `src/building_code_ast/ingest/layout_analysis.py`: positioned page records, recurring margins, font profile, adaptive reading-order profiles, stable evidence.
- Create `src/building_code_ast/ingest/table_geometry.py`: row and cell candidates, table grouping, deterministic table text and local spans.
- Create `src/building_code_ast/ingest/layout_validation.py`: line coverage, page ownership, nested fragment, and table-span validation.
- Modify `src/building_code_ast/ingest/ibc2018.py`: use generic analysis, preserve IBC rules, build nested table AST nodes, serialize private evidence.
- Modify `src/building_code_ast/ingest/__init__.py`: export the narrow generic API and retain compatibility exports.
- Modify `scripts/ingest_ibc_2018.py`: record layout-analysis version in the private manifest.
- Create `tests/test_layout_analysis.py`.
- Create `tests/test_table_geometry.py`.
- Create `tests/test_layout_validation.py`.
- Modify `tests/test_ibc2018_ingest.py`.
- Modify `docs/how-to/ingest-ibc-2018.md` and `README.md`.

---

### Task 1: Generic positioned-page records and recurring-margin analysis

**Files:**
- Create: `src/building_code_ast/ingest/layout_analysis.py`
- Modify: `src/building_code_ast/ingest/ibc2018.py`
- Modify: `src/building_code_ast/ingest/__init__.py`
- Create: `tests/test_layout_analysis.py`
- Modify: `tests/test_ibc2018_ingest.py`

**Interfaces:**

- Produces:

```python
@dataclass(frozen=True, slots=True)
class SourceFragment:
    page_number: int
    bbox: tuple[float, float, float, float]
    block_number: int
    raw_text: str
    font_size: float = 0.0
    font_name: str | None = None

@dataclass(frozen=True, slots=True)
class VisualLine:
    line_id: str
    page_number: int
    bbox: tuple[float, float, float, float]
    text: str
    fragments: tuple[SourceFragment, ...]
    font_size: float = 0.0
    font_name: str | None = None

@dataclass(frozen=True, slots=True)
class PageLines:
    page_number: int
    width: float
    height: float
    lines: tuple[VisualLine, ...]

@dataclass(frozen=True, slots=True)
class RecurringMargins:
    header_keys: frozenset[str]
    footer_keys: frozenset[str]
    minimum_occurrences: int

@dataclass(frozen=True, slots=True)
class RemovedLine:
    line: VisualLine
    reason: str

@dataclass(frozen=True, slots=True)
class CleanedPage:
    page_number: int
    width: float
    height: float
    retained: tuple[VisualLine, ...]
    removed: tuple[RemovedLine, ...]

@dataclass(frozen=True, slots=True)
class BodyFontProfile:
    body_font_size: float | None
    heading_threshold: float | None
    confidence: float
    evidence: tuple[str, ...]
```

- Produces:

```python
def visual_line_id(
    page_number: int,
    fragments: Sequence[SourceFragment],
) -> str: ...

def structural_margin_key(text: str) -> str: ...

def detect_recurring_margins(
    pages: Sequence[PageLines],
    *,
    top_fraction: float = 0.10,
    bottom_fraction: float = 0.10,
    minimum_fraction: float = 0.40,
    minimum_pages: int = 2,
) -> RecurringMargins: ...

def clean_recurring_margins(
    pages: Sequence[PageLines],
    margins: RecurringMargins,
    *,
    top_fraction: float = 0.10,
    bottom_fraction: float = 0.10,
) -> tuple[CleanedPage, ...]: ...

def estimate_body_font(
    pages: Sequence[CleanedPage],
) -> BodyFontProfile: ...
```

- `ibc2018.py` imports `SourceFragment` and `VisualLine` from the generic module so existing callers retain the same names.

- [ ] **Step 1: Write failing tests for structural keys and position-gated removal**

```python
from building_code_ast.ingest.layout_analysis import (
    PageLines,
    SourceFragment,
    VisualLine,
    clean_recurring_margins,
    detect_recurring_margins,
    structural_margin_key,
    visual_line_id,
)


def line(page: int, y: float, text: str, *, height: float = 10.0) -> VisualLine:
    fragment = SourceFragment(page, (10.0, y, 190.0, y + height), int(y), text, 10.0, "Body")
    return VisualLine(
        line_id=visual_line_id(page, (fragment,)),
        page_number=page,
        bbox=fragment.bbox,
        text=text,
        fragments=(fragment,),
        font_size=10.0,
        font_name="Body",
    )


def test_structural_key_normalizes_page_numbers() -> None:
    assert structural_margin_key("2018 IBC 31") == structural_margin_key("2018 IBC 32")


def test_recurring_header_is_removed_only_in_top_band() -> None:
    pages = tuple(
        PageLines(
            page_number=page,
            width=200.0,
            height=300.0,
            lines=(
                line(page, 285.0, f"2018 IBC {page}"),
                line(page, 150.0, f"2018 IBC {page}"),
                line(page, 120.0, f"Body paragraph {page}."),
            ),
        )
        for page in (1, 2, 3)
    )
    margins = detect_recurring_margins(pages)
    cleaned = clean_recurring_margins(pages, margins)

    assert [item.line.text for item in cleaned[0].removed] == ["2018 IBC 1"]
    assert "2018 IBC 1" in [item.text for item in cleaned[0].retained]
```

- [ ] **Step 2: Run the focused tests and confirm missing-module failure**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_layout_analysis -v
```

Expected: FAIL because `layout_analysis.py` and its records do not exist.

- [ ] **Step 3: Implement immutable records, deterministic line identity, and structural keys**

Use canonical JSON and SHA-256 for `visual_line_id`. Identity input must include page number plus each fragment's rounded bounding box, block number, and raw text. The resulting ID format is `pdfline:<64 lowercase hex characters>`.

`structural_margin_key` must case-fold, replace each numeric run with `#`, collapse non-alphanumeric separators to one space, and trim.

- [ ] **Step 4: Implement recurring-margin detection and cleanup**

Only lines inside the configured top or bottom bands contribute candidate keys. The recurrence threshold is:

```python
minimum_occurrences = max(minimum_pages, math.ceil(len(pages) * minimum_fraction))
```

A line is removed only when both its position and key match the corresponding recurring set. Record `recurring_header` or `recurring_footer` as the reason.

- [ ] **Step 5: Add and implement the weighted body-font test**

```python
def test_body_font_estimate_resists_short_oversized_headings() -> None:
    pages = (
        CleanedPage(
            page_number=1,
            width=200.0,
            height=300.0,
            retained=(
                line_with_font(1, 250.0, "LARGE TITLE", 22.0),
                line_with_font(1, 200.0, "This is a long synthetic body paragraph used for weighting.", 10.0),
                line_with_font(1, 180.0, "Another long synthetic body paragraph used for weighting.", 10.0),
            ),
            removed=(),
        ),
    )

    profile = estimate_body_font(pages)

    assert profile.body_font_size == 10.0
    assert profile.heading_threshold == 11.5
    assert "body_font:10.0" in profile.evidence
```

Weight each positive font-size sample by `min(len(line.text), 200)`. Ignore lines shorter than 20 characters. Use a median of the weighted samples. Set the threshold to `body_font_size * 1.15`. Return a conservative `None` profile when no usable sample exists.

- [ ] **Step 6: Move the IBC positioned records onto the generic types**

Update `_extract_page_lines`, `merge_visual_fragments`, and synthetic tests to populate font metadata and deterministic `line_id`. Preserve current glyph reconstruction and same-baseline merging behavior.

- [ ] **Step 7: Run focused and regression tests**

```bash
PYTHONPATH=src python -m unittest tests.test_layout_analysis tests.test_ibc2018_ingest -v
PYTHONPATH=src python -m compileall -q src tests
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/building_code_ast/ingest/layout_analysis.py \
  src/building_code_ast/ingest/ibc2018.py \
  src/building_code_ast/ingest/__init__.py \
  tests/test_layout_analysis.py tests/test_ibc2018_ingest.py
git commit -m "feat: add generic PDF page analysis records"
```

---

### Task 2: Adaptive page-local reading order

**Files:**
- Modify: `src/building_code_ast/ingest/layout_analysis.py`
- Modify: `src/building_code_ast/ingest/ibc2018.py`
- Modify: `tests/test_layout_analysis.py`
- Modify: `tests/test_ibc2018_ingest.py`

**Interfaces:**

```python
class ReadingOrderMode(StrEnum):
    TOP_TO_BOTTOM = "top_to_bottom"
    TWO_COLUMN = "two_column"

@dataclass(frozen=True, slots=True)
class PageOrderProfile:
    page_number: int
    mode: ReadingOrderMode
    split_x: float | None
    confidence: float
    evidence: tuple[str, ...]


def infer_page_order(page: CleanedPage) -> PageOrderProfile: ...


def order_page_lines(
    page: CleanedPage,
    profile: PageOrderProfile,
) -> tuple[VisualLine, ...]: ...
```

- [ ] **Step 1: Write failing asymmetric-column and false-split tests**

```python
def test_infers_asymmetric_two_column_split() -> None:
    page = cleaned_page(
        width=600.0,
        lines=(
            geom_line(1, 50.0, 240.0, "left top"),
            geom_line(1, 50.0, 200.0, "left bottom"),
            geom_line(1, 360.0, 240.0, "right top"),
            geom_line(1, 360.0, 200.0, "right bottom"),
        ),
    )

    profile = infer_page_order(page)
    ordered = order_page_lines(page, profile)

    assert profile.mode is ReadingOrderMode.TWO_COLUMN
    assert 240.0 < profile.split_x < 360.0
    assert [item.text for item in ordered] == [
        "left top",
        "left bottom",
        "right top",
        "right bottom",
    ]


def test_rejects_false_split_without_vertical_overlap() -> None:
    page = cleaned_page(
        width=600.0,
        lines=(
            geom_line(1, 50.0, 260.0, "top left"),
            geom_line(1, 360.0, 80.0, "bottom right"),
        ),
    )

    assert infer_page_order(page).mode is ReadingOrderMode.TOP_TO_BOTTOM
```

- [ ] **Step 2: Run the focused tests and confirm missing API failure**

```bash
PYTHONPATH=src python -m unittest tests.test_layout_analysis -v
```

- [ ] **Step 3: Implement page-profile inference**

Use only lines with positive width and nonempty text. Treat a line as full-width opening matter when it spans at least 65 percent of the page width or crosses the page center by at least 10 percent of page width. Exclude full-width lines from the column sample, but preserve them for output.

Build candidate split positions from sorted line-start positions. A split is accepted only when:

- at least two sampled lines fall on each side;
- the left and right vertical ranges overlap by at least one median line height;
- the horizontal separation between the right edge of the left cluster and left edge of the right cluster is at least `max(24.0, page.width * 0.04)`;
- the gap is materially larger than the median positive gap between neighboring starts within either cluster.

Select the candidate with the largest normalized separation score. Bound confidence to `0.0..1.0`. Emit stable evidence such as `two_column`, `left_lines:4`, `right_lines:5`, and `split_x:312.0`.

- [ ] **Step 4: Implement conservative ordering**

For `TOP_TO_BOTTOM`, sort by `(bbox.y0, bbox.x0, line_id)` using the existing PDF top-origin coordinate convention.

For `TWO_COLUMN`:

1. emit full-width opening lines above the earliest column body line in top-to-bottom order;
2. emit left-column body lines top-to-bottom;
3. emit right-column body lines top-to-bottom;
4. emit remaining full-width or ambiguous lines top-to-bottom after the body.

Do not mutate lines or create new identities during ordering.

- [ ] **Step 5: Replace the IBC midpoint-only ordering call**

`ibc2018.py` must create `PageLines`, clean margins, infer one profile per page, and pass the ordered lines into existing commentary trimming and logical-block coalescing. Chapter-specific rules remain outside the generic functions.

- [ ] **Step 6: Run focused and full source-free tests**

```bash
PYTHONPATH=src python -m unittest tests.test_layout_analysis tests.test_ibc2018_ingest -v
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m compileall -q src scripts tests
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/building_code_ast/ingest/layout_analysis.py \
  src/building_code_ast/ingest/ibc2018.py \
  tests/test_layout_analysis.py tests/test_ibc2018_ingest.py
git commit -m "feat: infer adaptive PDF reading order"
```

---

### Task 3: Geometry-backed table rows and cells

**Files:**
- Create: `src/building_code_ast/ingest/table_geometry.py`
- Modify: `src/building_code_ast/ingest/__init__.py`
- Create: `tests/test_table_geometry.py`

**Interfaces:**

```python
@dataclass(frozen=True, slots=True)
class TableCellCandidate:
    text: str
    fragments: tuple[SourceFragment, ...]
    local_start: int
    local_end: int

@dataclass(frozen=True, slots=True)
class TableRowCandidate:
    page_number: int
    source_line_ids: tuple[str, ...]
    cells: tuple[TableCellCandidate, ...]
    bbox: tuple[float, float, float, float]
    confidence: float
    evidence: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class TableCandidate:
    page_number: int
    rows: tuple[TableRowCandidate, ...]
    normalized_text: str
    confidence: float
    evidence: tuple[str, ...]


def detect_table_rows(
    page: CleanedPage,
    profile: PageOrderProfile,
) -> tuple[TableRowCandidate, ...]: ...


def group_table_candidates(
    rows: Sequence[TableRowCandidate],
) -> tuple[TableCandidate, ...]: ...
```

- [ ] **Step 1: Write failing cell-spacing and column-gap tests**

```python
def test_detects_two_geometry_cells_and_preserves_fragments() -> None:
    page = page_with_fragments(
        fragments=(
            fragment(1, 50.0, 100.0, 85.0, "Group"),
            fragment(1, 90.0, 100.0, 120.0, "A"),
            fragment(1, 210.0, 100.0, 250.0, "Limit"),
        )
    )

    rows = detect_table_rows(page, top_to_bottom_profile(1))

    assert [cell.text for cell in rows[0].cells] == ["Group A", "Limit"]
    assert sum(len(cell.fragments) for cell in rows[0].cells) == 3


def test_does_not_treat_page_columns_as_table_cells() -> None:
    page = page_with_fragments(
        width=600.0,
        fragments=(
            fragment(1, 50.0, 100.0, 120.0, "Left paragraph"),
            fragment(1, 360.0, 100.0, 450.0, "Right paragraph"),
        ),
    )

    rows = detect_table_rows(page, two_column_profile(1, split_x=300.0))

    assert rows == ()
```

- [ ] **Step 2: Run focused tests and confirm missing-module failure**

```bash
PYTHONPATH=src python -m unittest tests.test_table_geometry -v
```

- [ ] **Step 3: Implement baseline grouping and cell-gap estimation**

Group fragments into rows when their vertical centers differ by no more than `max(2.5, median_font_size * 0.25)`. Sort fragments within a row by x coordinate.

Calculate each fragment's estimated end as:

```python
x1 = max(fragment.bbox[2], fragment.bbox[0] + len(fragment.raw_text) * max(fragment.font_size, 8.0) * 0.45)
```

Use `max(18.0, row_font_size * 1.8)` as the initial cell-gap threshold. Preserve ordinary word spacing inside a cell when the gap exceeds `max(1.5, font_size * 0.12)`.

Reject rows with fewer than two cells. When the page profile is two-column, reject any candidate whose largest separator straddles the inferred page split or exceeds 18 percent of page width.

- [ ] **Step 4: Write and implement compatible-row grouping tests**

```python
def test_two_compatible_rows_form_one_table() -> None:
    rows = (
        synthetic_row(1, y=100.0, cells=("Class", "Value"), starts=(50.0, 200.0)),
        synthetic_row(1, y=120.0, cells=("A", "10"), starts=(50.0, 200.0)),
    )

    tables = group_table_candidates(rows)

    assert len(tables) == 1
    assert tables[0].normalized_text == "Class\tValue\nA\t10"


def test_one_row_does_not_form_a_table() -> None:
    assert group_table_candidates((synthetic_row(...),)) == ()
```

Rows are compatible when they are on the same page, vertically consecutive within three median line heights, have at least two cells, and their cell-start x coordinates align within `max(12.0, median_font_size * 1.5)` for at least two columns.

A table requires at least two compatible rows. Normalize each row with tab-separated cells and join rows with newline. Pad missing trailing cells with empty strings to the maximum column count. Calculate exact cell-local spans while constructing the string.

- [ ] **Step 5: Validate deterministic confidence and evidence**

Confidence is a review score, not a probability. Use stable inputs only: row count, alignment count, geometry-backed cell count, and whether a page-column split was avoided. Ensure repeated runs serialize identically.

- [ ] **Step 6: Run tests and compilation**

```bash
PYTHONPATH=src python -m unittest tests.test_table_geometry -v
PYTHONPATH=src python -m compileall -q src tests
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/building_code_ast/ingest/table_geometry.py \
  src/building_code_ast/ingest/__init__.py \
  tests/test_table_geometry.py
git commit -m "feat: reconstruct PDF table geometry"
```

---

### Task 4: Integrate analysis evidence and nested table AST projection

**Files:**
- Modify: `src/building_code_ast/ingest/ibc2018.py`
- Modify: `scripts/ingest_ibc_2018.py`
- Modify: `tests/test_ibc2018_ingest.py`
- Modify: `tests/test_package_metadata.py`

**Interfaces:**

Extend private IBC records:

```python
SEED_VERSION = "0.2.0"
LAYOUT_ANALYSIS_VERSION = "0.1.0"

@dataclass(frozen=True, slots=True)
class LogicalBlock:
    text: str
    fragments: tuple[SourceFragment, ...]
    source_line_ids: tuple[str, ...]
    confidence: float
    evidence: tuple[str, ...]
    table: TableCandidate | None = None

@dataclass(frozen=True, slots=True)
class ChapterLayoutAnalysis:
    version: str
    body_font: BodyFontProfile
    margins: RecurringMargins
    page_profiles: tuple[PageOrderProfile, ...]
    removed_lines: tuple[RemovedLine, ...]
```

`ChapterSeed.to_dict()` gains a deterministic top-level `layout_analysis` object. Source-map entries gain `source_line_ids`, `confidence`, and `evidence`. Text-bearing generated output remains private.

- [ ] **Step 1: Write failing serialization tests**

```python
def test_chapter_seed_serializes_private_layout_evidence() -> None:
    seed = build_synthetic_chapter_seed_with_analysis()
    payload = seed.to_dict()

    assert payload["seed_version"] == "0.2.0"
    assert payload["layout_analysis"]["version"] == "0.1.0"
    assert payload["source_map"][0]["source_line_ids"]
    assert 0.0 <= payload["source_map"][0]["confidence"] <= 1.0
    assert payload["source_map"][0]["evidence"]
```

- [ ] **Step 2: Add table projection test using existing Document AST table types**

```python
def test_geometry_table_projects_nested_document_nodes() -> None:
    seed = build_synthetic_table_chapter_seed()
    chapter = seed.document_ast.root.children[0]
    table = next(node for node in chapter.children if node.node_type is DocumentNodeType.TABLE)

    assert [child.node_type for child in table.children] == [
        DocumentNodeType.TABLE_ROW,
        DocumentNodeType.TABLE_ROW,
    ]
    assert all(
        cell.node_type is DocumentNodeType.TABLE_CELL
        for row in table.children
        for cell in row.children
    )
```

- [ ] **Step 3: Run focused tests and confirm failures**

```bash
PYTHONPATH=src python -m unittest tests.test_ibc2018_ingest -v
```

- [ ] **Step 4: Integrate chapter-level layout analysis**

For each selected chapter:

1. extract unsorted `PageLines` for the verified physical page range;
2. detect recurring margins across that chapter's pages;
3. clean pages and retain removal records;
4. estimate the chapter body-font profile;
5. infer and apply one page order profile per page;
6. detect and group table candidates;
7. coalesce remaining visual lines into IBC logical blocks;
8. attach confidence and evidence without changing IBC semantic meaning.

Table source lines must not also enter ordinary paragraph coalescing.

- [ ] **Step 5: Build exact nested table spans**

Use the deterministic tab/newline table string as the logical block text. During `_build_text_and_map`, record the block's global start. Translate each row and cell local span to a global `SourceSpan`. Emit:

```text
table
  -> table_row
       -> table_cell
```

Use locators:

```text
chapter:<number>/block:<index>/row:<row_index>/cell:<cell_index>
```

Set table attributes only to source-safe structural metadata such as `row_count`, `column_count`, `pdf_pages`, and `layout_role`. Do not infer units, headers, regulatory relationships, or applicability.

- [ ] **Step 6: Preserve ambiguous tables explicitly**

When geometry finds only one row, incompatible rows, or ambiguous page-column gaps, preserve ordinary text and emit a diagnostic such as `ambiguous-table-layout`. Retain `unsupported-table-layout` only when the source clearly announces a table but no trustworthy row/cell projection exists.

- [ ] **Step 7: Update private manifest metadata**

`scripts/ingest_ibc_2018.py` must add:

```json
"layout_analysis_version": "0.1.0"
```

Do not serialize absolute source paths.

- [ ] **Step 8: Run focused and full tests**

```bash
PYTHONPATH=src python -m unittest tests.test_layout_analysis \
  tests.test_table_geometry tests.test_ibc2018_ingest -v
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m compileall -q src scripts tests
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/building_code_ast/ingest/ibc2018.py \
  scripts/ingest_ibc_2018.py \
  tests/test_ibc2018_ingest.py tests/test_package_metadata.py
git commit -m "feat: integrate IBC layout evidence and tables"
```

---

### Task 5: Exact layout coverage and provenance validation

**Files:**
- Create: `src/building_code_ast/ingest/layout_validation.py`
- Modify: `src/building_code_ast/ingest/ibc2018.py`
- Modify: `src/building_code_ast/ingest/__init__.py`
- Create: `tests/test_layout_validation.py`
- Modify: `tests/test_ibc2018_ingest.py`

**Interfaces:**

```python
def validate_line_coverage(
    retained_lines: Sequence[VisualLine],
    removed_lines: Sequence[RemovedLine],
    blocks: Sequence[LogicalBlock],
) -> None: ...


def validate_page_profiles(
    pages: Sequence[CleanedPage],
    profiles: Sequence[PageOrderProfile],
) -> None: ...


def validate_table_candidate(table: TableCandidate) -> None: ...


def validate_layout_projection(chapter: ChapterLayout) -> None: ...
```

- [ ] **Step 1: Write missing and duplicate consumption tests**

```python
def test_missing_retained_line_fails() -> None:
    retained = (synthetic_line("line:a"), synthetic_line("line:b"))
    blocks = (synthetic_block(source_line_ids=("line:a",)),)

    with self.assertRaisesRegex(ValueError, "missing retained line"):
        validate_line_coverage(retained, (), blocks)


def test_duplicate_line_consumption_fails() -> None:
    retained = (synthetic_line("line:a"),)
    blocks = (
        synthetic_block(source_line_ids=("line:a",)),
        synthetic_block(source_line_ids=("line:a",)),
    )

    with self.assertRaisesRegex(ValueError, "consumed more than once"):
        validate_line_coverage(retained, (), blocks)
```

- [ ] **Step 2: Write page and table containment tests**

```python
def test_page_profile_cannot_reference_another_page() -> None:
    with self.assertRaisesRegex(ValueError, "page profile"):
        validate_page_profiles((cleaned_page(1),), (profile_for_page(2),))


def test_table_cell_fragment_must_belong_to_row() -> None:
    bad = table_with_foreign_cell_fragment()
    with self.assertRaisesRegex(ValueError, "outside its parent row"):
        validate_table_candidate(bad)
```

- [ ] **Step 3: Run focused tests and confirm missing-module failure**

```bash
PYTHONPATH=src python -m unittest tests.test_layout_validation -v
```

- [ ] **Step 4: Implement exact set and multiplicity checks**

Validation must reject:

- duplicate retained line IDs;
- a line appearing in both retained and removed sets;
- a removed line without a nonempty reason;
- a retained line absent from every block;
- a retained line consumed by multiple blocks;
- a block referencing an unknown line ID;
- a page profile with no matching page or duplicate page profile;
- a table row referencing a line from another page;
- a cell fragment not present in its row fragment set;
- a row or cell local span that does not round-trip to normalized table text.

- [ ] **Step 5: Invoke validation before ChapterSeed construction completes**

`extract_ibc2018_layout` or `build_chapter_seed` must validate the complete analyzed chapter before serialization. Fail closed on invariant errors. Existing `validate_document_ast` remains the final normalized-text and AST-span gate.

- [ ] **Step 6: Add positive integration coverage test**

```python
def test_complete_synthetic_chapter_consumes_every_line_once() -> None:
    layout = analyzed_synthetic_chapter_with_paragraph_and_table()
    validate_layout_projection(layout)
```

- [ ] **Step 7: Run all source-free verification**

```bash
PYTHONPATH=src python -m unittest tests.test_layout_validation \
  tests.test_layout_analysis tests.test_table_geometry \
  tests.test_ibc2018_ingest -v
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m compileall -q src scripts tests
python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"
git diff --check
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/building_code_ast/ingest/layout_validation.py \
  src/building_code_ast/ingest/ibc2018.py \
  src/building_code_ast/ingest/__init__.py \
  tests/test_layout_validation.py tests/test_ibc2018_ingest.py
git commit -m "feat: validate PDF layout coverage"
```

---

### Task 6: Documentation, private production comparison, and publication

**Files:**
- Modify: `README.md`
- Modify: `docs/how-to/ingest-ibc-2018.md`
- Modify: `docs/superpowers/specs/2026-08-01-pdf-layout-analysis-design.md`
- Private output only: regenerated ChapterSeed files and comparison report outside Git.

**Interfaces:**

The private production comparison reports counts and validation status without printing IBC text.

- [ ] **Step 1: Update operating documentation**

Document:

- recurring margin detection is position-gated;
- page reading order is inferred per page and falls back to top-to-bottom;
- body-font and confidence evidence are review aids;
- geometry-backed tables preserve rows, cells, and source fragments but do not interpret regulatory meaning;
- every retained line is coverage-validated;
- generated JSON remains private and outside public Git;
- ChapterSeed private contract is `0.2.0`.

- [ ] **Step 2: Run documentation and source-leak scans**

```bash
! grep -R --exclude='*.pyc' "/mnt/data/" README.md docs src scripts tests
! git ls-files | grep -E 'icc-2018\.pdf|chapter-[123]\.json|generated-private' \
  && exit 1 || exit 0
```

Expected: both commands exit zero.

- [ ] **Step 3: Run the complete exact-head source-free suite**

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m compileall -q src scripts tests
python -c "import tomllib; data=tomllib.load(open('pyproject.toml','rb')); assert data['project']['optional-dependencies']['ibc-pdf'] == ['PyMuPDF>=1.24,<2']"
git diff --check
```

Expected: PASS.

- [ ] **Step 4: Run the exact private IBC artifact**

```bash
PYTHONPATH=src python scripts/ingest_ibc_2018.py /private/icc-2018.pdf \
  --output-dir /private/generated/ibc-2018-layout-v2 \
  --chapters 1,2,3
```

Do not print source text. Record only:

- source SHA-256, byte size, and page count;
- ChapterSeed version and layout-analysis version;
- source-map and source-fragment counts by chapter;
- recurring header and footer key counts;
- page-order mode counts and inferred split summary;
- table, row, and cell counts;
- ambiguous and unsupported table diagnostic counts;
- Chapter 2 definition count;
- line-coverage validation result;
- source-map and Document AST span-validation result.

- [ ] **Step 5: Review count changes against the prior private baseline**

Prior baseline:

- Chapter 1: 216 source-map entries and 1,086 fragments;
- Chapter 2: 797 entries, 3,537 fragments, and 633 definition nodes;
- Chapter 3: 270 entries, 1,545 fragments, and two unsupported-table diagnostics.

Count changes are acceptable only when explained by recurring furniture removal, corrected line grouping, corrected column order, or table row/cell projection. Investigate unexplained text loss or sudden definition-count changes before publication.

- [ ] **Step 6: Commit documentation and exact-head records**

```bash
git add README.md docs/how-to/ingest-ibc-2018.md \
  docs/superpowers/specs/2026-08-01-pdf-layout-analysis-design.md
git commit -m "docs: explain IBC layout analysis"
```

- [ ] **Step 7: Push and open a stacked draft PR**

Head: `agent/ibc-layout-analysis`

Base: `agent/ibc-2018-local-ingestion`

Title: `Add adaptive layout analysis to IBC ingestion`

The PR body must include:

- the generic module boundaries;
- the unchanged public Document AST contract;
- the private ChapterSeed `0.2.0` boundary;
- recurring-margin, adaptive-column, table-geometry, and line-coverage behavior;
- source-free test results;
- private production comparison counts without source text;
- exact head SHA and verification commands;
- confirmation that the PDF and generated text-bearing files are absent from Git.

- [ ] **Step 8: Verify exact-head CI and self-review**

Review the exact pushed head for:

- generic modules containing accidental IBC-specific assumptions;
- line identity instability;
- position-insensitive furniture deletion;
- page-column gaps misclassified as table cells;
- table local/global span errors;
- duplicate or omitted line consumption;
- serialized absolute paths;
- public contract drift;
- private source leakage.

Keep the PR draft until CI passes and no critical or important issue remains.
