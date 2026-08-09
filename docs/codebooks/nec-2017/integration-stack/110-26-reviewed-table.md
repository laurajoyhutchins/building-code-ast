# NEC 110.26 reviewed table slice

Predecessor: `feature/nec-110-26-table-evidence` / PR #61.
Restack note: substantive implementation must follow #61 onto then-current `main` before landing.

Owns:
- one exact-source-reviewed semantic interpretation of the 110.26(A)(1) table sufficient to expose real header, span, condition-description, unit, and cell-role requirements;
- explicit mapping from structural table evidence to reviewed semantic roles;
- ambiguity and unsupported states where the source relationship cannot be represented honestly;
- source-safe synthetic fixtures plus private review evidence.

Does not own:
- a generic table lookup model before this reviewed case proves what is required;
- broad NEC table semantics;
- project-specific working-space evaluation;
- flattening a derived threshold into an unexplained number.

Completion:
- the reviewed case has exact provenance from source geometry through approved semantic roles;
- parser output and reviewed interpretation remain distinct;
- unresolved source relationships remain visible;
- no reconstructive NEC table content enters Git.

Successor: `feature/table-lookup-semantic-contract`.
