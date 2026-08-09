# NFPA 13 (2019) semantic review workflow

Predecessor: `feature/nfpa13-provision-adapter` (PR #82)

Owns:
- NFPA 13 participation in the generic issue #4 semantic review workflow;
- reviewer identity/date metadata and parser-versus-approved interpretation state;
- deterministic fixture generation and diffing for source-safe expectations;
- local-only handling of exact restricted-source evidence;
- structural mismatch, unsupported-node, and source-span reporting for NFPA semantic candidates.

Does not own:
- new semantic vocabulary;
- automatic acceptance of generated candidates;
- publication of licensed source text;
- whole-edition semantic completeness claims.

Completion:
- contributors can review NFPA cases without hand-editing generated spans;
- private exact-source review and public non-reconstructive fixtures share one deterministic workflow;
- rejected and unsupported candidates remain durable review outcomes;
- review reports separate reproducibility from semantic correctness.

Successor: `feature/nfpa13-semantic-corpus-expansion`.
