# NFPA 13 (2019) applicability semantics

Predecessor: landed definition graph PR #76.

This PR owns the small publication-neutral applicability/scope vocabulary justified by reviewed NFPA 13 structure. It records structural ownership of applicability evidence without turning that evidence into project-specific applicability, compliance, or engineering conclusions.

## Exact retained source

The bounded review uses the same exact artifact as the landed NFPA definition graph:

- private filename: `nfpa-2019.pdf`
- size: 49,070,148 bytes
- SHA-256: `07c229b70cfdde21c3c67e6918040663c76aec680a0bd8d026392e21e8b81ee5`
- physical PDF pages: 3,853
- NFPA 13 structural extraction range: PDF pages 21 through 513
- media type: `application/pdf`
- encryption: none

The artifact identity was reverified in the review runtime before inspecting applicability evidence. No protected source prose, page image, table, figure, or private generated bundle is committed.

## Implemented contract

`src/building_code_ast/applicability.py` defines `applicability-scopes/0.1.0`.

Each record preserves:

- a structural owner locator;
- the descendant locators governed by that evidence;
- explicit `resolved`, `ambiguous`, or `unsupported` resolution state;
- parser/review method identity;
- independent `unreviewed`, `reviewed`, or `rejected` review state;
- source-stream evidence coordinates with source expression removed from projection output.

Distinct owners cannot silently claim the same descendant, and an owner cannot claim itself. Review status remains orthogonal to resolution state.

## Bounded exact-source review

The exact retained PDF was read using the same NFPA source-stream ordering rules used by the existing extractor: artifact furniture was excluded, retained text-layer lines were ordered by physical page, column, and geometry, and deterministic source offsets were assigned.

A concrete structural applicability family was reviewed on physical PDF page 29:

- structural applicability owner: `3.3.119`
- source-stream evidence span: `[46285, 46360)`
- physical PDF page: 29
- governed direct descendants: `3.3.119.1` through `3.3.119.13`
- descendant count: 13
- resolution state: `resolved`
- review status: `reviewed`
- review method: `private-exact-source-structural-review/0.1.0`

The source states at that owner that the nested definition family has a chapter-specific applicability scope. The reviewed evidence therefore supports assigning the applicability evidence to the `3.3.119` structural owner and its thirteen nested definitions. The public contract needs only locators, state, method, review status, and the exact source-stream coordinates; it does not need the protected source expression.

This is a bounded reviewed semantic case. It establishes that the contract can faithfully represent one real NFPA structural applicability family. It does **not** establish whole-publication applicability coverage or automatic applicability discovery.

## Deliberate exclusions from this review

Broader Chapter 1 application and retroactivity statements were inspected but are not promoted through this structural-ownership contract merely because they contain applicability language. They govern publication-wide subject matter, existing installations, or project/temporal conditions rather than a simple descendant-locator family. Treating those statements as equivalent to nested structural ownership would overclaim the current model.

Likewise, ordinary conditional clauses elsewhere in the publication are not applicability records merely because they contain phrases such as `where`, `when`, or `shall apply`. Conditions, exceptions, and project-specific applicability remain separate semantic problems.

## Verification history

- TDD RED: `65b2ac0eed27482d0ff93a4566dd5409a5ad70fa`.
- prior synthetic GREEN: `2896461d80ee7c488775915667b0455084ce1d18`.
- explicit convergence onto `main` after #76 landed: `a4251637238395b297a498354d12f17cb9d07a6f`.

Synthetic fixtures cover deterministic ordering, nested applicability ownership, explicit ambiguity, source-expression omission, conflicting-owner rejection, self-ownership rejection, and review-state independence.

The bounded exact-source case above closes this PR's private semantic review gate without adding a new source detector.

## Boundaries

This PR does not own:

- automatic applicability discovery;
- Chapter 1 project/temporal applicability modeling;
- exception semantics;
- definition resolution beyond landed #76;
- table, calculation, or figure meaning;
- mapping scope records into Provision AST;
- project-specific applicability, system design, compliance, jurisdiction, adoption, or legal conclusions.

Provision AST remains unchanged in this PR. Any later integration must make its version migration explicit and must be justified by executable evidence rather than resurrecting the retired NFPA descendant ladder.
