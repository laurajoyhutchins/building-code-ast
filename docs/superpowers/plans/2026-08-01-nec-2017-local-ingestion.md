# NEC 2017 Local Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a source-free, coordinate-aware local ingestion pipeline and generate private validated ArticleSeed files for NEC 2017 Articles 90, 100, and 110.

**Architecture:** Keep PDF extraction behind an optional PyMuPDF adapter. Convert extracted layout blocks into normalized article text, block-level source maps, and the existing DocumentAst contract. Publish only code, synthetic tests, and documentation; keep the supplied PDF and generated seeds outside Git.

**Tech Stack:** Python 3.12, standard library dataclasses/argparse/json/hashlib, optional PyMuPDF 1.x, unittest.

## Global Constraints

- Base runtime dependencies remain empty.
- Optional extra is named `nec-pdf` and pins `PyMuPDF>=1.24,<2`.
- Public Git contains no NEC text, page images, or generated ArticleSeed output.
- Default production seed is Articles `90,100,110`.
- Every normalized AST and source-map span must round-trip exactly.
- Same-page article transitions must not leak adjacent article text.
- The pipeline is structural only and makes no compliance interpretation.

---

## File Map

- `src/building_code_ast/ingest/pdf_layout.py`: layout dataclasses, normalization, reading order, optional PyMuPDF extraction.
- `src/building_code_ast/ingest/nec2017.py`: manifest, bookmark discovery, article selection, node classification, ArticleSeed construction.
- `src/building_code_ast/ingest/__init__.py`: narrow ingestion API exports.
- `scripts/ingest_nec_2017.py`: local CLI and overwrite protection.
- `tests/test_nec2017_ingest.py`: source-free unit and CLI tests.
- `docs/how-to/ingest-nec-2017.md`: operating procedure and publication boundary.
- `README.md`: ingestion capability and private-output boundary.
- `pyproject.toml`: optional `nec-pdf` dependency group.

### Task 1: Define layout records and deterministic normalization

**Files:**
- Create: `src/building_code_ast/ingest/pdf_layout.py`
- Create: `src/building_code_ast/ingest/__init__.py`
- Create: `tests/test_nec2017_ingest.py`

**Interfaces:**
- Produces: `PdfBlock`, `PdfOutlineItem`, `PdfLayoutDocument`, `normalize_block_text(text: str) -> str`, `order_content_blocks(blocks, page_width) -> tuple[PdfBlock, ...]`, `extract_pdf_layout(path: Path) -> PdfLayoutDocument`.

- [ ] **Step 1: Write failing normalization and reading-order tests**

```python
class PdfLayoutTests(unittest.TestCase):
    def test_normalize_block_text_repairs_line_break_hyphen(self) -> None:
        self.assertEqual(normalize_block_text("consid‐\nered necessary"), "considered necessary")

    def test_order_content_blocks_reads_left_column_before_right(self) -> None:
        blocks = (
            PdfBlock(1, (327, 100, 576, 130), "right"),
            PdfBlock(1, (54, 100, 303, 130), "left"),
        )
        self.assertEqual([b.text for b in order_content_blocks(blocks, 612)], ["left", "right"])
```

- [ ] **Step 2: Run the focused tests and confirm import failure**

Run: `PYTHONPATH=src python -m unittest tests.test_nec2017_ingest.PdfLayoutTests -v`
Expected: FAIL because the ingestion package does not exist.

- [ ] **Step 3: Implement immutable layout records, normalization, header/footer filtering, two-column order, and lazy PyMuPDF import**

The optional adapter must raise:

```python
RuntimeError("PyMuPDF is required for PDF ingestion; install building-code-ast[nec-pdf]")
```

- [ ] **Step 4: Run the focused tests**

Run: `PYTHONPATH=src python -m unittest tests.test_nec2017_ingest.PdfLayoutTests -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/building_code_ast/ingest tests/test_nec2017_ingest.py
git commit -m "feat: add PDF layout ingestion primitives"
```

### Task 2: Select article boundaries and construct validated ArticleSeeds

**Files:**
- Create: `src/building_code_ast/ingest/nec2017.py`
- Modify: `src/building_code_ast/ingest/__init__.py`
- Modify: `tests/test_nec2017_ingest.py`

**Interfaces:**
- Consumes: layout records from Task 1 and existing `DocumentAst` types.
- Produces: `SourceManifest`, `SourceMapEntry`, `ArticleSeed`, `discover_article_ranges(layout)`, `select_article_blocks(layout, article_number)`, `build_article_seed(layout, article_number, source_sha256, source_size)`.

- [ ] **Step 1: Add failing same-page boundary, definition, and provenance tests**

Use a synthetic layout where Article 100 ends in the left column and Article 110 begins in the right column on the same page. Assert Article 100 excludes the Article 110 anchor and Article 110 excludes the Article 100 tail. Assert an Article 100 definition block becomes `definition_entry`. Assert every source-map span and AST node span round-trips.

- [ ] **Step 2: Run focused tests and confirm missing API failures**

