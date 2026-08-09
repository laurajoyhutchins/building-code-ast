# IBC 2018 reviewed table slice

Predecessor: `feature/ibc-table-semantics-contract`.

Owns:
- one bounded, coherent IBC table family mapped into the generic table semantic contract;
- human-reviewed headers, units, notes, applicability, lookup behavior, and source evidence;
- explicit unsupported/ambiguous cells or relationships.

Does not own:
- broad conversion of all 215 IBC tables;
- equation semantics beyond referenced inputs;
- project-specific compliance evaluation.

Completion:
- selected family is source-safe and representative;
- reviewed cases distinguish parser output from approved interpretation;
- source spans and table coordinates round-trip;
- support claims remain limited to the reviewed slice.

Successor: `feature/ibc-calculation-semantics`.
