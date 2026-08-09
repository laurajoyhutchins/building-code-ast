# IBC 2018 semantic review workflow

Predecessor: `feature/ibc-external-reference-graph`.

Owns:
- IBC participation in the generic reviewed-fixture workflow from issue #4;
- reviewer identity/date, parser output, approved interpretation, dispute/rejection notes, and deterministic regeneration;
- conversion of the existing semantic pilot into reviewable gold cases where publication-safe.

Does not own:
- mass review of the entire IBC queue;
- changing semantic vocabulary defined by predecessor PRs;
- compliance evaluation.

Completion:
- contributors can add/review IBC fixtures without hand-editing generated spans;
- parser output and approved interpretation remain distinct;
- source-span and structural mismatches are reported deterministically;
- restricted source handling remains local-only.

Successor: `feature/ibc-semantic-corpus-expansion`.
