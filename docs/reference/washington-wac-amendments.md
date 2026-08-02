# Washington WAC Jurisdictional Amendment Patches

## Purpose

The Washington amendment layer represents chapter 51-50 WAC provisions as jurisdictional overlays on an identified International Building Code publication state. It does not copy the adopted IBC, determine which authority applies to a project, or evaluate compliance.

Washington adopts the 2021 IBC by reference in chapter 51-50 WAC and publishes state amendments as separately cited WAC sections. The patch model preserves that relationship explicitly:

```text
identified IBC publication state
  + effective Washington WAC patches
  -> reviewable jurisdictional overlay
```

## Patch contract `0.1.0`

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

`add` and `replace` require replacement text. `delete` and `reserve` prohibit replacement text. `scope` requires a scope statement and prohibits replacement text.

The model does not infer an operation from general explanatory prose. Unknown directives remain source-located diagnostics and unsupported regions.

## Effective intervals

Patch intervals are half-open:

- a patch is active on `effective_from`;
- it remains active before `effective_to`;
- it is inactive on `effective_to` itself;
- a null `effective_to` means the patch has no recorded end date.

This supports non-overlapping revisions where a later patch begins exactly when an earlier patch ends.

## Amendment-set validation

`AmendmentSet` requires every patch to share one jurisdiction and one base publication state. It orders patches by effective date, source sequence, WAC citation, and locator.

Overlapping records with the same legal effect are permitted as reaffirmations or duplicate-source evidence. Overlapping scope records may coexist with an add or replacement affecting the same locator. Other overlapping incompatible effects fail closed.

`active_for(locator, date)` returns the ordered patches active for one base locator on one date. It does not apply those patches to an AST or decide how multiple provisions interact semantically.

## Bounded Washington HTML adapter

`WashingtonWacHtmlAdapter` consumes a registered UTF-8 `text/html` source with evidence role `jurisdictional_law`. It must be invoked through `run_evidence_adapter`, so source role, media type, and exact-byte SHA-256 are verified before parsing.

The public adapter recognizes bounded section blocks shaped like:

```html
<section>
  <h3>WAC 51-50-0107</h3>
  <p>Section 107.3 is added.</p>
  <p>...</p>
</section>
```

It recognizes explicit added, replaced, deleted, reserved, and scoped directives. An optional base-locator oracle rejects amendments whose target cannot be resolved in the identified base AST.

The official Washington site does not necessarily use this simplified public-fixture markup at every endpoint. A production acquisition layer may normalize official HTML into these bounded section blocks, but it must preserve the registered source digest and source anchors.

## Official-source boundary

Chapter 51-50 WAC identifies the adopted IBC edition and enumerates state amendments and reserved sections as individual WAC provisions. Public repository fixtures use invented text. Official HTML, PDFs, insert pages, and any extracted protected code expression remain governed by the source register and corpus policy.

## Relationship to Building Code Map

Building Code Map owns location, jurisdiction, authority, and adopted-source resolution. Building Code AST owns faithful representation of the identified base publication and separately sourced amendment patches.

A later integration may supply the applicable jurisdiction and effective date, then select the matching patch set. This module does not perform that selection from an address.

## Non-goals

This layer does not:

- reproduce or replace the adopted IBC;
- infer local amendments outside chapter 51-50 WAC;
- decide which Washington code cycle applies to a permit;
- resolve AHJ boundaries;
- interpret legal effect beyond the explicit patch operation;
- apply patches to produce compliance conclusions.
