# Recovery observation contract

`recovery-observation-v1` is the publication-neutral evidence boundary for text recovered from rasterized or OCR-derived PDF regions. It records how recovery happened without deciding what recovered text means.

## Boundary

A recovery observation may record:

- exact source identity: SHA-256, byte size, media type, and page count;
- page or region identity and coordinate space;
- render backend, version, parameters, and output digest;
- recovery backend, version, and parameters;
- recovered-text SHA-256;
- whether the recovered expression is only represented by a durable digest or is available through an authorized private payload binding;
- performed and deliberately omitted operations;
- source-safe warnings.

The contract does **not** contain publication locator grammar, normative/commentary authority, legal interpretation, semantic promotion, or protected recovered expression.

## Payload states

`digest_only` means the durable evidence proves an expression digest but does not authorize or supply the expression for downstream use. A digest-only observation cannot be used to populate searchable text in a derivative PDF.

`private_retrievable` means an authorized private payload may be supplied outside the durable source-safe record. Before downstream use, the caller must provide that payload and the implementation must verify that its SHA-256 exactly matches `recovered_text_sha256`.

Changing `digest_only` to `private_retrievable` is not a formatting operation. It requires an authoritative private payload/provenance binding.

## Publication-specific interpretation stays outside

The shared contract deliberately stops before structural or authority interpretation.

For ANSI/AISC 360-16, dotted hierarchy locator recognition remains in the AISC raster hierarchy adapter. Shared recovery provenance does not decide whether a recovered number is hierarchy.

For TMS 402-16, normative versus commentary assignment remains governed by the explicit TMS publication authority policy. A left or right coordinate in a generic recovery observation has no authority meaning by itself.

## PDF enrichment bridge

PDF enrichment may consume recovered expression only through `searchable_text_entry_from_recovery(...)`. The bridge requires:

1. a `private_retrievable` recovery observation;
2. an exact recovered-text digest match;
3. an explicit PDF-point region bounding box.

The bridge maps the recovery source kind to the enrichment text origin. It does not make the enriched derivative authoritative and does not replace the canonical source artifact. The untouched retained source remains the source of record.

## Durable form

The closed JSON Schema projection is [`schemas/recovery-observation.schema.json`](../../schemas/recovery-observation.schema.json). The durable form contains hashes and provenance only. Protected recovered text stays private or transient.
