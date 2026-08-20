from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

ADAPTER_TESTS = (
    "tests/test_evidence_review_edge_cases.py",
    "tests/test_evidence_review_regressions.py",
    "tests/test_evidence_second_review.py",
    "tests/test_icc_development.py",
    "tests/test_icc_errata.py",
    "tests/test_icc_official_development.py",
    "tests/test_washington_amendments.py",
    "tests/test_washington_official_html.py",
)

ASHRAE_TESTS = (
    "tests/test_ashrae621_2016_document_ast.py",
    "tests/test_ashrae901_2016_document_ast.py",
)


def migrate_adapter_test(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "from provenance_fixtures import bound_source" not in text:
        marker = "import unittest\n"
        if marker not in text:
            raise RuntimeError(f"missing unittest import in {path}")
        text = text.replace(marker, marker + "\nfrom provenance_fixtures import bound_source\n", 1)

    text = text.replace("    PublicationIdentity,\n", "")
    text = text.replace("    SourceRegisterEntry,\n", "")
    text = text.replace("    publication_state_id,\n", "")

    evidence_import = "from building_code_ast.evidence import (\n"
    if evidence_import in text:
        if "    BoundArtifact,\n" not in text:
            text = text.replace(evidence_import, evidence_import + "    BoundArtifact,\n", 1)
        if "    PublicationState,\n" not in text:
            text = text.replace(evidence_import, evidence_import + "    PublicationState,\n", 1)
    else:
        raise RuntimeError(f"missing evidence import block in {path}")

    text = text.replace("PublicationIdentity(", "PublicationState(")
    text = text.replace("SourceRegisterEntry(", "bound_source(")
    text = text.replace("SourceRegisterEntry", "BoundArtifact")
    text = re.sub(
        r"publication_state_id\(([A-Za-z_][A-Za-z0-9_\.]*)\)",
        r"\1.publication_id",
        text,
    )

    leftovers = ("PublicationIdentity", "SourceRegisterEntry", "publication_state_id(")
    remaining = [token for token in leftovers if token in text]
    if remaining:
        raise RuntimeError(f"unmigrated tokens in {path}: {remaining}")
    path.write_text(text, encoding="utf-8")


def migrate_ashrae_test(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = text.replace("from building_code_ast.evidence.model import publication_state_id\n", "")
    text = re.sub(
        r"publication_state_id\(([A-Za-z_][A-Za-z0-9_\.]*)\)",
        r"\1.publication_id",
        text,
    )
    if "publication_state_id" in text:
        raise RuntimeError(f"unmigrated publication_state_id in {path}")
    path.write_text(text, encoding="utf-8")


def migrate_ibc_test(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "from building_code_ast.evidence import source_register_from_dict\n",
        "from building_code_ast.evidence import load_source_package\n",
    )
    pattern = re.compile(
        r"    def test_source_register_round_trips_and_is_restricted\(self\) -> None:\n.*?(?=    def test_printed_page_mapping)",
        re.DOTALL,
    )
    replacement = '''    def test_source_package_is_canonical_and_restricted(self) -> None:\n        package = load_source_package(CORPUS / "source-package.json")\n        binding = package.binding_for_source("source:icc:ibc:2018:pdf:c8f0b755")\n        artifact = package.artifact(binding.artifact_id)\n\n        self.assertEqual(package.package_id, "ibc-2018")\n        self.assertEqual(artifact.sha256, SOURCE_SHA256)\n        self.assertEqual(artifact.access_scope.value, "private_local")\n        self.assertEqual(artifact.rights_status.value, "uncertain_restricted")\n        self.assertIsNotNone(artifact.rights_note)\n        self.assertEqual(binding.evidence_role.value, "normative_text")\n\n'''
    text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise RuntimeError("IBC legacy source-register test was not found exactly once")
    if "source_register_from_dict" in text or "ibc-2018-source-register.json" in text:
        raise RuntimeError("IBC test still references legacy source register")
    path.write_text(text, encoding="utf-8")


def main() -> int:
    for relative in ADAPTER_TESTS:
        migrate_adapter_test(ROOT / relative)
    for relative in ASHRAE_TESTS:
        migrate_ashrae_test(ROOT / relative)
    migrate_ibc_test(ROOT / "tests/test_ibc2018_corpus.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
