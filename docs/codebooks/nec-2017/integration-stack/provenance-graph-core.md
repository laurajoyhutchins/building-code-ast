# Publication-neutral provenance graph core

Status: active implementation gate.

Canonical roadmap: #219.

## Evidence boundary

This shared core generalizes behavior already demonstrated by the merged IBC 2018 reference/definition graphs and the active NFPA 13 reference/definition graphs. It must not acquire capabilities merely because a later publication might need them.

Common behavior proven by those concrete lanes:

- graph identity is scoped to exact publication/artifact state;
- source-family node and relationship identities remain available as opaque provenance keys;
- resolved, unresolved, ambiguous, and explicitly nonexistent relationships remain distinct;
- external targets retain their own publication identity instead of collapsing into the current publication;
- source evidence is carried as coordinates/hashes/record identities without source expression;
- stable IDs and serialization do not depend on caller order;
- cycles are graph traversal facts over resolved internal edges, not a replacement resolution state;
- missing/ambiguous relationships remain explicit diagnostics rather than disappearing.

## Owns

A small versioned generic graph contract for normalized source-family graph observations:

- publication identity;
- stable deterministic node and edge IDs;
- source-family opaque keys and source-record identities;
- internal and external node identity;
- resolved, unresolved, ambiguous, and nonexistent relationship states;
- source-safe evidence links;
- deterministic unresolved/ambiguous/nonexistent and cycle diagnostics;
- canonical deterministic JSON serialization.

## Excludes

- NEC-specific reference discovery;
- lexical definition-use discovery;
- semantic applicability or exception inference;
- amendment consolidation or patch application;
- destructive rewriting of Document AST or Provision AST;
- compliance/project evaluation;
- protected source expression.

Issue #5 still owns later amendment-aware consolidation. This PR establishes only the graph primitives already justified by concrete IBC/NFPA behavior.

## Completion evidence

Synthetic tests must cover deterministic identity/serialization, resolved and external edges, missing and ambiguous targets, a reference cycle, source-safe evidence preservation, and fail-closed identity/state validation.

The source-family graphs remain valid upstream evidence. Adoption by an individual publication can happen non-destructively after this core lands.
