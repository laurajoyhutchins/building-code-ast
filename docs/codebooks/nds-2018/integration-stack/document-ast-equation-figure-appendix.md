# NDS-required neutral non-prose AST compatibility

Predecessor: `feature/nds-2018-source-registration`.

Exact-base observation: the shared Document AST already contains first-class `equation`, `figure`, and `graphical_region` nodes. This scope must not duplicate them.

Owns:
- verifying that the existing equation, figure, graphical-region, table, note, footnote, and unsupported primitives satisfy the NDS structural contract;
- deciding the smallest publication-neutral representation for appendices;
- reusing existing chapter/heading plus source-role metadata when that preserves appendix identity and validation honestly;
- adding a first-class neutral appendix node only if NDS demonstrates a source-independent representation gap;
- any generic schema/runtime compatibility tests required by that appendix decision.

Does not own:
- NDS recognition rules;
- duplicate equation or figure node types;
- mathematical parsing or equation execution;
- figure semantics;
- table semantics.

Completion:
- NDS appendices can be represented without ad hoc NDS-only identity fields or semantic loss;
- existing equation/figure primitives are reused rather than re-created;
- any generic model change has source-independent meaning and passes deterministic identity, serialization, validation, and source-safe tests;
- no NDS source expression is required by public tests.

Successor: `feature/nds-2018-layout-evidence`.