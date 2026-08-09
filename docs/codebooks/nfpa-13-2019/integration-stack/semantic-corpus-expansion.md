# NFPA 13 (2019) semantic corpus expansion

Predecessor: `feature/nfpa13-semantic-review-workflow` (PR #83)

Owns:
- deliberate expansion of reviewed NFPA semantic coverage across supported clause shapes;
- corpus-level measurement of accepted, rejected, unsupported, ambiguous, and source-span-mismatch outcomes;
- representative definition, applicability, exception, reference, table, and calculation dependencies;
- publication-safe public expectations paired with richer local exact-source review evidence.

Does not own:
- new semantic vocabulary;
- a requirement to review every extracted NFPA clause;
- automatic promotion from generated output to reviewed support;
- whole-edition compliance or design conclusions.

Completion:
- review coverage is broad enough to exercise every NFPA semantic family claimed by predecessors;
- metrics remain stratified by semantic family and review state rather than one supported boolean;
- unsupported structures remain visible in corpus reporting;
- deterministic regeneration reproduces the reviewed public expectations without licensed source text.

Successor: `feature/nfpa13-reviewed-vertical-slice`.
