# NFPA 13 (2019) integration closeout

Predecessor: `feature/nfpa13-reviewed-vertical-slice` (PR #85)

Owns:
- final NFPA 13 integration validation across source identity, Document AST, Provision AST, provenance/reference graph, semantic review, and reviewed vertical-slice evidence;
- precise support-stage reporting rather than a single `supported: true` claim;
- documentation of accepted, unsupported, unresolved, and deliberately out-of-scope structures;
- deletion of superseded NFPA-only semantic paths after replacement verification;
- durable LORE/Deciduous knowledge only for integration boundaries that are actually proven and merged.

Does not own:
- new semantic feature families;
- whole-edition semantic completeness merely because the integration stack landed;
- figure/diagram interpretation without separate reviewed contracts;
- geocoding, adoption, jurisdiction, AHJ, permit context, sprinkler design, hydraulic conclusions, project compliance, or legal advice.

Completion:
- exact-head repository checks and required private exact-source verification pass for the final claimed support boundaries;
- support reporting distinguishes source opening, hierarchy validation, reference/definition resolution, semantic generation, human review, table/calculation support, and reviewed rule-family coverage;
- obsolete NFPA semantic scaffolding is removed only after its replacement is verified;
- remaining unsupported structures are documented plainly;
- final documentation states what downstream callers may and may not rely on.

Successor: none. Later NFPA 13 work should be incremental reviewed coverage or evidence improvement rather than integration plumbing.
