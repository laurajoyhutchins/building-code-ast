# Source counterexample workflow

Status: scope-only stacked PR stub.

Purpose: make retrieval explicitly useful for parser development by supporting deliberate counterexample discovery around known evidence.

Owns retrieval of analogous candidates from a known evidence ID and machine-readable candidate output.

Excludes automatically promoting retrieval hits into gold data or verified AST semantics.

Completion: a parser hypothesis can be challenged with retrieved analogues, a real counterexample can be identified, and the eventual parser regression remains a deliberate source-safe fixture.

Predecessor: `feature/source-hybrid-search`.
Terminal shared retrieval workflow; later publication-specific adoption should branch from landed `main`.
