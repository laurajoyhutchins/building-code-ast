# AISC SCM 15 exact-source verification

This step is deliberately separate from source characterization and Document AST parsing.

PR #52 established the retained Manual's edition/printing identity and major internal publication-role boundaries. Exact-byte and physical-PDF facts must now be measured from the retained private `scm-15.pdf` on a host that can access all 221,820,282 bytes.

The connected ChatGPT Drive surface cannot transport this object because its raw-download limit is 104,857,600 bytes. That transport limit is not a publication fact and must not block or weaken exact-source verification.

## Verification boundary

Run the verifier only against the retained private artifact. Do not substitute another nominally equivalent AISC SCM 15 PDF.

The verifier emits only non-reconstructive factual evidence:

- exact byte count and SHA-256;
- PDF page count and version;
- encryption/password/permission state reported by the PDF reader;
- page-label rules;
- aggregate bookmark depth and valid/invalid target counts, without bookmark titles;
- page-level embedded-text presence counts, without extracted text;
- distinct page geometries and counts;
- explicitly supplied one-based PDF ranges for operator-verified logical components;
- verifier tool identity and UTC verification time.

It does not emit the local source path, source prose, bookmark titles, page images, tables, figures, equations, or extracted corpus material.

## Local setup

From an exact checkout of this branch or its eventual merge:

```text
python -m pip install -e '.[evidence-pdf]'
```

Keep the source outside Git.

## First pass: inspect physical PDF facts

Run without component ranges first:

```text
python -m building_code_ast.aisc_scm15_source_verification \
  /private/path/scm-15.pdf \
  --output /tmp/aisc-scm-15-exact-source-receipt.json
```

The command fails before PDF inspection if the source is not a regular file or is not exactly 221,820,282 bytes. A successful receipt binds the exact bytes by SHA-256 and records the PDF-level observations needed to review physical coordinates.

Review the receipt before retaining it. It should contain factual metadata only and no reconstructive source expression.

## Second pass: record verified component ranges

Determine component boundaries by inspecting the exact retained PDF. Use one-based PDF page numbers, not printed page labels and not positions from another copy.

Candidate component labels are:

```text
manual-front-matter
manual-parts-1-15
ansi-aisc-360-16
rcsc-high-strength-bolts-2014
aisc-code-standard-practice-2016
manual-part-17
manual-nomenclature-index
```

After each boundary is independently verified against the exact retained bytes, rerun with the corresponding range:

```text
python -m building_code_ast.aisc_scm15_source_verification \
  /private/path/scm-15.pdf \
  --component-range ansi-aisc-360-16=FIRST-LAST \
  --output /tmp/aisc-scm-15-exact-source-receipt.json
```

`FIRST-LAST` above is intentionally not a value. Replace it only with page coordinates observed from the retained artifact. Do not infer or copy page ranges from a web copy, another printing, or the connected text projection.

Additional verified ranges may be supplied by repeating `--component-range`. The verifier rejects duplicate component IDs, non-positive or reversed ranges, and any range extending past the observed PDF page count.

## Evidence review and integration

Before a receipt is used as repository evidence, confirm:

1. the byte count is 221,820,282;
2. the SHA-256 was computed from the retained private bytes;
3. the receipt contains no local source path or protected source content;
4. every supplied component range was checked against this exact artifact;
5. unresolved ranges remain absent rather than guessed;
6. any correction/errata or digital-revision conclusion is supported independently rather than inferred from PDF metadata timestamps.

The source PDF remains private and outside Git. A reviewed source-safe receipt may supply factual identity and coordinate evidence for the source profile/source registration without granting redistribution rights.

## Parser gate

Do not begin a whole-Manual parser from this step.

Once one coherent component has an exact verified physical range, a later descendant may choose that component explicitly for Document AST work. ANSI/AISC 360-16 is a strong candidate because it is an independently identified publication with its own hierarchy, but this verification PR does not select or implement that parser.
