# NFPA 13 (2019) reviewed table slice

Predecessor: `feature/nfpa13-table-semantics-contract` (PR #79)

Owns:
- one narrowly bounded NFPA 13 table family reviewed against the exact authorized source;
- semantic header/span interpretation only for that reviewed family;
- row/column selection evidence, units, footnotes, qualifications, and unresolved cases;
- precise support claims that distinguish geometry extraction from reviewed lookup semantics.

Does not own:
- broad table interpretation across NFPA 13;
- engineering calculation execution;
- figure or diagram interpretation;
- project compliance or sprinkler design.

Completion:
- private exact-source cases are independently reviewed;
- public fixtures remain synthetic or non-reconstructive;
- every accepted lookup retains its derivation path and source coordinates;
- ambiguous or unsupported rows/headers remain explicit;
- support claims are limited to the reviewed table family.

Successor: `feature/nfpa13-calculation-semantics`.
