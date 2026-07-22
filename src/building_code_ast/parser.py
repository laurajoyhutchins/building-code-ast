"""Deterministic parser for the initial bounded provision grammar."""

from __future__ import annotations

import re

from .model import (
    Action,
    ComparisonCondition,
    Diagnostic,
    DiagnosticSeverity,
    Modality,
    ProvisionAst,
    Quantity,
    SectionReference,
    SourceArtifact,
    SourceSpan,
)
from .validation import validate_ast

_MODAL_PATTERN = re.compile(
    r"\b(?P<modal>shall\s+not|must\s+not|may\s+not|shall|must|may)\b",
    re.IGNORECASE,
)

_THRESHOLD_PATTERN = re.compile(
    r"(?P<marker>exceeding|greater\s+than|more\s+than|at\s+least|not\s+less\s+than)\s+"
    r"(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>feet|foot|ft|inches|inch|in|square\s+feet|sq\.?\s*ft)"
    r"(?:\s+in)?\s+(?P<property>[A-Za-z][A-Za-z -]*?)$",
    re.IGNORECASE,
)

_EXCEPTION_PATTERN = re.compile(
    r",?\s*except\s+as\s+(?:provided|permitted|required)\s+(?:for\s+)?(?:in|by)\s+"
    r"Section\s+(?P<section>[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*(?:\([A-Za-z0-9]+\))*)\.?$",
    re.IGNORECASE,
)

_ACTION_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^provide\s+(?P<object>.+)$", re.IGNORECASE), "provide"),
    (re.compile(r"^have\s+(?P<object>.+)$", re.IGNORECASE), "have"),
    (re.compile(r"^maintain\s+(?P<object>.+)$", re.IGNORECASE), "maintain"),
    (re.compile(r"^be\s+equipped(?:\s+throughout)?\s+with\s+(?P<object>.+)$", re.IGNORECASE), "equip"),
    (re.compile(r"^be\s+installed\s+(?P<object>.+)$", re.IGNORECASE), "install"),
)

_UNIT_NORMALIZATION = {
    "feet": "ft",
    "foot": "ft",
    "ft": "ft",
    "inches": "in",
    "inch": "in",
    "in": "in",
    "square feet": "ft2",
    "sq ft": "ft2",
    "sq. ft": "ft2",
}

_OPERATOR_BY_MARKER = {
    "exceeding": ">",
    "greater than": ">",
    "more than": ">",
    "at least": ">=",
    "not less than": ">=",
}


def _span(source: str, start: int, end: int) -> SourceSpan:
    return SourceSpan(start=start, end=end, text=source[start:end])


def _trimmed_bounds(source: str, start: int, end: int) -> tuple[int, int]:
    while start < end and source[start].isspace():
        start += 1
    while end > start and source[end - 1].isspace():
        end -= 1
    return start, end


def _modality(modal: str) -> Modality:
    normalized = " ".join(modal.lower().split())
    if normalized in {"shall", "must"}:
        return Modality.REQUIREMENT
    if normalized in {"shall not", "must not", "may not"}:
        return Modality.PROHIBITION
    if normalized == "may":
        return Modality.PERMISSION
    return Modality.UNKNOWN


def _extract_exception(source: str, action_start: int, action_text: str) -> tuple[str, tuple[SectionReference, ...]]:
    match = _EXCEPTION_PATTERN.search(action_text)
    if not match:
        return action_text.rstrip(), ()

    section_start = action_start + match.start("section")
    section_end = action_start + match.end("section")
    exception = SectionReference(
        section=match.group("section"),
        span=_span(source, section_start, section_end),
    )
    core_action = action_text[: match.start()].rstrip().rstrip(",").rstrip().rstrip(".")
    return core_action, (exception,)


def _extract_condition(
    source: str, subject_start: int, subject_text: str
) -> tuple[str, SourceSpan | None, tuple[ComparisonCondition, ...]]:
    match = _THRESHOLD_PATTERN.search(subject_text)
    if not match:
        subject_end = subject_start + len(subject_text)
        return subject_text, _span(source, subject_start, subject_end) if subject_text else None, ()

    condition_start = subject_start + match.start("marker")
    condition_end = subject_start + match.end("property")
    marker = " ".join(match.group("marker").lower().split())
    raw_unit = " ".join(match.group("unit").lower().replace(".", "").split())
    property_text = " ".join(match.group("property").lower().split())

    condition = ComparisonCondition(
        subject_property=property_text,
        operator=_OPERATOR_BY_MARKER[marker],
        threshold=Quantity(
            value=float(match.group("value")),
            unit=_UNIT_NORMALIZATION[raw_unit],
            original_text=match.group(0),
        ),
        span=_span(source, condition_start, condition_end),
    )
    subject_end = subject_start + match.start()
    subject_start, subject_end = _trimmed_bounds(source, subject_start, subject_end)
    regulated_subject = source[subject_start:subject_end]
    return regulated_subject, _span(source, subject_start, subject_end) if regulated_subject else None, (condition,)


