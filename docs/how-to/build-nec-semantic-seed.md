# Build the private NEC semantic seed

This procedure consumes the private ArticleSeed JSON generated from a user-supplied 2017 NEC PDF. The output reproduces NEC source expression and **must remain private**, outside public Git, public package artifacts, and public CI artifacts.

## Prerequisites

Generate the ArticleSeed files first:

```bash
python -m pip install -e '.[nec-pdf]'
python scripts/ingest_nec_2017.py /path/to/nec-2017.pdf \
  --output-dir generated-private/nec-2017
```

## Generate the semantic bundle

```bash
PYTHONPATH=src python scripts/build_nec_2017_semantics.py \
  --article-90 generated-private/nec-2017/article-90.json \
  --article-100 generated-private/nec-2017/article-100.json \
  --article-110 generated-private/nec-2017/article-110.json \
  --output-dir generated-private/nec-2017-semantics
```

The command validates that all inputs share one artifact and edition identity before touching the output directory. Add `--force` only to replace a directory containing exclusively files produced by this generator. Unexpected files or subdirectories cause a fail-closed error.

The bundle contains:

- `definitions-article-100.json`
- `language-policy-90.5.json`
- `section-110.2.json`
- `section-110.3.json`
- `section-110.14.json`
- `section-110.16.json`
- `section-110.26.json`
- `manifest.json`

## Review the result

Confirm that the manifest reports the expected artifact hash, definition count, section list, clause counts, and diagnostic counts. Keep the generated directory access-controlled. Public contributions should contain only project-authored code, schemas, documentation, and synthetic fixtures.
