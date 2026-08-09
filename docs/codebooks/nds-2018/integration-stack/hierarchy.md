# NDS 2018 hierarchy

Predecessor: merged PR #105 `feature/nds-2018-layout-evidence`.

Owns:
- NDS chapter opener recognition without promoting chapter-contents locators as body sections;
- decimal section/subsection hierarchy using publication-native locators;
- explicit appendix nodes and mandatory/non-mandatory source roles when the appendix locator is present in source evidence;
- structural definition entries under evidence-backed Definition/Definitions owners;
- ordinary paragraph/list ownership and root-level references transition;
- exact `DocumentSourceArtifact` identity inherited from registered NDS layout evidence;
- deterministic coordinate/content fallback locators for unnumbered structural regions;
- explicit diagnostics when a structural locator cannot be recovered safely.

Does not own:
- equation, table, figure, or graphical engineering structure beyond explicit deferred/unsupported retention;
- definition resolution or reference graph semantics;
- Provision AST interpretation;
- whole-document structural completeness claims.

Completion:
- representative synthetic chapter, nested-section, definition, appendix-role, list, references, and unresolved-locator cases validate through the generic Document AST contract;
- publication-native locators determine durable IDs where available;
- chapter opener contents cannot create duplicate body sections;
- malformed or extraction-damaged appendix locators remain unsupported rather than inferred from sequence;
- private exact-source replay confirms the recognized grammar before any completeness claim.

Successor: `feature/nds-2018-nonprose-structure`.
