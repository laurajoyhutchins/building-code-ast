# Source hybrid search

Status: scope-only stacked PR stub.

Purpose: combine lexical, semantic, and metadata-constrained retrieval without collapsing their scores into evidentiary confidence.

Owns simple rank fusion and separate lexical, semantic, fusion, and rank metadata.

Excludes learned ranking, parser confidence, and semantic approval.

Completion: exact identifiers still favor lexical evidence while conceptual queries can benefit from semantic candidates.

Predecessor: `feature/source-semantic-index`.
Successor: `feature/source-counterexample-workflow`.
