# NFPA 13 (2019) local AST extractor

`tools/build_nfpa13_2019_bundle.py` is the canonical local entry point. It runs the low-level PDF engine in `tools/extract_nfpa13_2019_ast.py`, then upgrades that raw extraction into the strict `nfpa13-ast-bundle/0.2.0` contract.

The tool is intentionally local-only. Do not commit the source PDF, canonical source text, table contents, generated AST, or overlay PDFs.

## Requirements

- Python 3.12 or later
- PyMuPDF for local PDF processing
- the repository source tree, including the Document AST `0.1.0` reader and schema
- the exact Git commit that produced the bundle

The verified source artifact has SHA-256:

```text
07c229b70cfdde21c3c67e6918040663c76aec680a0bd8d026392e21e8b81ee5
```

## Run

```bash
python tools/build_nfpa13_2019_bundle.py /path/to/nfpa-2019.pdf \
  --producer-commit <full-40-character-git-sha> \
  --output local-output/nfpa13-2019-source-linked-ast.json \
  --report local-output/nfpa13-2019-source-linked-ast-validation.md \
  --overlays-dir local-output/overlays \
  --overlay-pages 22,181,182,323,489,513
```

The default expected source hash fails closed when the input artifact differs. Pass an empty `--expected-sha256` only when deliberately testing another source artifact.

## Contract stages

1. The low-level engine extracts a page-, column-, font-, and bounding-box-aware source stream and builds the source-linked Document AST.
2. The strict wrapper round-trips that Document AST through the repository’s authoritative `document_ast_from_dict` reader.
3. Only explicit Annex A clauses emit `explains` relationships. Synthesized ancestry containers remain structural only.
4. Every relationship records whether its target is internal, an identified external standard, or an unspecified document. Unresolved references never guess a target artifact.
5. External publication identifiers include NFPA, ASTM, ASME, AWWA, ANSI, ANSI/UL, IEEE, ISO, and UL families.
6. Lexical annotations record `method`, parser revision, and review state. Deterministic execution is not represented as semantic confidence.
7. The bundle records exact producer provenance: repository commit, engine and wrapper content hashes, Python version, PyMuPDF version, and normalized options.
8. The complete bundle passes both the low-level provenance validator and the strict bundle-contract validator.

## Bundle contract

The canonical local envelope is `nfpa13-ast-bundle/0.2.0` and contains:

- exact producer metadata;
- source identity and PDF boundaries;
- a Document AST `0.1.0` value accepted by the existing strict reader;
- target-domain-aware relationships;
- bounded lexical semantic annotations with explicit review status;
- geometry-derived table matrices;
- source-map locations for rendering and audit;
- aggregate statistics and separate engine and contract validation reports.

The machine-readable contract is `schemas/nfpa13-ast-bundle.schema.json`.

## Reviewed cases

`fixtures/reviewed/nfpa13-2019-golden-cases.json` stores non-reconstructive expectations from source review. It covers normative and annex structure, definitions, artifact filtering, a table shape, internal and unresolved references, explicit-versus-implicit Annex A relationships, and external-standard families.

Verify those expectations against a local complete bundle:

```bash
python tools/verify_nfpa13_2019_reviewed_cases.py \
  local-output/nfpa13-2019-source-linked-ast.json
```

The registry contains locators, labels, structural counts, relationship expectations, and geometry shapes. It does not contain clause bodies or table contents.

## Interpretation boundary

Table rows and cells reflect detected page geometry, not reviewed semantic column meaning. Figure captions are preserved, but image and diagram semantics remain unsupported. Lexical annotations are deterministic parser outputs and default to `review_status=unreviewed`; they are not engineering interpretations, compliance decisions, or substitutes for the source publication.
