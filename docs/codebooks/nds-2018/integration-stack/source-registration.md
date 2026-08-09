# NDS 2018 source registration

Predecessor: merged PR #51 `nds-2018/source-profile`.

Owns:
- registering the exact retained NDS 2018 artifact through the existing publication-neutral source register;
- binding publication state, exact SHA-256, access/rights state, and `DocumentSourceArtifact` identity;
- preserving unresolved printing and correction/errata state explicitly;
- source-safe tests proving exact-byte identity is not replaced by filename, title, edition, or page count.

Does not own:
- PDF layout extraction or Document AST parsing;
- an NDS-only registry;
- resolving unknown printing or correction state from another nominally identical PDF;
- semantic interpretation.

Completion:
- the retained `581353dab836de933546bc93b8265674dabb08d1073da04d660cf894250b48b4` artifact is representable by the existing source-registration contract;
- rights/access and publication-state unknowns round-trip without inference;
- generic validation passes with source-safe tests;
- no protected NDS expression enters Git.

Successor: `feature/document-ast-equation-figure-appendix`.