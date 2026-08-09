# ACI 318-19 semantic review

Predecessor: `feature/aci-318-19-provision-semantics`.

Owns:
- ACI participation in the generic semantic review workflow;
- explicit separation of parser output, reviewed semantic interpretation, and approved semantic artifacts;
- commentary as optional explanatory/review evidence distinct from normative rule provenance;
- reviewer status, exact evidence spans, ambiguity recording, and rejection of lossy parses.

Does not own:
- automatic approval of parser output;
- commentary-driven rewriting of normative text;
- claims of full semantic coverage;
- project design or compliance decisions.

Completion:
- reviewed ACI semantic artifacts retain exact normative provenance and independent review state;
- commentary evidence is separately identified;
- parser disagreement and unsupported cases remain visible;
- review outcomes serialize deterministically without protected corpus material.

Successor: `feature/aci-318-19-reviewed-vertical-slices`.