def _parse_action(source: str, action_start: int, action_text: str) -> tuple[Action, tuple[Diagnostic, ...]]:
    diagnostics: list[Diagnostic] = []
    normalized_verb: str | None = None
    object_text: str | None = None

    for pattern, verb in _ACTION_PATTERNS:
        match = pattern.match(action_text)
        if match:
            normalized_verb = verb
            object_text = match.group("object").strip().rstrip(".")
            break

    if normalized_verb is None:
        diagnostics.append(
            Diagnostic(
                code="unsupported-action-shape",
                severity=DiagnosticSeverity.WARNING,
                message="The action text was preserved but not normalized into a known verb/object shape.",
                span=_span(source, action_start, action_start + len(action_text)),
            )
        )

    return (
        Action(
            text=action_text,
            normalized_verb=normalized_verb,
            object_text=object_text,
            span=_span(source, action_start, action_start + len(action_text)),
        ),
        tuple(diagnostics),
    )


def parse_provision(
    source_text: str,
    *,
    source_artifact_id: str = "inline",
    provision_locator: str = "inline",
) -> ProvisionAst:
    """Parse one provision from the initial bounded grammar.

    Offsets always address the exact ``source_text`` supplied by the caller.
    Source identity and provision location distinguish identical text from
    different artifacts or editions.
    """

    if not source_text.strip():
        raise ValueError("source_text must not be empty")
    if not source_artifact_id.strip():
        raise ValueError("source_artifact_id must not be empty")
    if not provision_locator.strip():
        raise ValueError("provision_locator must not be empty")

    source = source_text
    source_artifact = SourceArtifact(
        artifact_id=source_artifact_id,
        provision_locator=provision_locator,
    )
    content_start, content_end = _trimmed_bounds(source, 0, len(source))
    modal_match = _MODAL_PATTERN.search(source, content_start, content_end)
    if modal_match is None:
        action = Action(
            text=source[content_start:content_end],
            normalized_verb=None,
            object_text=None,
            span=_span(source, content_start, content_end),
        )
        ast = ProvisionAst(
            source_text=source,
            source_artifact=source_artifact,
            modality=Modality.UNKNOWN,
            modality_span=None,
            subject="",
            subject_span=None,
            action=action,
            source_span=_span(source, 0, len(source)),
            diagnostics=(
                Diagnostic(
                    code="missing-modality",
                    severity=DiagnosticSeverity.ERROR,
                    message="No supported requirement, prohibition, or permission modal was found.",
                    span=_span(source, content_start, content_end),
                ),
            ),
        )
        validate_ast(ast)
        return ast

    subject_start, subject_end = _trimmed_bounds(source, content_start, modal_match.start())
    raw_subject = source[subject_start:subject_end]

    action_start, action_end = _trimmed_bounds(source, modal_match.end(), content_end)
    raw_action = source[action_start:action_end]

    action_text, exceptions = _extract_exception(source, action_start, raw_action)
    subject, subject_span, conditions = _extract_condition(source, subject_start, raw_subject)
    action, action_diagnostics = _parse_action(source, action_start, action_text)

    diagnostics = list(action_diagnostics)
    if not conditions:
        diagnostics.append(
            Diagnostic(
                code="no-structured-condition",
                severity=DiagnosticSeverity.INFO,
                message="No supported numeric threshold condition was found; the subject was preserved as written.",
                span=_span(source, subject_start, subject_end),
            )
        )

    ast = ProvisionAst(
        source_text=source,
        source_artifact=source_artifact,
        modality=_modality(modal_match.group("modal")),
        modality_span=_span(source, modal_match.start("modal"), modal_match.end("modal")),
        subject=subject,
        subject_span=subject_span,
        conditions=conditions,
        action=action,
        exceptions=exceptions,
        diagnostics=tuple(diagnostics),
        source_span=_span(source, 0, len(source)),
    )
    validate_ast(ast)
    return ast
