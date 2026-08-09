# NDS 2018 reviewed vertical slices

Predecessor: `feature/nds-2018-semantic-review`.

Owns:
- proving end-to-end reviewed NDS semantics across contrasting source families;
- at least one equation-backed rule family, one table/lookup-backed family, and one prose/definition/reference-heavy family selected from measured source evidence;
- exact-source trace from retained artifact through Document AST, graph/semantic dependencies, Provision AST candidate, and reviewed interpretation;
- explicit support/unsupported boundaries for each demonstrated family.

Does not own:
- choosing rule families from memory before structural measurement and review value justify them;
- reviewing every NDS provision;
- project-specific compliance, member selection, or design conclusions;
- hiding unresolved dependencies merely to complete a demonstration.

Completion:
- all selected families have independently reviewable exact-evidence traces;
- at least one selected family exercises reviewed equation semantics and one exercises reviewed table semantics;
- parser output and approved interpretation remain distinct;
- unresolved/unsupported paths fail closed and are represented in the review record;
- public Git contains only source-safe fixtures, metadata, and aggregate review evidence.

Successor: `feature/nds-2018-integration-closeout`.