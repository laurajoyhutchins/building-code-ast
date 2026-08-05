"""Section-first navigation projections for structural corpus records.

The source inventories retain PDF pages, text offsets, and bounding boxes for
provenance. This module intentionally excludes those coordinates from the
navigation index. A record without a structural code locator remains unresolved
rather than receiving a page-derived identity.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

_STRUCTURAL_LOCATOR_FIELDS = (
    "code_locator",
    "locator",
    "section_context",
    "source_section",
    "parent_locator",
    "source_locator",
    "scope_locator",
)


def _text(record: Mapping[str, Any], field: str) -> str | None:
    value = record.get(field)
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _section_locator(record: Mapping[str, Any]) -> str | None:
    for field in _STRUCTURAL_LOCATOR_FIELDS:
        value = _text(record, field)
        if value is not None:
            return value
    return None


def code_address_for_record(
    record: Mapping[str, Any],
    *,
    publication: str = "IBC",
    edition: str = "2018",
) -> dict[str, str] | None:
    """Return the primary code address for an inventory record.

    Page anchors are deliberately ignored. Returning ``None`` is preferable to
    inventing a structural identity from a PDF coordinate.
    """

    record_type = _text(record, "record_type") or "record"

    if record_type in {"table", "figure"}:
        context_locator = _text(record, "section_context") or _section_locator(record)
        locator = _text(record, "published_identifier")
        if locator is None:
            return None
        label = "Table" if record_type == "table" else "Figure"
        address = {
            "publication": publication,
            "edition": edition,
            "kind": record_type,
            "locator": locator,
        }
        if context_locator is not None:
            address["context_locator"] = context_locator
        address["canonical"] = f"{publication}-{edition} {label} {locator}"
        return address

    if record_type in {"exception", "exception_block"}:
        context_locator = _text(record, "parent_locator") or _text(
            record, "section_context"
        )
        if context_locator is None:
            return None
        number = _text(record, "exception_number")
        address = {
            "publication": publication,
            "edition": edition,
            "kind": "exception",
            "locator": context_locator,
        }
        if number is not None:
            address["qualifier"] = number
            address["canonical"] = (
                f"{publication}-{edition} §{context_locator} Exception {number}"
            )
        else:
            address["canonical"] = f"{publication}-{edition} §{context_locator} Exception"
        return address

    if record_type == "definition":
        context_locator = _text(record, "scope_locator") or _text(
            record, "section_context"
        ) or _text(record, "source_section")
        if context_locator is None:
            return None
        term = _text(record, "term") or _text(record, "observed_term")
        address = {
            "publication": publication,
            "edition": edition,
            "kind": "definition",
            "locator": context_locator,
        }
        if term is not None:
            address["qualifier"] = term
            address["canonical"] = (
                f'{publication}-{edition} §{context_locator} Definition "{term}"'
            )
        else:
            address["canonical"] = f"{publication}-{edition} §{context_locator} Definition"
        return address

    if record_type == "equation":
        context_locator = _text(record, "section_context") or _text(
            record, "source_section"
        ) or _section_locator(record)
        if context_locator is None:
            return None
        label = _text(record, "equation_label") or _text(
            record, "equation_identifier"
        )
        address = {
            "publication": publication,
            "edition": edition,
            "kind": "equation",
            "locator": context_locator,
        }
        if label is not None:
            address["qualifier"] = label
            address["canonical"] = (
                f"{publication}-{edition} §{context_locator} Equation {label}"
            )
        else:
            address["canonical"] = f"{publication}-{edition} §{context_locator} Equation"
        return address

    if record_type in {"internal_cross_reference", "external_reference"}:
        context_locator = _text(record, "source_locator") or _text(
            record, "source_section"
        )
    else:
        context_locator = _section_locator(record)

    if context_locator is None:
        return None

    return {
        "publication": publication,
        "edition": edition,
        "kind": "section",
        "locator": context_locator,
        "canonical": f"{publication}-{edition} §{context_locator}",
    }


def _code_sort_key(
    address: Mapping[str, str],
) -> tuple[tuple[tuple[int, int | str], ...], str, str]:
    tokens: list[tuple[int, int | str]] = []
    for token in re.findall(r"\d+|[^\d]+", address["locator"]):
        if token.isdigit():
            tokens.append((0, int(token)))
        else:
            tokens.append((1, token.casefold()))
    return tuple(tokens), address["kind"], address["canonical"].casefold()


def _record_ref(record: Mapping[str, Any]) -> dict[str, str]:
    return {
        "record_type": _text(record, "record_type") or "record",
        "id": _text(record, "id") or "",
    }


def build_section_index(
    records: Iterable[Mapping[str, Any]],
    *,
    publication: str = "IBC",
    edition: str = "2018",
) -> dict[str, Any]:
    """Build a deterministic section-first projection over inventory records."""

    grouped: dict[str, list[tuple[dict[str, str], dict[str, str]]]] = defaultdict(list)
    unresolved: list[dict[str, str]] = []

    for record in records:
        record_ref = _record_ref(record)
        address = code_address_for_record(
            record,
            publication=publication,
            edition=edition,
        )
        if address is None:
            unresolved.append(record_ref)
            continue
        grouped[address["canonical"]].append((address, record_ref))

    entries: list[dict[str, Any]] = []
    grouped_items = sorted(
        grouped.items(),
        key=lambda item: _code_sort_key(item[1][0][0]),
    )
    for _canonical, grouped_records in grouped_items:
        address = grouped_records[0][0]
        record_refs = sorted(
            (record_ref for _, record_ref in grouped_records),
            key=lambda item: (item["record_type"], item["id"]),
        )
        entries.append({"address": address, "record_refs": record_refs})

    unresolved.sort(key=lambda item: (item["record_type"], item["id"]))
    return {
        "index_version": "0.1.0",
        "publication": {"code": publication, "edition": edition},
        "addressing_policy": "section_first",
        "provenance_policy": "page_anchors_remain_on_source_records",
        "entries": entries,
        "unresolved_record_refs": unresolved,
    }
