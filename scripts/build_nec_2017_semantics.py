#!/usr/bin/env python3
"""Build private NEC 2017 definition and section-review JSON from ArticleSeed files."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any

from building_code_ast.nec import (
    DEFINITION_INDEX_VERSION,
    LANGUAGE_PROFILE_VERSION,
    SECTION_REVIEW_VERSION,
    build_definition_index,
    build_section_review,
    derive_language_profile,
)
from building_code_ast.nec.seed import article_seed_view


BUNDLE_VERSION = "0.1.0"
SECTION_LOCATORS = ("110.2", "110.3", "110.14", "110.16", "110.26")
KNOWN_OUTPUT_FILES = frozenset(
    {
        "manifest.json",
        "definitions-article-100.json",
        "language-policy-90.5.json",
        *(f"section-{locator}.json" for locator in SECTION_LOCATORS),
    }
)


def _load_json(path: Path) -> Mapping[str, Any]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"JSON root must be an object: {source.name}")
    return payload


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def prepare_output_dir(output_dir: Path, *, force: bool) -> None:
    output = Path(output_dir)
    if output.exists() and not output.is_dir():
        raise NotADirectoryError(output)
    if not output.exists():
        output.mkdir(parents=True, exist_ok=False)
        return

    children = tuple(output.iterdir())
    if not children:
        return
    if not force:
        raise FileExistsError(
            f"output directory is not empty: {output}; pass --force to replace it"
        )
    unexpected = [
        child.name
        for child in children
        if not child.is_file() or child.name not in KNOWN_OUTPUT_FILES
    ]
    if unexpected:
        raise FileExistsError(
            "output directory contains unexpected entries and will not be deleted: "
            + ", ".join(sorted(unexpected))
        )
    for child in children:
        child.unlink()


def _source_identity(payload: Mapping[str, Any], article: str) -> tuple[str, str]:
    view = article_seed_view(payload, expected_article=article)
    return view.source_artifact.artifact_id, view.source_artifact.edition_id


def write_outputs(
    article_90_path: Path,
    article_100_path: Path,
    article_110_path: Path,
    output_dir: Path,
    *,
    force: bool,
) -> tuple[Path, ...]:
    article_90 = _load_json(Path(article_90_path))
    article_100 = _load_json(Path(article_100_path))
    article_110 = _load_json(Path(article_110_path))

    identities = {
        _source_identity(article_90, "90"),
        _source_identity(article_100, "100"),
        _source_identity(article_110, "110"),
    }
    if len(identities) != 1:
        raise ValueError("ArticleSeed files do not share one source artifact identity")
    artifact_id, edition_id = next(iter(identities))

    definitions = build_definition_index(article_100)
    policy_review = build_section_review(article_90, "90.5", definitions=definitions)
    language_profile = derive_language_profile(policy_review)
    section_reviews = tuple(
        build_section_review(article_110, locator, definitions=definitions)
        for locator in SECTION_LOCATORS
    )

    payloads: dict[str, object] = {
        "definitions-article-100.json": definitions.to_dict(),
        "language-policy-90.5.json": {
            "section_review": policy_review.to_dict(),
            "language_profile": language_profile.to_dict(),
        },
    }
    for review in section_reviews:
        payloads[f"section-{review.section_locator}.json"] = review.to_dict()

    manifest = {
        "bundle_version": BUNDLE_VERSION,
        "type": "nec_2017_semantic_seed",
        "source_artifact": {
            "artifact_id": artifact_id,
            "edition_id": edition_id,
        },
        "input_files": {
            "article_90": Path(article_90_path).name,
            "article_100": Path(article_100_path).name,
            "article_110": Path(article_110_path).name,
        },
        "contracts": {
            "definition_index": DEFINITION_INDEX_VERSION,
            "section_review": SECTION_REVIEW_VERSION,
            "language_profile": LANGUAGE_PROFILE_VERSION,
        },
        "definition_index": {
            "file": "definitions-article-100.json",
            "article_locator": definitions.article_locator,
            "entry_count": len(definitions.entries),
            "diagnostic_count": len(definitions.diagnostics)
            + sum(len(entry.diagnostics) for entry in definitions.entries),
        },
        "language_policy": {
            "file": "language-policy-90.5.json",
            "section_locator": policy_review.section_locator,
            "evidence_count": len(language_profile.evidence),
        },
        "section_reviews": [
            {
                "file": f"section-{review.section_locator}.json",
                "section_locator": review.section_locator,
                "clause_count": len(review.clauses),
                "exception_count": len(review.exceptions),
                "note_count": len(review.notes),
                "diagnostic_count": len(review.diagnostics),
            }
            for review in section_reviews
        ],
    }
    payloads["manifest.json"] = manifest

    output = Path(output_dir)
    prepare_output_dir(output, force=force)
    written: list[Path] = []
    for name in sorted(payloads):
        path = output / name
        _write_json(path, payloads[name])
        written.append(path)
    return tuple(written)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build private NEC 2017 definition and section-review JSON from "
            "ArticleSeed files."
        )
    )
    parser.add_argument("--article-90", required=True, type=Path)
    parser.add_argument("--article-100", required=True, type=Path)
    parser.add_argument("--article-110", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--force", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    written = write_outputs(
        args.article_90,
        args.article_100,
        args.article_110,
        args.output_dir,
        force=args.force,
    )
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
