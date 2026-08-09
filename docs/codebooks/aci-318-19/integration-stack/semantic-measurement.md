# ACI 318-19 semantic measurement

Predecessor: `feature/aci-318-19-reviewed-vertical-slices`.

Owns:
- whole-publication measurement of normative semantic candidates, parser-supported cases, reviewed cases, unsupported cases, and ambiguities;
- separate counts for equation-backed, table-backed, definition/reference-heavy, conditional, exception, and numeric-comparison provision families;
- explicit distinction between structural coverage, parsed semantic coverage, and reviewed semantic coverage;
- separate commentary measurements that never contribute to normative requirement denominators.

Does not own:
- semantic parser changes merely to improve percentages;
- automatic review or approval;
- project compliance conclusions.

Completion:
- every semantic support claim has a reproducible denominator and producer identity;
- reviewed coverage is reported separately from automatically parsed coverage;
- unsupported semantic families are enumerated;
- repeated exact-source measurement runs are deterministic and source-safe.

Successor: `feature/aci-318-19-integration-closeout`.
