from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"expected exactly one match in {path}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> int:
    validator = ROOT / "tools/validate_ibc_2018_corpus.py"
    replace_once(
        validator,
        "from building_code_ast.evidence.io import source_register_from_dict\n",
        "from building_code_ast.evidence import load_source_package\n",
    )
    replace_once(
        validator,
        '    "ibc-2018-source-register.json",\n',
        '    "source-package.json",\n',
    )
    replace_once(
        validator,
        '''    source_register = source_register_from_dict(load(corpus_dir / "ibc-2018-source-register.json"))\n    if source_register.entries[0].sha256 != SOURCE_SHA256:\n        discrepancies.append({"code": "source-register-hash-mismatch"})\n''',
        '''    source_package = load_source_package(corpus_dir / "source-package.json")\n    source_binding = source_package.binding_for_source("source:icc:ibc:2018:pdf:c8f0b755")\n    source_artifact = source_package.artifact(source_binding.artifact_id)\n    if source_artifact.sha256 != SOURCE_SHA256:\n        discrepancies.append({"code": "source-package-hash-mismatch"})\n''',
    )

    ashrae621 = ROOT / "tests/test_ashrae621_2016_document_ast.py"
    replace_once(
        ashrae621,
        '''        self.assertEqual(\n            ASHRAE_62_1_2016_PUBLICATION.correction_set,\n            "incorporated-addenda:ashrae-62.1-2013:a,c,d,e,f,g,h,i,j,k,p,q,r,s;"\n            "correction-layer:unresolved:no-incorporated-correction-layer-established",\n        )\n''',
        '''        self.assertEqual(\n            ASHRAE_62_1_2016_PUBLICATION.addenda_set,\n            "a,c,d,e,f,g,h,i,j,k,p,q,r,s",\n        )\n        self.assertIsNone(ASHRAE_62_1_2016_PUBLICATION.correction_set)\n''',
    )

    ashrae901 = ROOT / "tests/test_ashrae901_2016_document_ast.py"
    replace_once(
        ashrae901,
        '''        self.assertEqual(\n            ASHRAE_90_1_2016_PUBLICATION.addenda_set,\n            "ashrae-90.1-2013:addenda-enumerated-in-90.1-2016-appendix-h",\n        )\n        self.assertEqual(\n            ASHRAE_90_1_2016_PUBLICATION.correction_set,\n            "unresolved:no-incorporated-post-publication-correction-established",\n        )\n''',
        '''        self.assertEqual(\n            ASHRAE_90_1_2016_PUBLICATION.addenda_set,\n            "all addenda to Standard 90.1-2013 enumerated by retained Informative Appendix H",\n        )\n        self.assertIsNone(ASHRAE_90_1_2016_PUBLICATION.correction_set)\n''',
    )

    forbidden = (
        "building_code_ast.evidence.io",
        "ibc-2018-source-register.json",
        "source_register_from_dict",
    )
    validator_text = validator.read_text(encoding="utf-8")
    remaining = [item for item in forbidden if item in validator_text]
    if remaining:
        raise RuntimeError(f"legacy IBC validator dependencies remain: {remaining}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
