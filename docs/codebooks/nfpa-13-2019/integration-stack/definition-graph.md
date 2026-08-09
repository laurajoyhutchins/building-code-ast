# NFPA 13 (2019) definition graph

Predecessor: `feature/nfpa13-reference-graph` (PR #60)

Owns:
- stable NFPA 13 definition identities projected into the provenance/reference graph;
- definition scope/context and definition-use relationships;
- resolved, ambiguous, unresolved, duplicate, and cyclic definition relationships;
- exact source-evidence retention without copying definition prose into use sites;
- deterministic graph serialization over reviewed definition relationships.

Does not own:
- applicability or exception semantics;
- table or calculation meaning;
- broad external-standard resolution beyond the existing NFPA relationship contract;
- amendment, jurisdiction, adoption, compliance, or sprinkler-design conclusions.

Completion:
- synthetic fixtures cover shared, missing, ambiguous, duplicate, and cyclic definition cases;
- private exact-source review covers a bounded representative NFPA definition/use set;
- definition nodes and use edges preserve publication identity and exact source spans;
- unsupported scope questions remain explicit rather than guessed;
- behavior coordinates with issue #5 and Provision AST definition-use work in issue #3.

Successor: `feature/nfpa13-applicability-semantics`.
