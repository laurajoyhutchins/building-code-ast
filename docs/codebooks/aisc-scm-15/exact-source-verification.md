# AISC SCM 15 exact-source verification

This step is deliberately separate from source characterization and Document AST parsing.

PR #52 established the retained Manual's edition/printing identity and major internal publication-role boundaries. Exact-byte and physical-PDF facts must be measured from the retained private `scm-15.pdf` on a host that can access all 221,820,282 bytes.

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

The untouched retained artifact was verified on 2026-08-10:

- filename: `scm-15.pdf`
- media type: `application/pdf`
- byte size: **221,820,282**
- SHA-256: `c5fbe648fd81a7ecda10df115393bbb9492924c8ce22167fc6d86c8b87fd8e7f`
- physical PDF page count: **2,303**
- PDF version: **1.6**
- encrypted: **false**
- needs password: **false**
- raw permissions value reported by PyMuPDF: **-4**
- outline entries: **2,371**, all with valid targets; maximum depth **3**
- embedded-text pages: **2,025**; pages without embedded text: **278**
- page-label rules: none reported
- five distinct page geometries were observed

Review the receipt before retaining it. It should contain factual metadata only and no reconstructive source expression.

## Second pass: record verified component ranges

Determine component boundaries by inspecting the exact retained PDF. Use one-based PDF page numbers, not printed page labels and not positions from another copy.

The exact retained artifact established these contiguous component ranges:

| Component identity | Inclusive physical PDF pages | Page count |
| --- | ---: | ---: |
| `manual-front-matter` | 1–9 | 9 |
| `manual-parts-1-15` | 10–1375 | 1366 |
| `ansi-aisc-360-16` | 1376–2049 | 674 |
| `rcsc-high-strength-bolts-2014` | 2050–2146 | 97 |
| `aisc-code-standard-practice-2016` | 2147–2229 | 83 |
| `manual-part-17` | 2230–2273 | 44 |
| `manual-nomenclature-index` | 2274–2303 | 30 |

The Part 16 container is physical pages 1376–2229 and is kept distinct from its ANSI/AISC 360-16, 2014 RCSC, and 2016 AISC Code of Standard Practice components. The Manual handbook material and Part 17/nomenclature/index remain distinct from those embedded standards and codes.

The range receipt was produced by repeating `--component-range` for each row:

```text
python -m building_code_ast.aisc_scm15_source_verification \
  /private/path/scm-15.pdf \
  --component-range manual-front-matter=1-9 \
  --component-range manual-parts-1-15=10-1375 \
  --component-range ansi-aisc-360-16=1376-2049 \
  --component-range rcsc-high-strength-bolts-2014=2050-2146 \
  --component-range aisc-code-standard-practice-2016=2147-2229 \
  --component-range manual-part-17=2230-2273 \
  --component-range manual-nomenclature-index=2274-2303 \
  --output /tmp/aisc-scm-15-exact-source-receipt-with-ranges.json
```

The verifier rejects duplicate component IDs, non-positive or reversed ranges, and any range extending past the observed PDF page count.

## Verified private page-range derivatives

After the original SHA-256 was established, six private analysis derivatives were created from the untouched original. Their physical page ranges provide complete, non-overlapping coverage of pages 1–2303. Every derivative is below the 104,857,600-byte transport ceiling.

| Derivative filename | Inclusive original PDF pages | Derivative pages | Bytes | SHA-256 |
| --- | ---: | ---: | ---: | --- |
| `01-front-and-manual-parts-1-5.pdf` | 1–707 | 707 | 71,372,836 | `80148e3469b088f7463319491ffa10a7a68becb1f6e2c4aa1adf34968d1d7685` |
| `02-manual-parts-6-15.pdf` | 708–1375 | 668 | 63,745,838 | `7ff498519f41e07cd4de732afb76fb2e569abcd5cf814a24816285a3bdbe9b60` |
| `03-ansi-aisc-360-16.pdf` | 1376–2049 | 674 | 64,464,266 | `6ba073e6549e0c7408909cde2261f2bc393c7e6bfc63392268bd51399338e126` |
| `04-rcsc-high-strength-bolts-2014.pdf` | 2050–2146 | 97 | 9,209,711 | `6261a9ba9f42bdd375545a626f558278da26d3a7a71b1601ac0c1f7da6defde9` |
| `05-aisc-code-standard-practice-2016.pdf` | 2147–2229 | 83 | 8,159,218 | `f604edf5f5939834197bdfed04246aea327f6ad0200e7e12855fedc57583b152` |
| `06-manual-part-17-and-nomenclature-index.pdf` | 2230–2303 | 74 | 5,875,661 | `ed2aff0858d330091105eed9c9b55d59625c5abe0ccd60ad1b3e06c1a34b3dc0` |

The derivatives and a source-safe JSON manifest are stored in a clearly associated private Google Drive folder with sharing verified as not shared. The original and all derivative PDFs remain outside Git.

Production procedure: Python 3.12 with PyMuPDF 1.28.2 opened the verified original; each inclusive range was inserted into a new PDF using `insert_pdf(source, from_page=first-1, to_page=last-1, links=True, annots=True, widgets=True)`; source metadata was copied; outputs were saved with `garbage=0, clean=False, deflate=False`.

Fidelity checks found zero mismatches across all pages for mediabox/cropbox/rotation, text presence and character counts, image-reference counts, and link counts. Rendered first and last pages matched their corresponding original pages for every derivative. The procedure rewrites the PDF object graph and does not copy the source outline/bookmarks; derivative hashes do not substitute for or reconstruct the original hash, and no byte-level equivalence is claimed.

## Evidence review and integration

Before a receipt is used as repository evidence, confirm:

1. the byte count is 221,820,282;
2. the SHA-256 was computed from the retained private bytes;
3. the receipt contains no local source path or protected source content;
4. every supplied component range was checked against this exact artifact;
5. derivative coverage has no gaps or accidental overlaps;
6. derivative hashes are recorded only as provenance for transformed analysis artifacts;
7. any correction/errata or digital-revision conclusion is supported independently rather than inferred from PDF metadata timestamps.

The source PDF and derivatives remain private and outside Git. A reviewed source-safe receipt and manifest may supply factual identity, coordinate, and transformed-artifact evidence for the source profile/source registration without granting redistribution rights.

## Parser gate

Do not begin a whole-Manual parser from this step.

Once one coherent component has an exact verified physical range, a later descendant may choose that component explicitly for Document AST work. ANSI/AISC 360-16 is a strong candidate because it is an independently identified publication with its own hierarchy, but this verification PR does not select or implement that parser.
