# NFPA 13 (2019) reviewed vertical slice

Predecessor: `feature/nfpa13-semantic-corpus-expansion` (PR #84)

Owns:
- one narrowly bounded NFPA 13 rule family carried end to end from exact source evidence through reviewed semantic representation;
- representative use of definitions, applicability, conditions/exceptions, references, and a table or calculation dependency where genuinely required;
- a human-readable provenance trace from reviewed semantic nodes back to exact source evidence;
- explicit unsupported boundaries and review decisions for the selected family.

Does not own:
- general sprinkler-system design;
- hydraulic design conclusions;
- project-specific compliance, adoption, jurisdiction, AHJ, permit, or legal conclusions;
- whole-edition semantic completeness.

Completion:
- source identity and redistribution boundary are verified before review;
- every derived node has an exact evidence/provenance trace;
- required issue #3, #4, and #5 capabilities are exercised by the selected family;
- parser output, reviewed interpretation, and unsupported cases are reported separately;
- the demonstration stops at reviewed rule representation.

Successor: `feature/nfpa13-integration-closeout`.
