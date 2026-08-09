# Publication-neutral appendix, equation, and figure structure

Predecessor: `feature/nds-2018-source-registration`.

Owns:
- extending the shared Document AST only where neutral structure is genuinely missing;
- first-class appendix, equation, and figure node types with deterministic identity and ordinary source-span invariants;
- JSON Schema/runtime validation and synthetic source-safe fixtures for the new node kinds;
- compatibility/versioning decisions required by the additive structural vocabulary.

Does not own:
- NDS recognition rules;
- mathematical parsing or equation execution;
- figure semantics;
- table semantics or publication-specific appendix policy.

Completion:
- appendix, equation, and figure are representable without hiding them in headings or NDS-only metadata;
- deterministic IDs, serialization, strict deserialization, containment, and span round-trip are covered by generic tests;
- existing source-family adapters remain compatible or receive an explicit documented migration;
- no NDS source expression is required by public tests.

Successor: `feature/nds-2018-layout-evidence`.