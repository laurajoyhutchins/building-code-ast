# NDS 2018 hierarchy

Predecessor: `feature/nds-2018-layout-evidence`.

Owns:
- NDS-specific recognition of the 16 numbered chapters and decimal section hierarchy;
- deterministic publication-native locators for nested sections and source-safe fallback locators only where no durable printed locator exists;
- appendix A-N hierarchy and mandatory/non-mandatory source-role distinctions;
- paragraph, list, definition, heading, note, and footnote ownership within the structural tree;
- chapter/appendix opener handling and bookmark evidence without treating bookmarks as an oracle.

Does not own:
- equation/table/figure internal structure beyond preserving their regions for the next descendant;
- definition semantic resolution;
- reference graph resolution;
- Provision AST interpretation.

Completion:
- representative body and appendix hierarchies pass generic Document AST validation;
- deterministic IDs are independent of parse order and PDF block indices;
- the invalid `12.6 Multiple Fasteners` bookmark cannot repair or invent hierarchy;
- source roles and unsupported hierarchy ambiguities remain explicit diagnostics;
- private exact-source replay covers representative chapters and appendices.

Successor: `feature/nds-2018-nonprose-structure`.