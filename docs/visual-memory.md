# Engineering Visual Memory

Engineering Visual Memory is a private derived retrieval layer over exact retained technical publications. It is deliberately downstream of source evidence and Document AST/corpus inventories. It does not add legal, code-compliance, or engineering-authority semantics.

## Authority boundaries

```text
exact retained source artifact
  -> existing page / block / AST / corpus observations
  -> private visual-object projection
  -> private rendered staging views
  -> visual-memory embeddings and local descriptors
  -> retrieval candidates
  -> source-context / native-vision review
```

Git contains only source-safe implementation, schemas, tests, and compact evaluation receipts. Retained PDFs, private ASTs that reproduce protected expression, rendered figures/pages, CLIP model weights, generated embeddings, and ORB descriptors remain outside Git.

Visual similarity answers "where should I look?" It does not establish semantic or engineering equivalence. Text queries use lexical/structural evidence first and visual similarity only as augmentation. Scan/image-only source re-identification uses CLIP to shortlist candidates and ORB local features to identify likely source occurrences.

## Object contract

A visual object has two identities when needed:

- `occurrence_id`: one rendered source occurrence on a particular page/region;
- `logical_visual_id`: the publication-level figure or logical visual identity when the source corpus can establish one.

For ordinary single-occurrence objects, `logical_visual_id` can equal `occurrence_id`.

Every object retains exact `source_sha256`, page, corpus namespace, published label when available, structural context, and an explicit `caption_text_quality` state (`usable`, `degraded`, or `unavailable`). Missing/degraded text is evidence state, not an invitation to synthesize a caption.

## Projection boundary

Source-specific AST/corpus machinery owns object discovery and source coordinates. The generic visual-memory code does not rescan a publication when a source inventory already establishes the denominator. Private projectors may use caption geometry, raster rectangles, vector-path clusters, page regions, or other source evidence, but they emit the same generic staging object contract.

The generic builder consumes private staged images plus `objects.jsonl`, creates deterministic global/medium views, optionally adds finer views where a hard-fragment benchmark justifies them, embeds image and context channels, and writes a source-free private index.

## Retrieval operations

- `figure-image`: semantic/fragment visual retrieval across figure objects.
- `figure-text`: lexical/structural retrieval first, then context and visual reranking.
- `figure-related`: candidate discovery only; cross-corpus similarity never asserts equivalence.
- `page-image --mode source`: CLIP shortlist followed by ORB local-feature reranking for exact source re-identification.

Page objects and figure objects remain in separate namespaces because full-page similarity and figure similarity have different retrieval semantics and benchmark behavior.

## Runtime and private release

The current private release is **Engineering Visual Memory v0.4**. The tested archive SHA-256 is:

`4e4ed0ca37524c653768df81d5677f6115b2894934f02566dd0281ca068b5c76`

It depends on the separately retained **CLIP Runtime v1** checkpoint whose model SHA-256 is:

`40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af`

The private archive is retained in Google Drive under `Offline Execution Payloads / Engineering Visual Memory`. Git intentionally does not contain Drive object IDs.

## Rebuild contract

A rebuild must record at least:

1. exact source artifact SHA-256 and byte size for each corpus;
2. source AST/corpus implementation version or exact Git commit where applicable;
3. visual projector version and object denominator;
4. view policy, including whether fine 50% views are enabled;
5. CLIP runtime/model SHA-256;
6. generated object/view counts;
7. source-safety verification proving no PDFs or rendered source images are packaged;
8. corpus-specific fragment-recovery receipt;
9. claim boundaries for cross-corpus retrieval and source re-identification.

Large builds must be resumable/content-addressed. The generic builder caches each object by render hash, model hash, view policy, and packed text context so an interrupted run can reuse completed embedding work. Completed projection or embedding slices should not be recomputed solely because a later slice is interrupted.

## Validation

Run the source-safe unit tests and package verifier:

```bash
python -m unittest discover -s tests -p 'test_visual_memory.py' -v
python tools/visual_memory/verify_package.py /path/to/Engineering-Visual-Memory-v0.4.zip \
  --expected-sha256 4e4ed0ca37524c653768df81d5677f6115b2894934f02566dd0281ca068b5c76
```

Private smoke tests should exercise one figure fragment, one text query, one TMS scan fragment, and one AISC image-only-page fragment against the exact retained runtime/index artifacts.
