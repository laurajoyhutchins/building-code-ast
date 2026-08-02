"""Versioned NEC-specific definition and section-review contracts.

These values preserve evidence and uncertainty. They do not represent project
applicability or compliance conclusions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import json
from typing import Any, Mapping

from ..document_model import DocumentSourceArtifact
from ..model import Diagnostic, SourceSpan


DEFINITION_INDEX_VERSION = "0.1.0"
SECTION_REVIEW_VERSION = "0.1.0"
LANGUAGE_PROFILE_VERSION = "0.1.0"


class DefinitionFragmentKind(StrEnum):
    BODY = "body"
    CONTINUATION = "continuation"
    LIST_ITEM = "list_item"
    NOTE = "note"


class DefinitionQualifierKind(StrEnum):
    APPLICABILITY = "applicability"
    SCOPE = "scope"


class CodeReferenceKind(StrEnum):
    SECTION = "section"
    ARTICLE = "article"
    TABLE = "table"


class ReviewedModality(StrEnum):
    REQUIREMENT = "requirement"
    PROHIBITION = "prohibition"
    PERMISSION = "permission"
    NONREQUIREMENT = "nonrequirement"
    UNKNOWN = "unknown"


class LanguageCategory(StrEnum):
    MANDATORY = "mandatory"
    PERMISSIVE = "permissive"
    EXPLANATORY = "explanatory"
    NONMANDATORY = "nonmandatory"


@dataclass(frozen=True, slots=True)
class DefinitionQualifier:
    kind: DefinitionQualifierKind
    text: str
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "text": self.text,
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class DefinitionFragment:
    kind: DefinitionFragmentKind
    node_locator: str
    node_type: str
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "node_locator": self.node_locator,
            "node_type": self.node_type,
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class CodeReference:
    kind: CodeReferenceKind
    target: str
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "target": self.target,
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class DefinitionEntry:
    definition_id: str
    source_locator: str
    display_term: str
    canonical_term: str
    term_span: SourceSpan
    alternate_terms: tuple[SourceSpan, ...]
    qualifiers: tuple[DefinitionQualifier, ...]
    body_fragments: tuple[DefinitionFragment, ...]
    notes: tuple[DefinitionFragment, ...]
    code_making_panels: tuple[SourceSpan, ...]
    references: tuple[CodeReference, ...]
    source_span: SourceSpan
    diagnostics: tuple[Diagnostic, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "definition_id": self.definition_id,
            "source_locator": self.source_locator,
            "display_term": self.display_term,
            "canonical_term": self.canonical_term,
            "term_span": self.term_span.to_dict(),
            "alternate_terms": [item.to_dict() for item in self.alternate_terms],
            "qualifiers": [item.to_dict() for item in self.qualifiers],
            "body_fragments": [item.to_dict() for item in self.body_fragments],
            "notes": [item.to_dict() for item in self.notes],
            "code_making_panels": [item.to_dict() for item in self.code_making_panels],
            "references": [item.to_dict() for item in self.references],
            "source_span": self.source_span.to_dict(),
            "diagnostics": [item.to_dict() for item in self.diagnostics],
        }


@dataclass(frozen=True, slots=True)
class DefinitionIndex:
    source_text: str
    source_artifact: DocumentSourceArtifact
    article_locator: str
    entries: tuple[DefinitionEntry, ...]
    diagnostics: tuple[Diagnostic, ...] = ()
    index_version: str = field(default=DEFINITION_INDEX_VERSION, init=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index_version": self.index_version,
            "type": "nec_definition_index",
            "source_text": self.source_text,
            "source_artifact": self.source_artifact.to_dict(),
            "article_locator": self.article_locator,
            "entries": [entry.to_dict() for entry in self.entries],
            "diagnostics": [item.to_dict() for item in self.diagnostics],
        }


@dataclass(frozen=True, slots=True)
class SourceNodeProjection:
    locator: str
    node_type: str
    label: str | None
    span: SourceSpan
    attributes: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "locator": self.locator,
            "node_type": self.node_type,
            "label": self.label,
            "span": self.span.to_dict(),
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True, slots=True)
class ReviewedClause:
    clause_id: str
    modality: ReviewedModality
    span: SourceSpan
    modal_span: SourceSpan | None
    subject_span: SourceSpan | None
    predicate_span: SourceSpan | None
    condition_span: SourceSpan | None
    semantic_tags: tuple[str, ...]
    definition_ids: tuple[str, ...]
    references: tuple[CodeReference, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "clause_id": self.clause_id,
            "modality": self.modality.value,
            "span": self.span.to_dict(),
            "modal_span": self.modal_span.to_dict() if self.modal_span else None,
            "subject_span": self.subject_span.to_dict() if self.subject_span else None,
            "predicate_span": self.predicate_span.to_dict() if self.predicate_span else None,
            "condition_span": self.condition_span.to_dict() if self.condition_span else None,
            "semantic_tags": list(self.semantic_tags),
            "definition_ids": list(self.definition_ids),
            "references": [item.to_dict() for item in self.references],
        }


@dataclass(frozen=True, slots=True)
class ReviewedException:
    exception_id: str
    span: SourceSpan
    modality: ReviewedModality
    modal_span: SourceSpan | None
    condition_span: SourceSpan | None
    references: tuple[CodeReference, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "exception_id": self.exception_id,
            "span": self.span.to_dict(),
            "modality": self.modality.value,
            "modal_span": self.modal_span.to_dict() if self.modal_span else None,
            "condition_span": self.condition_span.to_dict() if self.condition_span else None,
            "references": [item.to_dict() for item in self.references],
        }


@dataclass(frozen=True, slots=True)
class ReviewedNote:
    note_id: str
    label: str
    span: SourceSpan
    references: tuple[CodeReference, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "note_id": self.note_id,
            "label": self.label,
            "span": self.span.to_dict(),
            "references": [item.to_dict() for item in self.references],
        }


@dataclass(frozen=True, slots=True)
class SectionReview:
    source_text: str
    source_artifact: DocumentSourceArtifact
    article_locator: str
    article_start: int
    article_end: int
    section_locator: str
    title: str
    title_span: SourceSpan
    source_nodes: tuple[SourceNodeProjection, ...]
    clauses: tuple[ReviewedClause, ...]
    exceptions: tuple[ReviewedException, ...]
    notes: tuple[ReviewedNote, ...]
    references: tuple[CodeReference, ...]
    diagnostics: tuple[Diagnostic, ...] = ()
    review_version: str = field(default=SECTION_REVIEW_VERSION, init=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_version": self.review_version,
            "type": "nec_section_review",
            "source_text": self.source_text,
            "source_artifact": self.source_artifact.to_dict(),
            "article_locator": self.article_locator,
            "article_span": {"start": self.article_start, "end": self.article_end},
            "section_locator": self.section_locator,
            "title": self.title,
            "title_span": self.title_span.to_dict(),
            "source_nodes": [item.to_dict() for item in self.source_nodes],
            "clauses": [item.to_dict() for item in self.clauses],
            "exceptions": [item.to_dict() for item in self.exceptions],
            "notes": [item.to_dict() for item in self.notes],
            "references": [item.to_dict() for item in self.references],
            "diagnostics": [item.to_dict() for item in self.diagnostics],
        }


@dataclass(frozen=True, slots=True)
class LanguageEvidence:
    category: LanguageCategory
    phrase: str
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "phrase": self.phrase,
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class NecLanguageProfile:
    source_locator: str
    mandatory_phrases: tuple[str, ...]
    permissive_phrases: tuple[str, ...]
    explanatory_markers: tuple[str, ...]
    nonmandatory_markers: tuple[str, ...]
    evidence: tuple[LanguageEvidence, ...]
    profile_version: str = field(default=LANGUAGE_PROFILE_VERSION, init=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_version": self.profile_version,
            "type": "nec_language_profile",
            "source_locator": self.source_locator,
            "mandatory_phrases": list(self.mandatory_phrases),
            "permissive_phrases": list(self.permissive_phrases),
            "explanatory_markers": list(self.explanatory_markers),
            "nonmandatory_markers": list(self.nonmandatory_markers),
            "evidence": [item.to_dict() for item in self.evidence],
        }


def _stable_id(prefix: str, payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"{prefix}:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def definition_entry_id(
    source_artifact: DocumentSourceArtifact,
    source_locator: str,
) -> str:
    return _stable_id(
        "necdef",
        {
            "artifact_id": source_artifact.artifact_id,
            "edition_id": source_artifact.edition_id,
            "source_locator": source_locator,
        },
    )


def reviewed_clause_id(
    source_artifact: DocumentSourceArtifact,
    section_locator: str,
    start: int,
    end: int,
) -> str:
    return _stable_id(
        "necclause",
        {
            "artifact_id": source_artifact.artifact_id,
            "edition_id": source_artifact.edition_id,
            "section_locator": section_locator,
            "start": start,
            "end": end,
        },
    )


def reviewed_exception_id(
    source_artifact: DocumentSourceArtifact,
    section_locator: str,
    start: int,
    end: int,
) -> str:
    return _stable_id(
        "necexception",
        {
            "artifact_id": source_artifact.artifact_id,
            "edition_id": source_artifact.edition_id,
            "section_locator": section_locator,
            "start": start,
            "end": end,
        },
    )


def reviewed_note_id(
    source_artifact: DocumentSourceArtifact,
    section_locator: str,
    start: int,
    end: int,
) -> str:
    return _stable_id(
        "necnote",
        {
            "artifact_id": source_artifact.artifact_id,
            "edition_id": source_artifact.edition_id,
            "section_locator": section_locator,
            "start": start,
            "end": end,
        },
    )
