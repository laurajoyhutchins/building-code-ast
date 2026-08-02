# Washington WAC Jurisdictional Amendment Patches

## Purpose

The Washington amendment layer represents chapter 51-50 WAC provisions as jurisdictional overlays on an identified International Building Code publication state. It does not copy the adopted IBC, determine which authority applies to a project, or evaluate compliance.

Washington adopts the 2021 IBC by reference in chapter 51-50 WAC and publishes state amendments as separately cited WAC sections. The patch model preserves that relationship explicitly:

```text
identified IBC publication state
  + effective Washington WAC patches
  -> reviewable jurisdictional overlay
```

## Patch contract `0.2.0`

`JurisdictionalAmendmentPatch` preserves:

- registered source identity;
- jurisdiction and issuing authority;
- exact base `publication:<sha256>` state;
- WAC citation and affected base locator;
- operation: `add`, `replace`, `delete`, `reserve`, or `scope`;
- half-open effective interval `[effective_from, effective_to)`;
- replacement text or scope statement when required;
- deterministic source-local sequence and source anchor;
- deterministic `amendment:<sha256>` identity.

The closed JSON projection is [`schemas/jurisdictional-amendment-patch.schema.json`](../../schemas/jurisdictional-amendment-patch.schema.json). Runtime deserialization rejects unknown fields and recomputes patch identity.

## Operation rules

`add` and `replace` require replacement text. `delete` and `reserve` prohibit replacement text. `scope` requires a scope statement and prohibits replacement text. The `scope` field is null for every non-scope operation, so one record cannot encode two legal effects.

Operation evidence differs by acquisition path. Direct official-page ingestion classifies a located clause as `replace` when the exact locator exists in the identified base AST, or `add` when an ancestor exists but the exact locator does not. It never guesses when neither condition holds. Explicit `delete`, `reserve`, and `scope` directives are available through the normalized acquisition contract described below.

## Effective intervals

Patch intervals are half-open:

- a patch is active on `effective_from`;
- it remains active before `effective_to`;
- it is inactive on `effective_to` itself;
- a null `effective_to` means the patch has no recorded end date.

Chapter-level metadata is not assumed to prove one universal date. `WashingtonWacHtmlAdapter` accepts WAC-section and locator-specific effective-date mappings, with locator-specific evidence taking precedence. It falls back to the registered source publication's effective date only when one is present. This supports one WAC citation containing clauses from different rule histories.

## Amendment-set validation

`AmendmentSet` requires every patch to share one jurisdiction and one base publication state. Source-local sequence values must be unique within each registered source.

Patches are ordered by effective date, source sequence, WAC citation, locator, and deterministic patch identity. The identity tie-breaker makes the result independent of input tuple order.

Overlapping records with the same legal effect are permitted as reaffirmations or duplicate-source evidence. Overlapping scope records may coexist with an add or replacement affecting the same locator. Other overlapping incompatible effects fail closed.

`active_for(locator, date)` returns the ordered patches active for one base locator on one date. It does not apply those patches to an AST or decide how multiple provisions interact semantically.

## Direct official HTML adapter

`WashingtonWacHtmlAdapter` version `0.4.0` consumes registered UTF-8 `text/html` with evidence role `jurisdictional_law`. It must be invoked through `run_evidence_adapter`, so role, media type, and exact-byte SHA-256 are verified before parsing.

The current Washington state site renders operative provision blocks as leaf `span` elements inside `div.section-page`. The adapter captures citation headings plus only those scoped section-body spans. Locator-like text in breadcrumbs, navigation, titles, and other page chrome is ignored.

The adapter retains support for paragraph- and list-shaped official fixtures. It segments pages by chapter 51-50 WAC citation headings, stops clause grouping at statutory-history blocks, and extracts code clauses beginning with explicit locators. It requires:

- the exact base publication state;
- a nonempty base-locator oracle;
- WAC-section or locator-specific effective dates when the source register does not provide one;
- an explicit WAC-to-locator mapping for reserved sections.

The adapter emits only `add`, `replace`, and `reserve` operations because those classifications can be bounded from official clause presentation plus the base AST oracle. Missing dates, unresolved locators, unrecognized sections, and unmapped reserved sections become diagnostics and unsupported regions.

Candidate ordinals are preserved even when an earlier source section or clause is unsupported. Gaps are intentional source provenance, not missing output.

The August 2, 2026 official-corpus validation extracted both reviewed clauses from WAC 51-50-0403 and preserved their distinct effective dates: `403.4.8.3` on March 16, 2024, and `403.5.4` on March 15, 2024. The source-free receipt is in [`docs/validation/official-evidence-2026-08-02.json`](../validation/official-evidence-2026-08-02.json).

## Normalized directive adapter

`NormalizedWashingtonWacHtmlAdapter` version `0.2.0` consumes project-normalized section blocks containing explicit directives such as:

```html
<section>
  <h3>WAC 51-50-0107</h3>
  <p>Section 107.3 is added.</p>
  <p>...</p>
</section>
```

This grammar supports `add`, `replace`, `delete`, `reserve`, and `scope`. It is appropriate only after an acquisition step has preserved the original registered artifact and produced explicit, reviewable operation evidence. Its name prevents normalized fixtures from being mistaken for the official website's native structure.

For `add`, a missing exact locator is expected. Decimal additions resolve through an existing parent locator. Whole-number IBC sections can resolve through their chapter designation, and appendix-prefixed sections can resolve through their appendix designation. Other operations require the exact base locator.

Normalized output also preserves the original section ordinal when unsupported candidates are skipped. The official-corpus validation replayed two normalized derivatives linked to the exact upstream WAC digest and confirmed deterministic projections.

## Official-source boundary

Chapter 51-50 WAC identifies the adopted IBC edition and enumerates state amendments and reserved sections as individual WAC provisions. Public repository fixtures use invented text shaped like the relevant presentation. Official HTML, PDFs, insert pages, and any extracted protected code expression remain governed by the source register and corpus policy.

## Relationship to Building Code Map

Building Code Map owns location, jurisdiction, authority, and adopted-source resolution. Building Code AST owns faithful representation of the identified base publication and separately sourced amendment patches.

A later integration may supply the applicable jurisdiction and effective date, then select the matching patch set. This module does not perform that selection from an address.

## Non-goals

This layer does not:

- reproduce or replace the adopted IBC;
- infer local amendments outside chapter 51-50 WAC;
- decide which Washington code cycle applies to a permit;
- resolve AHJ boundaries;
- infer deletion or scope from unlabeled official prose;
- apply patches to produce compliance conclusions.
