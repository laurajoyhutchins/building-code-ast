#!/usr/bin/env python3
"""Build a private NEC 2017-to-2020 expected changelog dataset.

Input records contain project-authored summaries and source locators only. This
command deliberately rejects source-bearing fields such as proposal text.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
from typing import Any

from building_code_ast.nec.change_history import (
    CHANGE_HISTORY_VERSION,
    ChangeType,
    DevelopmentDisposition,
    DevelopmentRecord,
    DevelopmentRecordType,
    DevelopmentStage,
    ObservedChange,
    ReconciliationOutcome,
    SourceLocator,
    SourceManifestEntry,
    project_expected_changes,
    reconcile_changes,
)


_INPUT_VERSION = "0.1.0"
_DEVELOPMENT_RECORD_FIELDS = frozenset(
    {
        "record_id",
        "change_chain_id",
        "record_type",
        "stage",
        "disposition",
        "panel",
        "affected_references_raw",
        "target_references_raw",
        "change_types",
        "summary",
        "source_locator",
        "related_record_ids",
    }
)
_SOURCE_FIELDS = frozenset(
    {
        "source_id",
        "document_type",
        "title",
        "cycle",
        "source_url",
        "retrieved_at",
        "sha256",
        "media_type",
        "access_scope",
        "panel",
        "page_count",
    }
)
_OBSERVED_FIELDS = frozenset(
    {
        "observed_change_id",
        "from_locators",
        "to_locators",
        "change_types",
        "summary",
        "alignment_confidence",
    }
)
_SOURCE_LOCATOR_FIELDS = frozenset({"source_id", "page", "anchor"})


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise ValueError(f"{label} keys must be strings")
    return value


def _sequence(value: Any, label: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _optional_string(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _string(value, label)


def _strings(value: Any, label: str) -> tuple[str, ...]:
    return tuple(
        _string(item, f"{label}[{index}]")
        for index, item in enumerate(_sequence(value, label))
    )


def _reject_extra_fields(
    value: Mapping[str, Any],
    allowed: frozenset[str],
    label: str,
) -> None:
    extras = sorted(set(value) - allowed)
    if extras:
        raise ValueError(f"unsupported {label} field: {extras[0]}")


def _integer_or_none(value: Any, label: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{label} must be an integer or null")
    return value


def _float(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be a number")
    return float(value)


def _enum(enum_type, value: Any, label: str):
    raw = _string(value, label)
    try:
        return enum_type(raw)
    except ValueError as error:
        raise ValueError(f"unsupported {label}: {raw}") from error


def _source(value: Any, index: int) -> SourceManifestEntry:
    label = f"sources[{index}]"
    obj = _mapping(value, label)
    _reject_extra_fields(obj, _SOURCE_FIELDS, "source")
    return SourceManifestEntry(
        source_id=_string(obj.get("source_id"), f"{label}.source_id"),
        document_type=_string(
            obj.get("document_type"), f"{label}.document_type"
        ),
        title=_string(obj.get("title"), f"{label}.title"),
        cycle=_string(obj.get("cycle"), f"{label}.cycle"),
        source_url=_string(obj.get("source_url"), f"{label}.source_url"),
        retrieved_at=_string(
            obj.get("retrieved_at"), f"{label}.retrieved_at"
        ),
        sha256=_string(obj.get("sha256"), f"{label}.sha256"),
        media_type=_string(obj.get("media_type"), f"{label}.media_type"),
        access_scope=_string(
            obj.get("access_scope"), f"{label}.access_scope"
        ),
        panel=_optional_string(obj.get("panel"), f"{label}.panel"),
        page_count=_integer_or_none(
            obj.get("page_count"), f"{label}.page_count"
        ),
    )


def _source_locator(value: Any, label: str) -> SourceLocator:
    obj = _mapping(value, label)
    _reject_extra_fields(obj, _SOURCE_LOCATOR_FIELDS, "source locator")
    return SourceLocator(
        source_id=_string(obj.get("source_id"), f"{label}.source_id"),
        page=_integer_or_none(obj.get("page"), f"{label}.page"),
        anchor=_optional_string(obj.get("anchor"), f"{label}.anchor"),
    )


def _development_record(value: Any, index: int) -> DevelopmentRecord:
    label = f"development_records[{index}]"
    obj = _mapping(value, label)
    _reject_extra_fields(obj, _DEVELOPMENT_RECORD_FIELDS, "development record")
    return DevelopmentRecord(
        record_id=_string(obj.get("record_id"), f"{label}.record_id"),
        change_chain_id=_string(
            obj.get("change_chain_id"), f"{label}.change_chain_id"
        ),
        record_type=_enum(
            DevelopmentRecordType,
            obj.get("record_type"),
            f"{label}.record_type",
        ),
        stage=_enum(DevelopmentStage, obj.get("stage"), f"{label}.stage"),
        disposition=_enum(
            DevelopmentDisposition,
            obj.get("disposition"),
            f"{label}.disposition",
        ),
        panel=_string(obj.get("panel"), f"{label}.panel"),
        affected_references_raw=_strings(
            obj.get("affected_references_raw"),
            f"{label}.affected_references_raw",
        ),
        target_references_raw=_strings(
            obj.get("target_references_raw", []),
            f"{label}.target_references_raw",
        ),
        change_types=tuple(
            _enum(ChangeType, item, f"{label}.change_types[{item_index}]")
            for item_index, item in enumerate(
                _sequence(obj.get("change_types"), f"{label}.change_types")
            )
        ),
        summary=_string(obj.get("summary"), f"{label}.summary"),
        source_locator=_source_locator(
            obj.get("source_locator"), f"{label}.source_locator"
        ),
        related_record_ids=_strings(
            obj.get("related_record_ids", []),
            f"{label}.related_record_ids",
        ),
    )


def _observed_change(value: Any, index: int) -> ObservedChange:
    label = f"observed_changes[{index}]"
    obj = _mapping(value, label)
    _reject_extra_fields(obj, _OBSERVED_FIELDS, "observed change")
    return ObservedChange(
        observed_change_id=_string(
            obj.get("observed_change_id"), f"{label}.observed_change_id"
        ),
        from_locators=_strings(
            obj.get("from_locators", []), f"{label}.from_locators"
        ),
        to_locators=_strings(
            obj.get("to_locators", []), f"{label}.to_locators"
        ),
        change_types=tuple(
            _enum(ChangeType, item, f"{label}.change_types[{item_index}]")
            for item_index, item in enumerate(
                _sequence(obj.get("change_types"), f"{label}.change_types")
            )
        ),
        summary=_string(obj.get("summary"), f"{label}.summary"),
        alignment_confidence=_float(
            obj.get("alignment_confidence"),
            f"{label}.alignment_confidence",
        ),
    )


def build_dataset(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one private input bundle and return a source-safe projection."""

    bundle = _mapping(value, "bundle")
    version = _string(bundle.get("bundle_version"), "bundle.bundle_version")
    if version != _INPUT_VERSION:
        raise ValueError(
            f"unsupported bundle_version {version!r}; expected {_INPUT_VERSION!r}"
        )
    cycle = _string(bundle.get("cycle"), "bundle.cycle")
    known_locators = _strings(
        bundle.get("known_2017_locators"), "bundle.known_2017_locators"
    )
    sources = tuple(
        _source(item, index)
        for index, item in enumerate(_sequence(bundle.get("sources"), "bundle.sources"))
    )
    source_ids = [item.source_id for item in sources]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("source manifest IDs must be unique")
    if any(item.cycle != cycle for item in sources):
        raise ValueError("source manifest cycle does not match bundle cycle")

    records = tuple(
        _development_record(item, index)
        for index, item in enumerate(
            _sequence(bundle.get("development_records"), "bundle.development_records")
        )
    )
    known_source_ids = set(source_ids)
    for record in records:
        if record.source_locator.source_id not in known_source_ids:
            raise ValueError(
                "development record source locator references unknown source_id: "
                + record.source_locator.source_id
            )

    observed = tuple(
        _observed_change(item, index)
        for index, item in enumerate(
            _sequence(bundle.get("observed_changes", []), "bundle.observed_changes")
        )
    )
    expected = project_expected_changes(records, known_locators)
    reconciliations = reconcile_changes(expected, observed) if observed else ()

    diagnostics: list[dict[str, Any]] = []
    for expectation in expected:
        for raw_reference in expectation.unresolved_references:
            diagnostics.append(
                {
                    "code": "unresolved-reference",
                    "expectation_id": expectation.expectation_id,
                    "raw_reference": raw_reference,
                    "message": (
                        "The controlling development record reference could not be "
                        "resolved against the supplied 2017 hierarchy."
                    ),
                }
            )
    for item in reconciliations:
        if item.outcome != ReconciliationOutcome.CONFIRMED:
            diagnostics.append(
                {
                    "code": "reconciliation-review",
                    "expectation_id": item.expectation_id,
                    "reconciliation_id": item.reconciliation_id,
                    "outcome": item.outcome.value,
                    "message": item.message,
                }
            )

    return {
        "dataset_version": CHANGE_HISTORY_VERSION,
        "type": "nec_expected_changelog",
        "cycle": cycle,
        "sources": [item.to_dict() for item in sorted(sources, key=lambda item: item.source_id)],
        "expected_changes": [item.to_dict() for item in expected],
        "observed_changes": [item.to_dict() for item in observed],
        "reconciliations": [item.to_dict() for item in reconciliations],
        "diagnostics": diagnostics,
    }


def _load_json(path: Path) -> Mapping[str, Any]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    payload = json.loads(source.read_text(encoding="utf-8"))
    return _mapping(payload, source.name)


def _write_json(path: Path, payload: object) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_dataset(input_path: Path, output_path: Path) -> dict[str, Any]:
    dataset = build_dataset(_load_json(Path(input_path)))
    _write_json(Path(output_path), dataset)
    return dataset


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a private expected NEC 2017-to-2020 changelog from "
            "source-safe development records."
        )
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return exit status 1 when the generated dataset contains diagnostics",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    dataset = write_dataset(args.input, args.output)
    print(args.output)
    print(
        "expectations="
        f"{len(dataset['expected_changes'])} "
        f"reconciliations={len(dataset['reconciliations'])} "
        f"diagnostics={len(dataset['diagnostics'])}"
    )
    return 1 if args.strict and dataset["diagnostics"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
