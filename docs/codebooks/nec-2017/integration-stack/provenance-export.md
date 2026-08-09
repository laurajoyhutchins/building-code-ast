# NEC 2017 provenance export

Predecessor: `feature/nec-2017-semantic-coverage-closeout`.

Owns:
- deterministic source-safe export of the integrated NEC structural, graph, semantic-support, and review-state indexes;
- human-readable and machine-readable traces from accepted semantic nodes to Document AST, graph edges, table/calculation derivations, exact artifact identity, and review metadata;
- non-reconstructive receipts and manifests suitable for downstream consumers and regression verification;
- explicit capability/limitation metadata so exported status cannot be mistaken for project compliance.

Does not own:
- redistribution of NEC prose, tables, images, or private generated ASTs;
- a compliance evaluator;
- new semantic interpretation;
- hiding unsupported or rejected states from exports.

Completion:
- every accepted semantic node has a complete provenance trace;
- terminal rejected/ambiguous/unsupported states are exported as status without protected expression;
- export identity is deterministic for the exact source/compiler/review state;
- downstream consumers can distinguish generated, reviewed, structural, and source authority layers.

Successor: `feature/nec-2017-integration-closeout`.
