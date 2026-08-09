# ACI 318-19 cross-page hierarchy

Predecessor: `feature/aci-318-19-region-classification`.

Owns:
- hierarchy continuation when sections, subsections, tables, commentary, and other structures cross PDF pages;
- parent recovery from publication-native locators without page-local assumptions;
- deterministic continuation identity for Code and Commentary independently;
- explicit diagnostics when cross-page ownership cannot be proven.

Does not own:
- equation or table internals;
- definition/reference resolution;
- Provision AST semantics.

Completion:
- page boundaries do not create duplicate publication-native nodes;
- section/subsection ownership is stable across representative continuation cases;
- Code and Commentary continuation cannot collide;
- private replay exercises representative multi-page structures.

Successor: `feature/aci-318-19-equation-structure`.
