# Building Code AST Archaeology

This repository contains a causal Deciduous backfill of the decisions that produced the current compiler, source-evidence, parser-family, and publication-boundary architecture.

The graph is not a commit timeline and is not an authority for parser behavior. Current behavior remains defined by source files, schemas, tests, merged history, accepted LORE records, and the controlling source publications.

Start with [`docs/archaeology/README.md`](docs/archaeology/README.md). The canonical graph source is the ordered patch set under [`.deciduous/patches/`](.deciduous/patches/). Generated projections are validated by:

```bash
python scripts/validate_archaeology.py --write
python scripts/validate_archaeology.py
python -m unittest tests.test_archaeology -v
```
