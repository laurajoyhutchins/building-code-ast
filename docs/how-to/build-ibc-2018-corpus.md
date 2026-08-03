# Build the private 2018 IBC structural corpus

## Prerequisites

Use Python 3.12 and install the optional PDF dependencies used by the IBC ingestion pipeline:

```bash
python -m pip install -e '.[ibc-pdf,validation]'
```

Keep the exact `icc-2018.pdf` and all text-bearing intermediate files outside Git. The required SHA-256 is:

```text
c8f0b75522707a39daf5202edee25d7fdce6c177c382f828a6dc1dfd5cc0b18d
```

## Private evidence inputs

The corpus builder consumes three private artifacts:

- complete positioned page-line evidence from all 761 PDF pages;
- the validated Chapter 2 seed used for definition locations;
- page-level image-region metadata.

These files can reproduce source layout or text and must remain in a private ignored directory.

## Build

```bash
PYTHONPATH=src python tools/build_ibc_2018_corpus.py \
  --page-lines /private/ibc-2018/page-lines.ndjson \
  --chapter-2-seed /private/ibc-2018/chapter-2.json \
  --image-regions /private/ibc-2018/image-regions.json \
  --output-dir corpora/ibc-2018
```

The builder validates page coverage, derives stable IDs, consolidates continuations, separates detections from normalized records, writes source-safe inventories, and reports item-level discrepancies.

## Vector-path evidence and source-safe inventory

Extract private geometry summaries directly from the exact PDF, then convert them into public source-safe review records:

```bash
PYTHONPATH=src python tools/extract_ibc_2018_vector_regions.py \
  /private/ibc-2018/icc-2018.pdf \
  /private/ibc-2018/vector-regions.json
PYTHONPATH=src python tools/build_ibc_2018_vector_inventory.py \
  /private/ibc-2018/vector-regions.json \
  corpora/ibc-2018
```

The private file contains geometry summaries, not source text, but remains outside Git because it is derived from the complete source. The public inventory does not assert that a vector region is a technical graphic.

## Reconcile references and build the review queue

```bash
PYTHONPATH=src python tools/reconcile_ibc_2018_references.py corpora/ibc-2018
PYTHONPATH=src python tools/reconcile_ibc_2018_external_references.py corpora/ibc-2018
PYTHONPATH=src python tools/prioritize_ibc_2018_review_queue.py corpora/ibc-2018
PYTHONPATH=src python tools/render_ibc_2018_coverage_report.py corpora/ibc-2018
```

Reference reconciliation is conservative: exact known targets, digit-only section-heading prefixes, and unique external aliases only.

## Verify

```bash
python -m unittest discover -s tests -v
python -m compileall -q src scripts tools tests
python tools/validate_ibc_2018_corpus.py corpora/ibc-2018
python tools/validate_ibc_2018_schemas.py corpora/ibc-2018 schemas
```

A zero-discrepancy result means the deterministic corpus contract is internally consistent. It does not mean every semantic interpretation has been human verified.

## Review corrections

Review `ibc-2018-review-queue.csv`, `ibc-2018-review-summary.md`, `ibc-2018-semantic-review-packet.md`, `ibc-2018-discrepancies.md`, and `ibc-2018-unresolved-borderline-cases.md`. When a count changes, add a correction record with the prior assertion, contradictory evidence, corrected value, and status transition. Never edit source hashes or evidence anchors to preserve an old count.
