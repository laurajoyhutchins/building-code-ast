# NEC hierarchy oracle parser implementation plan

> **Execution note:** Follow test-driven development. Each behavior begins with a failing test, then receives the minimum implementation needed to pass.

**Goal:** Make the NEC PDF parser infer a provenance-backed publication hierarchy and use Laura's existing NEC 2017 hierarchy as a local conformance oracle.

**Architecture:** Add a source-free hierarchy module that canonicalizes NEC locators, nests classified PDF nodes, and compares inferred structure with a locally supplied clause CSV. Integrate it into ArticleSeed construction and flatten nested nodes only at the semantic-consumer boundary.

**Stack:** Python 3.12, standard library, existing immutable document AST, pytest/unittest discovery, GitHub Actions.

## Task 1: Pin locator and parent semantics

**Files:**
- Create: `tests/test_nec_hierarchy.py`
- Create: `src/building_code_ast/ingest/nec_hierarchy.py`

1. Add failing tests for canonical locator parsing, parent derivation, depth, and invalid locators.
2. Run the focused test and confirm failure because the module/API does not exist.
3. Implement immutable locator helpers with no NEC corpus dependency.
4. Run the focused test and confirm it passes.

## Task 2: Build the structural stack

**Files:**
- Modify: `tests/test_nec_hierarchy.py`
- Modify: `src/building_code_ast/ingest/nec_hierarchy.py`

1. Add failing synthetic tests for Part → Section → `(A)` → `(1)` → `(a)` nesting.
2. Add sibling-reset and repeated deeper marker tests.
3. Add tests that notes, exceptions, prose, and unsupported nodes attach to the deepest open owner.
4. Add tests that structural parent spans expand through their final descendant.
5. Implement the minimal stack builder and explicit ambiguity diagnostics.
6. Run focused tests after each behavior.

## Task 3: Integrate hierarchy into ArticleSeed ingestion

**Files:**
- Modify: `tests/test_nec2017_ingest.py`
- Modify: `src/building_code_ast/ingest/nec2017.py`
- Modify: `src/building_code_ast/ingest/__init__.py`

1. Add failing ingestion tests asserting full NEC locators and nested children.
2. Preserve block source locators and PDF provenance on nonstructural nodes.
3. Improve Part and structural-heading classification metadata.
4. Call the hierarchy builder before constructing the Article node.
5. Preserve existing source maps and diagnostics.
6. Run ingestion and full unit suites.

## Task 4: Preserve semantic-review compatibility

**Files:**
- Modify: `tests/test_nec_semantic_models.py` or add a focused seed-view test.
- Modify: `src/building_code_ast/nec/seed.py`

1. Add a failing test showing nested Article children are exposed to existing semantic parsers in source preorder.
2. Implement recursive preorder flattening at `article_seed_view`.
3. Confirm existing definition and section semantic tests remain green.

## Task 5: Add the hierarchy oracle and mismatch report

**Files:**
- Create: `tests/test_nec_hierarchy_oracle.py`
- Modify: `src/building_code_ast/ingest/nec_hierarchy.py`

1. Add failing tests for loading `clause_id,clause_title,parent` CSV data.
2. Add failing tests for exact match and for missing, unexpected, duplicate, parent, title, depth, and order mismatches.
3. Implement immutable oracle records, inferred-record flattening, comparison, summary counts, and JSON serialization.
4. Ensure comparison never mutates or repairs the AST.
5. Run focused tests and the full suite.

## Task 6: Add a local conformance command

**Files:**
- Create: `scripts/check_nec_2017_hierarchy.py`
- Create: `tests/test_nec_hierarchy_cli.py`
- Create: `docs/how-to/validate-nec-hierarchy.md`
- Modify: `docs/README.md`
- Modify: `README.md`

1. Add a failing CLI test using synthetic ArticleSeed and oracle files.
2. Implement arguments for ArticleSeed JSON files, oracle CSV, optional report path, and strict exit status.
3. Document that the junk-drawer oracle is a local development input and must not be published here.
4. Document report interpretation and private-corpus boundaries.
5. Run CLI tests and documentation checks.

## Task 7: Validate against the private 2017 corpus

**Private inputs:**
- Existing NEC 2017 ArticleSeed archive in Google Drive.
- Existing `nec/csv/nec-2017-clauses.csv` in `laurajoyhutchins/junk-drawer`.

1. Materialize the private ArticleSeed outputs locally.
2. Materialize the reference CSV locally without committing it.
3. Run the conformance command for converted Articles 90, 100, and 110.
4. Classify mismatch families and fix parser rules with new synthetic regressions.
5. Save the private conformance report beside the private seed artifacts, not in GitHub.

## Task 8: Final verification and publication

1. Run the complete repository test command.
2. Run Python compilation and schema parsing checks used by CI.
3. Scan the branch diff for NEC source prose, PDFs, page images, source hashes, and oracle data.
4. Compare the branch with PR #14's exact head and verify only the intended source-free files changed.
5. Open a stacked draft PR targeting `agent/nec-definition-section-semantics`.
6. Confirm exact-head GitHub Actions success before reporting completion.