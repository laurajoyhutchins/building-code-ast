# NFPA 13 (2019) definition graph

Predecessor: `feature/nfpa13-reference-graph` (PR #60)

Owns:
- stable NFPA 13 definition identities projected into a source-safe definition graph;
- definition scope/context and explicit definition-use candidate relationships;
- resolved, ambiguous, unresolved, duplicate, and cyclic definition relationship states;
- exact evidence coordinates without copying definition or use-site source text into the graph;
- deterministic graph serialization over normalized definition relationships.

Does not own:
- lexical discovery of definition uses;
- applicability or exception semantics;
- table or calculation meaning;
- broad external-standard resolution beyond the existing NFPA relationship contract;
- amendment, jurisdiction, adoption, compliance, or sprinkler-design conclusions.

Implemented boundary:
- `tools/extract_nfpa13_2019_ast.py` already identifies Chapter 3 structural `definition_entry` nodes; this PR does not add a second definition detector;
- `src/building_code_ast/nfpa13_definition_graph.py` projects normalized definition records and candidate-use relationships downstream of that structural recognition;
- zero candidates remain `unresolved`, one candidate becomes `resolved`, and multiple candidates remain `ambiguous`;
- candidate locators must identify declared definitions; unknown locators fail closed;
- duplicate definition locators fail closed;
- definition-use cycles remain representable;
- public graph output retains evidence start/end coordinates while dropping evidence text.

Verification:
- TDD RED head: `f16f8a584fb149844183c991131fbf8a1261ca64`, where the repository test check failed before the production module existed;
- GREEN implementation head before this documentation update: `ca6bbdea0ff0b65a59f6d41455916115772986f4`, where repository test, verification, and archaeology checks passed;
- synthetic fixtures cover resolved, unresolved, ambiguous, duplicate, unknown-target, deterministic-order, source-text-boundary, and cyclic cases;
- no private source replay is claimed by this implementation increment because it adds no new source recognition rule.

Remaining before this scope is complete:
- bind normalized definition records/use candidates to a bounded private exact-source review set;
- establish reviewed source-backed use candidates without turning lexical matching into authority;
- reconcile the eventual generic issue #5 graph contract when shared primitives are ready.

Successor: `feature/nfpa13-applicability-semantics`.