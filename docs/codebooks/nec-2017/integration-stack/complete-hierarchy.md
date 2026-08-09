# NEC 2017 complete hierarchy

Predecessor: `feature/nec-2017-full-layout-evidence`.

Owns:
- NEC-specific recognition for chapters, articles, parts, sections, nested parenthetical levels, definitions, exceptions, informational notes, and annex hierarchy;
- deterministic publication-native locators and parent/child ownership;
- source-role distinctions needed to keep normative and informative material explicit;
- fail-closed treatment for malformed, ambiguous, or collapsed hierarchy.

Does not own:
- semantic interpretation of provisions;
- table cells, figure content, or other non-prose internals beyond hierarchy anchors;
- definition/reference resolution;
- compliance evaluation.

Completion:
- the complete retained publication can be traversed through deterministic structural locators;
- source spans and parentage round-trip to positioned evidence;
- ambiguous hierarchy remains explicit and measurable;
- synthetic and bounded private replay cover representative hierarchy pathologies.

Successor: `feature/nec-2017-nonprose-structure`.
