from __future__ import annotations

import json
from pathlib import Path
import unittest

from building_code_ast.evidence.source_packages import SOURCE_PACKAGE_VERSION, build_source_index, load_source_package, source_package_from_dict

ROOT = Path(__file__).resolve().parents[1]
CORPORA = ROOT / "corpora"
EXPECTED_PACKAGES = {"aci-318-19", "aisc-scm-15", "asce-7-22", "ashrae-62.1-2016", "ashrae-90.1-2016", "ibc-2018", "nds-2018", "nec-2017", "nfpa-13-2019", "tms-402-602-16"}


class ProvenanceStranglerCutoverTests(unittest.TestCase):
    def test_canonical_source_packages_are_the_only_committed_source_authority(self) -> None:
        packages = {path.parent.name: path for path in CORPORA.glob("*/source-package.json")}
        self.assertEqual(set(packages), EXPECTED_PACKAGES)
        self.assertEqual(list(CORPORA.glob("**/*-source-register.json")), [])
        self.assertFalse((CORPORA / "source-object-catalog.json").exists())
        for corpus, path in sorted(packages.items()):
            with self.subTest(corpus=corpus):
                package = load_source_package(path)
                self.assertEqual(package.version, SOURCE_PACKAGE_VERSION)
                self.assertEqual(source_package_from_dict(json.loads(path.read_text(encoding="utf-8"))).to_dict(), package.to_dict())

    def test_source_index_is_a_deterministic_projection_of_packages(self) -> None:
        packages = [load_source_package(path) for path in sorted(CORPORA.glob("*/source-package.json"))]
        self.assertEqual(json.loads((CORPORA / "source-index.json").read_text(encoding="utf-8")), build_source_index(packages))

    def test_legacy_authority_is_deleted(self) -> None:
        evidence = ROOT / "src" / "building_code_ast" / "evidence"
        for name in ("io.py", "source_objects.py", "source_object_hydration.py"):
            self.assertFalse((evidence / name).exists(), name)
        model_text = (evidence / "model.py").read_text(encoding="utf-8")
        self.assertNotIn("SourceRegister", model_text)
        self.assertNotIn("PublicationIdentity", model_text)


if __name__ == "__main__":
    unittest.main()
