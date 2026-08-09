# Source search CLI

Status: scope-only stacked PR stub.

Purpose: expose indexing, lexical search, evidence lookup, page/context navigation, status, and JSON output through the existing `building-code-ast` CLI.

Owns developer-facing command ergonomics and provenance-first output.

Excludes semantic search and a second standalone executable unless later evidence requires one.

Completion: AST work can use source retrieval without direct Python or database access.

Predecessor: `feature/source-context-navigation`.
Sibling dependency before Phase 1 closeout: `feature/source-structural-search`.
