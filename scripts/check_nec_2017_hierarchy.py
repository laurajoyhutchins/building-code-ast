#!/usr/bin/env python3
"""Compare private ArticleSeed hierarchy with a locally supplied NEC clause oracle."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
from typing import Any

from building_code_ast.ingest.nec_hierarchy import (
    HierarchyRecord,
    canonical_nec_locator,
    compare_hierarchy,
    load_clause_oracle,
)


REPORT_TYPE = "nec_hierarchy_conformance"


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    return value


def _load_json(path: Path) -> Mapping[str, Any]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    payload = json.loads(source.read_text(encoding="utf-8"))
    return _mapping(payload, source.name)


def _walk_records(
    value: Any,
    *,
    label: str,
    records: list[HierarchyRecord],
) -> None:
    node = _mapping(value, label)
    attributes = _mapping(node.get("attributes"), f"{label}.attributes")
    locator_value = attributes.get("nec_locator")
    if locator_value is not None:
        locator = canonical_nec_locator(_string(locator_value, f"{label}.nec_locator"))
        title = _string(attributes.get("nec_title", ""), f"{label}.nec_title")
        raw_parent = attributes.get("nec_parent")
        parent = (
            canonical_nec_locator(_string(raw_parent, f"{label}.nec_parent"))
            if raw_parent is not None
            else None
        )
        raw_depth = attributes.get("nec_depth")
        if not isinstance(raw_depth, str) or not raw_depth.isdigit():
            raise ValueError(f"{label}.nec_depth must be a decimal string")
        records.append(
            HierarchyRecord(
                locator=locator,
                title=title,
                parent=parent,
                order=len(records),
                depth=int(raw_depth),
            )
        )

    children = node.get("children")
    if not isinstance(children, list):
        raise ValueError(f"{label}.children must be an array")
    for index, child in enumerate(children):
        _walk_records(
            child,
            label=f"{label}.children[{index}]",
            records=records,
        )


def _article_records(payload: Mapping[str, Any], source_name: str) -> tuple[str, tuple[HierarchyRecord, ...]]:
    article = _mapping(payload.get("article"), f"{source_name}.article")
    article_number = canonical_nec_locator(
        _string(article.get("number"), f"{source_name}.article.number")
    )
    if "." in article_number:
        raise ValueError(f"{source_name}.article.number must identify an Article")

    document = _mapping(payload.get("document_ast"), f"{source_name}.document_ast")
    root = _mapping(document.get("root"), f"{source_name}.document_ast.root")
    root_children = root.get("children")
    if not isinstance(root_children, list) or len(root_children) != 1:
        raise ValueError(f"{source_name} must contain exactly one Article node")
    article_node = _mapping(root_children[0], f"{source_name}.article_node")
    article_locator = _string(article_node.get("locator"), f"{source_name}.article_node.locator")
    if article_locator != f"article:{article_number}":
        raise ValueError(
            f"{source_name} Article node locator must be 'article:{article_number}'"
        )

    records: list[HierarchyRecord] = []
    _walk_records(article_node, label=f"{source_name}.article_node", records=records)
    return article_number, tuple(records)


def _article_of(locator: str) -> str:
    return canonical_nec_locator(locator).split(".", 1)[0]


def write_report(
    article_seed_paths: Sequence[Path],
    oracle_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    """Write one source-free structural conformance report."""

    if not article_seed_paths:
        raise ValueError("at least one ArticleSeed is required")

    by_article: dict[str, tuple[str, tuple[HierarchyRecord, ...]]] = {}
    for path_value in article_seed_paths:
        path = Path(path_value)
        payload = _load_json(path)
        article_number, records = _article_records(payload, path.name)
        if article_number in by_article:
            raise ValueError(f"duplicate ArticleSeed for Article {article_number}")
        by_article[article_number] = (path.name, records)

    oracle_source = Path(oracle_path)
    if not oracle_source.is_file():
        raise FileNotFoundError(oracle_source)
    oracle = load_clause_oracle(oracle_source.read_text(encoding="utf-8-sig"))
    articles = sorted(by_article, key=lambda value: int(value))
    article_set = set(articles)
    expected = tuple(record for record in oracle if _article_of(record.locator) in article_set)

    actual: list[HierarchyRecord] = []
    for article_number in articles:
        _, records = by_article[article_number]
        for record in records:
            actual.append(
                HierarchyRecord(
                    locator=record.locator,
                    title=record.title,
                    parent=record.parent,
                    order=len(actual),
                    depth=record.depth,
                )
            )

    comparison = compare_hierarchy(expected, tuple(actual))
    report: dict[str, Any] = {
        "type": REPORT_TYPE,
        "articles": articles,
        "inputs": {
            "article_seeds": [by_article[number][0] for number in articles],
            "oracle": oracle_source.name,
        },
        **comparison.to_dict(),
    }

    destination = Path(report_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare locally generated NEC 2017 ArticleSeed hierarchy with a "
            "locally supplied clause oracle. The report contains structural "
            "metadata only, not NEC source prose."
        )
    )
    parser.add_argument(
        "--article-seed",
        action="append",
        required=True,
        type=Path,
        help="ArticleSeed JSON path; repeat for each converted Article",
    )
    parser.add_argument("--oracle", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return exit status 1 when any hierarchy mismatch is present",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = write_report(
        tuple(args.article_seed),
        args.oracle,
        args.report,
    )
    print(args.report)
    print(
        f"articles={','.join(report['articles'])} "
        f"matches={report['matches']} mismatches={len(report['mismatches'])}"
    )
    return 1 if args.strict and not report["conforms"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
