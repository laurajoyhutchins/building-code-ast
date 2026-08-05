"""Source-safe NEC development history, expectation, and reconciliation models.

This module records project-authored summaries and exact source locators. It does
not store or reproduce NEC or NFPA source prose. Development history creates an
expectation oracle; the issued edition remains the controlling text.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
import re
from typing import Any, Iterable, Sequence

from ..ingest.nec_hierarchy import canonical_nec_locator


CHANGE_HISTORY_VERSION = "0.1.0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RANGE_RE = re.compile(
    r"^(?P<start>\d{2,3}\.\d+[A-Za-z]?(?:\([A-Za-z0-9]+\))+?)"
    r"\s+(?:through|to)\s+\((?P<end>[A-Za-z0-9]+)\)$",
    re.IGNORECASE,
)
_SECTION_PREFIX_RE = re.compile(r"^Section\s+", re.IGNORECASE)


class DevelopmentRecordType(StrEnum):
    PUBLIC_INPUT = "public_input"
    FIRST_REVISION = "first_revision"
    PUBLIC_COMMENT = "public_comment"
    SECOND_REVISION = "second_revision"
    TECHNICAL_MEETING_MOTION = "technical_meeting_motion"
    STANDARDS_COUNCIL_ACTION = "standards_council_action"
    TIA = "tia"
    ERRATUM = "erratum"


class DevelopmentStage(StrEnum):
    PUBLIC_INPUT = "public_input"
    FIRST_REVISION = "first_revision"
    PUBLIC_COMMENT = "public_comment"
    SECOND_REVISION = "second_revision"
    TECHNICAL_MEETING = "technical_meeting"
    STANDARDS_COUNCIL = "standards_council"
    TIA = "tia"
    ERRATUM = "erratum"


_STAGE_RANK = {
    DevelopmentStage.PUBLIC_INPUT: 10,
    DevelopmentStage.FIRST_REVISION: 20,
    DevelopmentStage.PUBLIC_COMMENT: 30,
    DevelopmentStage.SECOND_REVISION: 40,
    DevelopmentStage.TECHNICAL_MEETING: 50,
    DevelopmentStage.STANDARDS_COUNCIL: 60,
    DevelopmentStage.TIA: 70,
    DevelopmentStage.ERRATUM: 80,
}


class DevelopmentDisposition(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    ACCEPTED_IN_PRINCIPLE = "accepted_in_principle"
    ACCEPTED_IN_PART = "accepted_in_part"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    FAILED_BALLOT = "failed_ballot"
    RETURNED_TO_PRIOR_EDITION = "returned_to_prior_edition"
    ISSUED = "issued"
    CORRECTED = "corrected"


class ChangeType(StrEnum):
    ADD = "add"
    ADD_SUBDIVISION = "add_subdivision"
    DELETE = "delete"
    MODIFY_TEXT = "modify_text"
    MOVE = "move"
    RENUMBER = "renumber"
    SPLIT = "split"
    MERGE = "merge"
    RESTRUCTURE = "restructure"
    CHANGE_HEADING = "change_heading"
    CHANGE_DEFINITION = "change_definition"
    CHANGE_TABLE = "change_table"
    CHANGE_EXCEPTION = "change_exception"
    CHANGE_CROSS_REFERENCE = "change_cross_reference"
    EDITORIAL_ONLY = "editorial_only"
    NO_FINAL_CHANGE = "no_final_change"
    UNKNOWN = "unknown"


class ExpectedDisposition(StrEnum):
    CHANGE_EXPECTED = "change_expected"
    NO_CHANGE_EXPECTED = "no_change_expected"
    UNCERTAIN = "uncertain"


class ExpectationConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReconciliationOutcome(StrEnum):
    CONFIRMED = "confirmed"
    EXPECTED_NOT_OBSERVED = "expected_not_observed"
    CONTRADICTED = "contradicted"
    AMBIGUOUS = "ambiguous"
    UNEXPECTED_OBSERVED = "unexpected_observed"


def _require_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must not be empty")


def _require_strings(values: Sequence[str], label: str, *, allow_empty: bool = False) -> None:
    if not allow_empty and not values:
        raise ValueError(f"{label} must not be empty")
    for value in values:
        _require_text(value, label)


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


@dataclass(frozen=True, slots=True)
class SourceLocator:
    source_id: str
    page: int | None = None
    anchor: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.source_id, "source_id")
        if self.page is not None and (isinstance(self.page, bool) or self.page < 1):
            raise ValueError("page must be a positive integer or null")
        if self.anchor is not None:
            _require_text(self.anchor, "anchor")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "page": self.page,
            "anchor": self.anchor,
        }


@dataclass(frozen=True, slots=True)
class SourceManifestEntry:
    source_id: str
    document_type: str
    title: str
    cycle: str
    source_url: str
    retrieved_at: str
    sha256: str
    media_type: str
    access_scope: str
    panel: str | None = None
    page_count: int | None = None

    def __post_init__(self) -> None:
        for label, value in (
            ("source_id", self.source_id),
            ("document_type", self.document_type),
            ("title", self.title),
            ("cycle", self.cycle),
            ("source_url", self.source_url),
            ("retrieved_at", self.retrieved_at),
            ("media_type", self.media_type),
            ("access_scope", self.access_scope),
        ):
            _require_text(value, label)
        if _SHA256_RE.fullmatch(self.sha256) is None:
            raise ValueError("sha256 must be a lowercase SHA-256 digest")
        if self.panel is not None:
            _require_text(self.panel, "panel")
        if self.page_count is not None and (
            isinstance(self.page_count, bool) or self.page_count < 1
        ):
            raise ValueError("page_count must be a positive integer or null")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "document_type": self.document_type,
            "title": self.title,
            "cycle": self.cycle,
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at,
            "sha256": self.sha256,
            "media_type": self.media_type,
            "access_scope": self.access_scope,
            "panel": self.panel,
            "page_count": self.page_count,
        }


@dataclass(frozen=True, slots=True)
class DevelopmentRecord:
    record_id: str
    change_chain_id: str
    record_type: DevelopmentRecordType
    stage: DevelopmentStage
    disposition: DevelopmentDisposition
    panel: str
    affected_references_raw: tuple[str, ...]
    target_references_raw: tuple[str, ...]
    change_types: tuple[ChangeType, ...]
    summary: str
    source_locator: SourceLocator
    related_record_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for label, value in (
            ("record_id", self.record_id),
            ("change_chain_id", self.change_chain_id),
            ("panel", self.panel),
            ("summary", self.summary),
        ):
            _require_text(value, label)
        _require_strings(self.affected_references_raw, "affected_references_raw")
        _require_strings(
            self.target_references_raw,
            "target_references_raw",
            allow_empty=True,
        )
        _require_strings(self.related_record_ids, "related_record_ids", allow_empty=True)
        if not self.change_types:
            raise ValueError("change_types must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "change_chain_id": self.change_chain_id,
            "record_type": self.record_type.value,
            "stage": self.stage.value,
            "disposition": self.disposition.value,
            "panel": self.panel,
            "affected_references_raw": list(self.affected_references_raw),
            "target_references_raw": list(self.target_references_raw),
            "change_types": [item.value for item in self.change_types],
            "summary": self.summary,
            "source_locator": self.source_locator.to_dict(),
            "related_record_ids": list(self.related_record_ids),
        }


@dataclass(frozen=True, slots=True)
class ResolvedReference:
    raw_reference: str
    resolved_locators: tuple[str, ...]
    method: str
    confidence: float
    diagnostic: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.raw_reference, "raw_reference")
        _require_text(self.method, "method")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        for locator in self.resolved_locators:
            canonical_nec_locator(locator)
        if self.diagnostic is not None:
            _require_text(self.diagnostic, "diagnostic")

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_reference": self.raw_reference,
            "resolved_locators": list(self.resolved_locators),
            "method": self.method,
            "confidence": self.confidence,
            "diagnostic": self.diagnostic,
        }


@dataclass(frozen=True, slots=True)
class ExpectedChange:
    expectation_id: str
    change_chain_id: str
    from_locators: tuple[str, ...]
    expected_target_references: tuple[str, ...]
    unresolved_references: tuple[str, ...]
    change_types: tuple[ChangeType, ...]
    summary: str
    disposition: ExpectedDisposition
    confidence: ExpectationConfidence
    controlling_record_id: str
    supporting_record_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "expectation_id": self.expectation_id,
            "change_chain_id": self.change_chain_id,
            "from_locators": list(self.from_locators),
            "expected_target_references": list(self.expected_target_references),
            "unresolved_references": list(self.unresolved_references),
            "change_types": [item.value for item in self.change_types],
            "summary": self.summary,
            "disposition": self.disposition.value,
            "confidence": self.confidence.value,
            "controlling_record_id": self.controlling_record_id,
            "supporting_record_ids": list(self.supporting_record_ids),
        }


@dataclass(frozen=True, slots=True)
class ObservedChange:
    observed_change_id: str
    from_locators: tuple[str, ...]
    to_locators: tuple[str, ...]
    change_types: tuple[ChangeType, ...]
    summary: str
    alignment_confidence: float

    def __post_init__(self) -> None:
        _require_text(self.observed_change_id, "observed_change_id")
        _require_strings(self.from_locators, "from_locators", allow_empty=True)
        _require_strings(self.to_locators, "to_locators", allow_empty=True)
        _require_text(self.summary, "summary")
        if not self.change_types:
            raise ValueError("change_types must not be empty")
        if not 0.0 <= self.alignment_confidence <= 1.0:
            raise ValueError("alignment_confidence must be between 0 and 1")
        for locator in (*self.from_locators, *self.to_locators):
            canonical_nec_locator(locator)

    def to_dict(self) -> dict[str, Any]:
        return {
            "observed_change_id": self.observed_change_id,
            "from_locators": list(self.from_locators),
            "to_locators": list(self.to_locators),
            "change_types": [item.value for item in self.change_types],
            "summary": self.summary,
            "alignment_confidence": self.alignment_confidence,
        }


@dataclass(frozen=True, slots=True)
class Reconciliation:
    reconciliation_id: str
    expectation_id: str | None
    observed_change_ids: tuple[str, ...]
    outcome: ReconciliationOutcome
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "reconciliation_id": self.reconciliation_id,
            "expectation_id": self.expectation_id,
            "observed_change_ids": list(self.observed_change_ids),
            "outcome": self.outcome.value,
            "message": self.message,
        }


def _unresolved(raw_reference: str, diagnostic: str) -> ResolvedReference:
    return ResolvedReference(
        raw_reference=raw_reference,
        resolved_locators=(),
        method="unresolved",
        confidence=0.0,
        diagnostic=diagnostic,
    )


def _range_values(start: str, end: str) -> tuple[str, ...] | None:
    if start.isdigit() and end.isdigit():
        first = int(start)
        last = int(end)
        if last < first:
            return None
        return tuple(str(value) for value in range(first, last + 1))
    if len(start) == len(end) == 1 and start.isalpha() and end.isalpha():
        if start.isupper() != end.isupper():
            return None
        first = ord(start)
        last = ord(end)
        if last < first:
            return None
        return tuple(chr(value) for value in range(first, last + 1))
    return None


def resolve_nec_reference(
    raw_reference: str,
    known_locators: Iterable[str],
) -> ResolvedReference:
    """Resolve exact locators and explicit sibling ranges against a 2017 tree."""

    _require_text(raw_reference, "raw_reference")
    known = {canonical_nec_locator(item) for item in known_locators}
    compact = _SECTION_PREFIX_RE.sub("", raw_reference.strip())

    try:
        exact = canonical_nec_locator(compact)
    except ValueError:
        exact = None
    if exact is not None:
        if exact in known:
            return ResolvedReference(raw_reference, (exact,), "exact", 1.0)
        return _unresolved(raw_reference, f"locator {exact} is absent from the known 2017 hierarchy")

    match = _RANGE_RE.fullmatch(compact)
    if match is None:
        return _unresolved(raw_reference, "unsupported NEC reference form")

    start_locator = canonical_nec_locator(match.group("start"))
    marker_start = start_locator.rfind("(")
    prefix = start_locator[:marker_start]
    start_value = start_locator[marker_start + 1 : -1]
    values = _range_values(start_value, match.group("end"))
    if values is None:
        return _unresolved(raw_reference, "range endpoints are incompatible or descending")

    candidates = tuple(canonical_nec_locator(f"{prefix}({value})") for value in values)
    missing = tuple(locator for locator in candidates if locator not in known)
    if missing:
        return _unresolved(
            raw_reference,
            "range member absent from the known 2017 hierarchy: " + ", ".join(missing),
        )
    return ResolvedReference(raw_reference, candidates, "sibling-range", 1.0)


_POSITIVE_DISPOSITIONS = frozenset(
    {
        DevelopmentDisposition.ACCEPTED,
        DevelopmentDisposition.ACCEPTED_IN_PRINCIPLE,
        DevelopmentDisposition.ACCEPTED_IN_PART,
        DevelopmentDisposition.ISSUED,
        DevelopmentDisposition.CORRECTED,
    }
)
_NEGATIVE_DISPOSITIONS = frozenset(
    {
        DevelopmentDisposition.REJECTED,
        DevelopmentDisposition.WITHDRAWN,
        DevelopmentDisposition.FAILED_BALLOT,
        DevelopmentDisposition.RETURNED_TO_PRIOR_EDITION,
    }
)


def _expected_disposition(value: DevelopmentDisposition) -> ExpectedDisposition:
    if value in _POSITIVE_DISPOSITIONS:
        return ExpectedDisposition.CHANGE_EXPECTED
    if value in _NEGATIVE_DISPOSITIONS:
        return ExpectedDisposition.NO_CHANGE_EXPECTED
    return ExpectedDisposition.UNCERTAIN


def _confidence(stage: DevelopmentStage, unresolved: bool) -> ExpectationConfidence:
    if unresolved:
        return ExpectationConfidence.LOW
    if stage in {
        DevelopmentStage.STANDARDS_COUNCIL,
        DevelopmentStage.TIA,
        DevelopmentStage.ERRATUM,
    }:
        return ExpectationConfidence.HIGH
    if stage in {
        DevelopmentStage.SECOND_REVISION,
        DevelopmentStage.TECHNICAL_MEETING,
    }:
        return ExpectationConfidence.MEDIUM
    return ExpectationConfidence.LOW


def _target_reference(value: str) -> str:
    compact = _SECTION_PREFIX_RE.sub("", value.strip())
    try:
        return canonical_nec_locator(compact)
    except ValueError:
        return value.strip()


def _controlling_signature(record: DevelopmentRecord) -> tuple[Any, ...]:
    return (
        record.disposition,
        record.affected_references_raw,
        record.target_references_raw,
        record.change_types,
    )


def project_expected_changes(
    records: Sequence[DevelopmentRecord],
    known_locators: Iterable[str],
) -> tuple[ExpectedChange, ...]:
    """Project one expected outcome per procedural change chain."""

    record_ids = [record.record_id for record in records]
    if len(record_ids) != len(set(record_ids)):
        raise ValueError("development record IDs must be unique")

    known = tuple(known_locators)
    grouped: dict[str, list[DevelopmentRecord]] = defaultdict(list)
    for record in records:
        grouped[record.change_chain_id].append(record)

    expectations: list[ExpectedChange] = []
    for chain_id in sorted(grouped):
        chain = sorted(
            grouped[chain_id],
            key=lambda item: (_STAGE_RANK[item.stage], item.record_id),
        )
        controlling_rank = max(_STAGE_RANK[item.stage] for item in chain)
        controlling_candidates = [
            item for item in chain if _STAGE_RANK[item.stage] == controlling_rank
        ]
        signatures = {_controlling_signature(item) for item in controlling_candidates}
        if len(signatures) != 1:
            ids = ", ".join(item.record_id for item in controlling_candidates)
            raise ValueError(
                f"conflicting controlling records for change chain {chain_id}: {ids}"
            )
        controlling = controlling_candidates[-1]

        resolved: list[str] = []
        unresolved: list[str] = []
        for raw_reference in controlling.affected_references_raw:
            result = resolve_nec_reference(raw_reference, known)
            resolved.extend(result.resolved_locators)
            if not result.resolved_locators:
                unresolved.append(raw_reference)

        disposition = _expected_disposition(controlling.disposition)
        change_types = (
            (ChangeType.NO_FINAL_CHANGE,)
            if disposition == ExpectedDisposition.NO_CHANGE_EXPECTED
            else controlling.change_types or (ChangeType.UNKNOWN,)
        )
        expectations.append(
            ExpectedChange(
                expectation_id=f"exp:{chain_id}",
                change_chain_id=chain_id,
                from_locators=_dedupe(resolved),
                expected_target_references=_dedupe(
                    _target_reference(value)
                    for value in controlling.target_references_raw
                ),
                unresolved_references=_dedupe(unresolved),
                change_types=change_types,
                summary=controlling.summary,
                disposition=disposition,
                confidence=_confidence(controlling.stage, bool(unresolved)),
                controlling_record_id=controlling.record_id,
                supporting_record_ids=tuple(item.record_id for item in chain),
            )
        )
    return tuple(expectations)


def _matches(expectation: ExpectedChange, observed: ObservedChange) -> bool:
    from_overlap = set(expectation.from_locators) & set(observed.from_locators)
    target_overlap = set(expectation.expected_target_references) & set(
        observed.to_locators
    )
    return bool(from_overlap or target_overlap)


def reconcile_changes(
    expectations: Sequence[ExpectedChange],
    observed_changes: Sequence[ObservedChange],
) -> tuple[Reconciliation, ...]:
    """Compare expected process outcomes with an independent edition diff."""

    observed_ids = [item.observed_change_id for item in observed_changes]
    if len(observed_ids) != len(set(observed_ids)):
        raise ValueError("observed change IDs must be unique")

    reconciliations: list[Reconciliation] = []
    consumed: set[str] = set()
    for expectation in expectations:
        candidates = tuple(
            item for item in observed_changes if _matches(expectation, item)
        )
        candidate_ids = tuple(item.observed_change_id for item in candidates)
        consumed.update(candidate_ids)

        if expectation.disposition == ExpectedDisposition.NO_CHANGE_EXPECTED:
            if candidates:
                outcome = ReconciliationOutcome.CONTRADICTED
                message = "A change was observed where the development record predicts no final change."
            else:
                outcome = ReconciliationOutcome.CONFIRMED
                message = "No change was observed, consistent with the negative expectation."
        elif expectation.disposition == ExpectedDisposition.UNCERTAIN:
            outcome = ReconciliationOutcome.AMBIGUOUS
            message = "The controlling development record does not establish final disposition."
        elif not candidates:
            outcome = ReconciliationOutcome.EXPECTED_NOT_OBSERVED
            message = "The expected change was not found in the observed edition diff."
        else:
            expected_types = set(expectation.change_types)
            observed_types = {
                change_type for item in candidates for change_type in item.change_types
            }
            if expected_types & observed_types or ChangeType.UNKNOWN in expected_types:
                outcome = ReconciliationOutcome.CONFIRMED
                message = "The observed edition diff confirms the expected change."
            else:
                outcome = ReconciliationOutcome.AMBIGUOUS
                message = "The affected provisions align, but the change classifications differ."

        reconciliations.append(
            Reconciliation(
                reconciliation_id=f"rec:{expectation.change_chain_id}",
                expectation_id=expectation.expectation_id,
                observed_change_ids=candidate_ids,
                outcome=outcome,
                message=message,
            )
        )

    for observed in observed_changes:
        if observed.observed_change_id in consumed:
            continue
        reconciliations.append(
            Reconciliation(
                reconciliation_id=f"rec:unexpected:{observed.observed_change_id}",
                expectation_id=None,
                observed_change_ids=(observed.observed_change_id,),
                outcome=ReconciliationOutcome.UNEXPECTED_OBSERVED,
                message="The observed edition diff has no matching development expectation.",
            )
        )

    return tuple(reconciliations)
