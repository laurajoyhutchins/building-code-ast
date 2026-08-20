"""ICC code-development records, lineage validation, and bounded extraction."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
import hashlib
import json
import re
from typing import Any

from ..model import DiagnosticSeverity
from .adapters import AdapterResult, EvidenceDiagnostic, SourceRegion
from .model import EvidenceRole
from .source_packages import BoundArtifact


DEVELOPMENT_RECORD_VERSION = "0.1.0"
_PROPOSAL_ID_RE = re.compile(r"^[A-Z]+\d+-\d{2}$")


class DevelopmentRecordKind(StrEnum):
    PROPOSAL = "proposal"
    PUBLIC_COMMENT = "public_comment"
    COMMITTEE_ACTION = "committee_action"
    HEARING_ACTION = "hearing_action"
    FINAL_ACTION = "final_action"


class DevelopmentDisposition(StrEnum):
    SUBMITTED = "submitted"
    APPROVED = "approved"
    APPROVED_AS_MODIFIED = "approved_as_modified"
    DISAPPROVED = "disapproved"
    WITHDRAWN = "withdrawn"
    SUPERSEDED = "superseded"


DEVELOPMENT_KIND_VALUES = frozenset(item.value for item in DevelopmentRecordKind)
DEVELOPMENT_DISPOSITION_VALUES = frozenset(item.value for item in DevelopmentDisposition)


def _require_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must not be empty")


def _optional_text(value: str | None, label: str) -> None:
    if value is not None:
        _require_text(value, label)


def _strict_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    extra = sorted(actual - expected)
    missing = sorted(expected - actual)
    if extra:
        raise ValueError(f"{label} has unsupported fields: {', '.join(extra)}")
    if missing:
        raise ValueError(f"{label} is missing fields: {', '.join(missing)}")


def _optional_date(value: str | None, label: str) -> None:
    if value is None:
        return
    _require_text(value, label)
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO 8601 date") from exc


def _identity(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return f"development:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


@dataclass(frozen=True, slots=True)
class DevelopmentRecord:
    source_id: str
    proposal_id: str
    record_key: str
    kind: DevelopmentRecordKind
    disposition: DevelopmentDisposition
    sequence: int
    proponent: str | None
    affected_locators: tuple[str, ...]
    parent_keys: tuple[str, ...]
    action_date: str | None
    summary: str
    source_page: int
    source_anchor: str
    record_version: str = field(default=DEVELOPMENT_RECORD_VERSION, init=False)

    def __post_init__(self) -> None:
        _require_text(self.source_id, "source_id")
        if not isinstance(self.proposal_id, str) or _PROPOSAL_ID_RE.fullmatch(self.proposal_id) is None:
            raise ValueError("proposal_id must be an ICC-style proposal identifier")
        _require_text(self.record_key, "record_key")
        if not isinstance(self.kind, DevelopmentRecordKind):
            raise ValueError("kind must be a DevelopmentRecordKind")
        if not isinstance(self.disposition, DevelopmentDisposition):
            raise ValueError("disposition must be a DevelopmentDisposition")
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int) or self.sequence < 1:
            raise ValueError("sequence must be a positive integer")
        _optional_text(self.proponent, "proponent")
        if self.kind is DevelopmentRecordKind.PROPOSAL and self.proponent is None:
            raise ValueError("proponent is required for proposal records")
        if not isinstance(self.affected_locators, tuple) or not self.affected_locators:
            raise ValueError("affected_locators must be a nonempty tuple")
        for locator in self.affected_locators:
            _require_text(locator, "affected locator")
        if len(set(self.affected_locators)) != len(self.affected_locators):
            raise ValueError("affected_locators must not contain duplicates")
        if not isinstance(self.parent_keys, tuple):
            raise ValueError("parent_keys must be a tuple")
        for parent in self.parent_keys:
            _require_text(parent, "parent key")
        if len(set(self.parent_keys)) != len(self.parent_keys):
            raise ValueError("parent_keys must not contain duplicates")
        if self.record_key in self.parent_keys:
            raise ValueError("record cannot be its own parent")
        _optional_date(self.action_date, "action_date")
        _require_text(self.summary, "summary")
        if isinstance(self.source_page, bool) or not isinstance(self.source_page, int) or self.source_page < 1:
            raise ValueError("source_page must be a positive integer")
        _require_text(self.source_anchor, "source_anchor")

    @property
    def record_id(self) -> str:
        return _identity(self.identity_dict())

    def identity_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "proposal_id": self.proposal_id,
            "record_key": self.record_key,
            "kind": self.kind.value,
            "disposition": self.disposition.value,
            "sequence": self.sequence,
            "proponent": self.proponent,
            "affected_locators": list(self.affected_locators),
            "parent_keys": list(self.parent_keys),
            "action_date": self.action_date,
            "summary": self.summary,
            "source_page": self.source_page,
            "source_anchor": self.source_anchor,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_version": self.record_version,
            "record_id": self.record_id,
            "type": "development_record",
            **self.identity_dict(),
        }


def development_record_from_dict(value: Mapping[str, Any]) -> DevelopmentRecord:
    if not isinstance(value, Mapping):
        raise ValueError("development record must be an object")
    expected = {
        "record_version",
        "record_id",
        "type",
        "source_id",
        "proposal_id",
        "record_key",
        "kind",
        "disposition",
        "sequence",
        "proponent",
        "affected_locators",
        "parent_keys",
        "action_date",
        "summary",
        "source_page",
        "source_anchor",
    }
    _strict_keys(value, expected, "development record")
    if value["record_version"] != DEVELOPMENT_RECORD_VERSION:
        raise ValueError("record_version is unsupported")
    if value["type"] != "development_record":
        raise ValueError("type must be development_record")
    affected = value["affected_locators"]
    parents = value["parent_keys"]
    if not isinstance(affected, list):
        raise ValueError("affected_locators must be an array")
    if not isinstance(parents, list):
        raise ValueError("parent_keys must be an array")
    try:
        kind = DevelopmentRecordKind(value["kind"])
    except (TypeError, ValueError) as exc:
        raise ValueError("kind is unsupported") from exc
    try:
        disposition = DevelopmentDisposition(value["disposition"])
    except (TypeError, ValueError) as exc:
        raise ValueError("disposition is unsupported") from exc
    record = DevelopmentRecord(
        source_id=value["source_id"],
        proposal_id=value["proposal_id"],
        record_key=value["record_key"],
        kind=kind,
        disposition=disposition,
        sequence=value["sequence"],
        proponent=value["proponent"],
        affected_locators=tuple(affected),
        parent_keys=tuple(parents),
        action_date=value["action_date"],
        summary=value["summary"],
        source_page=value["source_page"],
        source_anchor=value["source_anchor"],
    )
    if value["record_id"] != record.record_id:
        raise ValueError("record_id does not match deterministic identity")
    return record


def _assert_acyclic(records_by_key: Mapping[str, DevelopmentRecord]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(key: str) -> None:
        if key in visited:
            return
        if key in visiting:
            raise ValueError(f"development lineage contains a parent cycle at {key}")
        visiting.add(key)
        for parent in records_by_key[key].parent_keys:
            visit(parent)
        visiting.remove(key)
        visited.add(key)

    for record_key in records_by_key:
        visit(record_key)


def _has_proposal_ancestor(
    record: DevelopmentRecord,
    proposal_key: str,
    records_by_key: Mapping[str, DevelopmentRecord],
) -> bool:
    pending = list(record.parent_keys)
    seen: set[str] = set()
    while pending:
        parent_key = pending.pop()
        if parent_key == proposal_key:
            return True
        if parent_key in seen:
            continue
        seen.add(parent_key)
        pending.extend(records_by_key[parent_key].parent_keys)
    return False


@dataclass(frozen=True, slots=True)
class DevelopmentLineage:
    records: tuple[DevelopmentRecord, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.records, tuple) or not self.records:
            raise ValueError("records must be a nonempty tuple")
        if any(not isinstance(record, DevelopmentRecord) for record in self.records):
            raise ValueError("records must contain DevelopmentRecord values")
        keys = [record.record_key for record in self.records]
        if len(set(keys)) != len(keys):
            raise ValueError("record_key values must be unique")
        records_by_key = {record.record_key: record for record in self.records}
        for record in self.records:
            for parent in record.parent_keys:
                if parent not in records_by_key:
                    raise ValueError(
                        f"unresolved parent {parent} for record {record.record_key}"
                    )
        _assert_acyclic(records_by_key)
        for record in self.records:
            for parent in record.parent_keys:
                parent_record = records_by_key[parent]
                if (
                    parent_record.proposal_id == record.proposal_id
                    and parent_record.sequence >= record.sequence
                ):
                    raise ValueError(
                        f"parent sequence must precede child sequence for {record.record_key}"
                    )

        by_proposal: dict[str, list[DevelopmentRecord]] = {}
        for record in self.records:
            by_proposal.setdefault(record.proposal_id, []).append(record)
        for proposal_id, proposal_records in by_proposal.items():
            sequences = [record.sequence for record in proposal_records]
            if len(set(sequences)) != len(sequences):
                raise ValueError(f"duplicate sequence in proposal {proposal_id}")
            proposals = [
                record
                for record in proposal_records
                if record.kind is DevelopmentRecordKind.PROPOSAL
            ]
            if len(proposals) != 1:
                raise ValueError(
                    f"proposal {proposal_id} must contain exactly one proposal record"
                )
            proposal = proposals[0]
            if proposal.sequence != 1:
                raise ValueError(f"proposal record for {proposal_id} must have sequence 1")
            for record in proposal_records:
                if record is proposal:
                    continue
                if not record.parent_keys:
                    raise ValueError(
                        f"non-proposal record {record.record_key} must have a parent"
                    )
                if not _has_proposal_ancestor(record, proposal.record_key, records_by_key):
                    raise ValueError(
                        f"record {record.record_key} is disconnected from its proposal record"
                    )
            finals = [
                record
                for record in proposal_records
                if record.kind is DevelopmentRecordKind.FINAL_ACTION
            ]
            if len({record.disposition for record in finals}) > 1:
                raise ValueError(f"conflicting final actions for proposal {proposal_id}")

    def records_for(self, proposal_id: str) -> tuple[DevelopmentRecord, ...]:
        _require_text(proposal_id, "proposal_id")
        return tuple(
            sorted(
                (record for record in self.records if record.proposal_id == proposal_id),
                key=lambda record: (record.sequence, record.record_key),
            )
        )

    def controlling_record(self, proposal_id: str) -> DevelopmentRecord:
        records = self.records_for(proposal_id)
        if not records:
            raise ValueError(f"proposal {proposal_id} is not present")
        priority = {
            DevelopmentRecordKind.PROPOSAL: 0,
            DevelopmentRecordKind.PUBLIC_COMMENT: 1,
            DevelopmentRecordKind.COMMITTEE_ACTION: 2,
            DevelopmentRecordKind.HEARING_ACTION: 3,
            DevelopmentRecordKind.FINAL_ACTION: 4,
        }
        return max(records, key=lambda record: (priority[record.kind], record.sequence))


def _default_pdf_page_text(content: bytes) -> tuple[str, ...]:
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "PyMuPDF is required for ICC development PDF extraction; install the evidence-pdf extra"
        ) from exc
    try:
        document = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("PyMuPDF could not open the registered ICC development PDF") from exc
    try:
        return tuple(page.get_text("text") for page in document)
    finally:
        document.close()


_ACTION_KINDS = {
    "public comment": DevelopmentRecordKind.PUBLIC_COMMENT,
    "committee action": DevelopmentRecordKind.COMMITTEE_ACTION,
    "assembly action": DevelopmentRecordKind.HEARING_ACTION,
    "hearing action": DevelopmentRecordKind.HEARING_ACTION,
    "final action": DevelopmentRecordKind.FINAL_ACTION,
}
_DISPOSITIONS = {
    "submitted": DevelopmentDisposition.SUBMITTED,
    "approved": DevelopmentDisposition.APPROVED,
    "approved as modified": DevelopmentDisposition.APPROVED_AS_MODIFIED,
    "disapproved": DevelopmentDisposition.DISAPPROVED,
    "withdrawn": DevelopmentDisposition.WITHDRAWN,
    "superseded": DevelopmentDisposition.SUPERSEDED,
}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


class IccDevelopmentTextAdapter:
    """Extract a bounded proposal/action grammar from registered ICC PDF text."""

    adapter_id = "icc-development-text"
    adapter_version = "0.2.0"
    supported_roles = frozenset({EvidenceRole.DEVELOPMENT_HISTORY})
    supported_media_types = frozenset({"application/pdf"})

    def __init__(
        self,
        *,
        page_text_extractor: Callable[[bytes], tuple[str, ...]] | None = None,
    ) -> None:
        if page_text_extractor is not None and not callable(page_text_extractor):
            raise ValueError("page_text_extractor must be callable")
        self.page_text_extractor = page_text_extractor or _default_pdf_page_text

    def extract(
        self,
        source: BoundArtifact,
        content: bytes,
    ) -> AdapterResult[DevelopmentRecord]:
        pages = self.page_text_extractor(content)
        if not isinstance(pages, tuple) or any(not isinstance(page, str) for page in pages):
            raise ValueError("page_text_extractor must return a tuple of strings")
        records: list[DevelopmentRecord] = []
        diagnostics: list[EvidenceDiagnostic] = []
        unsupported: list[SourceRegion] = []

        for source_page, page_text in enumerate(pages, start=1):
            blocks: list[tuple[str, list[str]]] = []
            current_id: str | None = None
            current_lines: list[str] = []
            for raw_line in page_text.splitlines():
                line = raw_line.strip()
                if _PROPOSAL_ID_RE.fullmatch(line):
                    if current_id is not None:
                        blocks.append((current_id, current_lines))
                    current_id = line
                    current_lines = []
                elif current_id is not None and line:
                    current_lines.append(line)
            if current_id is not None:
                blocks.append((current_id, current_lines))

            for proposal_id, lines in blocks:
                values: dict[str, str] = {}
                action_lines: list[tuple[str, str]] = []
                for line in lines:
                    if ":" not in line:
                        continue
                    label, raw_value = line.split(":", 1)
                    normalized_label = label.strip().casefold()
                    text = raw_value.strip()
                    if normalized_label in {"proponent", "affected", "proposal"}:
                        values[normalized_label] = text
                    elif normalized_label.endswith("action") or normalized_label == "public comment":
                        action_lines.append((normalized_label, text))
                required = {"proponent", "affected", "proposal"}
                missing = sorted(required - set(values))
                if missing:
                    region = SourceRegion(page=source_page, anchor=f"{proposal_id}:proposal")
                    diagnostics.append(
                        EvidenceDiagnostic(
                            code="incomplete-development-proposal",
                            severity=DiagnosticSeverity.WARNING,
                            message="Proposal block is missing: " + ", ".join(missing),
                            region=region,
                        )
                    )
                    unsupported.append(region)
                    continue
                locators = tuple(
                    locator.strip()
                    for locator in values["affected"].split(",")
                    if locator.strip()
                )
                proposal_key = f"{proposal_id}:proposal"
                proposal = DevelopmentRecord(
                    source_id=source.source_id,
                    proposal_id=proposal_id,
                    record_key=proposal_key,
                    kind=DevelopmentRecordKind.PROPOSAL,
                    disposition=DevelopmentDisposition.SUBMITTED,
                    sequence=1,
                    proponent=values["proponent"],
                    affected_locators=locators,
                    parent_keys=(),
                    action_date=None,
                    summary=values["proposal"],
                    source_page=source_page,
                    source_anchor=proposal_key,
                )
                records.append(proposal)
                previous_key = proposal_key
                occurrence: dict[str, int] = {}
                chain_open = True
                for source_sequence, (label, text) in enumerate(action_lines, start=2):
                    if not chain_open:
                        region = SourceRegion(
                            page=source_page,
                            anchor=f"{proposal_id}:blocked-action:{source_sequence}",
                        )
                        diagnostics.append(
                            EvidenceDiagnostic(
                                code="blocked-development-action",
                                severity=DiagnosticSeverity.WARNING,
                                message=(
                                    "Development action follows an unsupported action whose "
                                    "parentage is unresolved."
                                ),
                                region=region,
                            )
                        )
                        unsupported.append(region)
                        continue
                    kind = _ACTION_KINDS.get(label)
                    disposition = _DISPOSITIONS.get(text.casefold())
                    if kind is None or disposition is None:
                        region = SourceRegion(
                            page=source_page,
                            anchor=f"{proposal_id}:unsupported-action:{source_sequence}",
                        )
                        diagnostics.append(
                            EvidenceDiagnostic(
                                code="unsupported-development-action",
                                severity=DiagnosticSeverity.WARNING,
                                message="Development action is outside the bounded vocabulary.",
                                region=region,
                            )
                        )
                        unsupported.append(region)
                        chain_open = False
                        continue
                    stem = _slug(label)
                    occurrence[stem] = occurrence.get(stem, 0) + 1
                    suffix = "" if occurrence[stem] == 1 else f"-{occurrence[stem]}"
                    record_key = f"{proposal_id}:{stem}{suffix}"
                    record = DevelopmentRecord(
                        source_id=source.source_id,
                        proposal_id=proposal_id,
                        record_key=record_key,
                        kind=kind,
                        disposition=disposition,
                        sequence=source_sequence,
                        proponent=None,
                        affected_locators=locators,
                        parent_keys=(previous_key,),
                        action_date=None,
                        summary=text,
                        source_page=source_page,
                        source_anchor=record_key,
                    )
                    records.append(record)
                    previous_key = record_key

        return AdapterResult(
            source_id=source.source_id,
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            records=tuple(records),
            diagnostics=tuple(diagnostics),
            unsupported_regions=tuple(unsupported),
        )