Run: `PYTHONPATH=src python -m unittest tests.test_nec2017_ingest.ArticleSeedTests -v`
Expected: FAIL because ArticleSeed APIs do not exist.

- [ ] **Step 3: Implement bookmark discovery, visible anchor trimming, source manifest identity, block classification, source-map construction, and AST validation**

Use `artifact_id="nfpa:70"` and `edition_id=f"2017:pdf:sha256:{source_sha256}"`. Keep PDF coordinates in source-map entries, not AST attributes.

- [ ] **Step 4: Run focused and complete tests**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_nec2017_ingest -v
PYTHONPATH=src python -m unittest discover -s tests -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/building_code_ast/ingest tests/test_nec2017_ingest.py
git commit -m "feat: build NEC article seeds"
```

### Task 3: Add the local CLI and optional dependency boundary

**Files:**
- Create: `scripts/ingest_nec_2017.py`
- Modify: `pyproject.toml`
- Modify: `tests/test_nec2017_ingest.py`

**Interfaces:**
- Consumes: `extract_pdf_layout` and `build_article_seed`.
- Produces: `main(argv: list[str] | None = None) -> int` and JSON files `manifest.json`, `article-<number>.json`.

- [ ] **Step 1: Add failing CLI overwrite and path-redaction tests**

Test that a nonempty output directory fails without `--force`, and serialized manifests contain file name but no absolute input path.

- [ ] **Step 2: Run CLI tests and confirm failure**

Run: `PYTHONPATH=src python -m unittest tests.test_nec2017_ingest.CliTests -v`
Expected: FAIL because the script is absent.

- [ ] **Step 3: Implement the CLI and add the optional dependency group**

Add:

```toml
[project.optional-dependencies]
nec-pdf = ["PyMuPDF>=1.24,<2"]
```

Default articles are `90,100,110`. Write deterministic sorted-key JSON with a trailing newline.

- [ ] **Step 4: Run focused and complete verification**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_nec2017_ingest -v
PYTHONPATH=src python -m compileall -q src scripts tests
python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/ingest_nec_2017.py pyproject.toml tests/test_nec2017_ingest.py
git commit -m "feat: add local NEC ingestion CLI"
```

### Task 4: Document operation and publication safety

**Files:**
- Create: `docs/how-to/ingest-nec-2017.md`
- Modify: `README.md`

**Interfaces:**
- Documents the exact command, output contract, local-only boundary, and known limitations.

- [ ] **Step 1: Write the how-to and README section**

Document:

```bash
python -m pip install -e '.[nec-pdf]'
python scripts/ingest_nec_2017.py /path/to/nec-2017.pdf --output-dir generated-private/nec-2017
```

State that generated text-bearing output is private and must not be committed.

- [ ] **Step 2: Run documentation and source scans**

Run:

```bash
! grep -R --exclude='*.pyc' "Practical Safeguarding" README.md docs/how-to src scripts
! grep -R --exclude='*.pyc' "/mnt/data/" README.md docs/how-to tests src scripts
```

Expected: both commands exit zero.

- [ ] **Step 3: Commit**

```bash
git add README.md docs/how-to/ingest-nec-2017.md
git commit -m "docs: explain private NEC ingestion"
```

### Task 5: Run the supplied PDF and package private seed artifacts

**Files outside Git:**
- Read: `/path/to/nec-2017.pdf`
- Create: `/tmp/nec-2017-seed/`
- Create: `/tmp/nec-2017-seed.zip`

**Interfaces:**
- Produces private `manifest.json`, `article-90.json`, `article-100.json`, and `article-110.json`.

- [ ] **Step 1: Run the CLI against the supplied PDF**

Run:

```bash
PYTHONPATH=src python scripts/ingest_nec_2017.py /path/to/nec-2017.pdf --output-dir /tmp/nec-2017-seed --articles 90,100,110 --force
```

Expected: four JSON files are written.

- [ ] **Step 2: Validate generated outputs without printing NEC text**

Check file names, SHA-256, article numbers, AST validation, source-map span round-trips, node counts, and definition-entry count for Article 100. Do not print source text.

- [ ] **Step 3: Zip the private output**

Run: `python -m zipfile -c /tmp/nec-2017-seed.zip /tmp/nec-2017-seed/*.json`
Expected: ZIP creation succeeds.

### Task 6: Exact-head verification and draft PR

**Files:** all changed public files.

- [ ] **Step 1: Run final verification**

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m compileall -q src scripts tests
python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"
git diff --check
```

- [ ] **Step 2: Review Git status and confirm no private artifacts are tracked**

Run:

```bash
git status --short
git ls-files | grep -E 'nec-2017\.pdf|article-(90|100|110)\.json' && exit 1 || exit 0
```

- [ ] **Step 3: Publish branch `agent/nec-2017-local-ingestion` and open a draft PR against `main`**

PR title: `Add local NEC 2017 ingestion pipeline`

The body must describe the local-only source boundary, coordinate-aware extraction, same-page article trimming, validated ArticleSeed outputs, synthetic tests, optional dependency, local production smoke test, and exact verification commands.
