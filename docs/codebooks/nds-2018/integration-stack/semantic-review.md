# NDS 2018 semantic review

Predecessor: `feature/nds-2018-table-semantics`.

Owns:
- connecting selected NDS structural nodes to the generic Provision AST and reviewed semantic workflow;
- consuming shared applicability, exception, definition-use, calculation, table-lookup, and review-status contracts when available;
- deterministic parser-versus-reviewed interpretation boundaries, reviewer metadata, and exact source evidence;
- source-safe synthetic fixtures plus private restricted-source review packets;
- measurable semantic coverage without treating generated candidates as approved engineering rules.

Does not own:
- an NDS-only Provision AST fork;
- project-specific member design, compliance, or jurisdiction evaluation;
- claiming every NDS provision is semantically modeled;
- bypassing unresolved structural, definition, reference, equation, or table evidence.

Completion:
- representative NDS prose can enter the generic semantic review workflow with exact evidence;
- shared applicability/exception/calculation contracts are reused or minimally extended source-independently where NDS proves a gap;
- parser candidates and reviewed interpretations remain separate durable states;
- source-safe tests cover accepted, rejected, ambiguous, and unsupported candidates;
- private review artifacts remain outside Git.

Successor: `feature/nds-2018-reviewed-vertical-slices`.