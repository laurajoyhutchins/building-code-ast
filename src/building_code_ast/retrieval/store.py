"""Replaceable local SQLite persistence for retrieval source evidence.

The database is disposable derived state. Source authority remains outside this
module, and every read reconstructs the shared evidence model so stored identity
tampering fails closed.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Iterable

from .model import SourceArtifactIdentity, SourceEvidence


SOURCE_EVIDENCE_STORE_VERSION = "source-evidence-store/0.1.0"

_SCHEMA = """
CREATE TABLE artifact_manifest (
    schema_version TEXT NOT NULL,
    source_id TEXT NOT NULL,
    publication_key TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    source_size INTEGER NOT NULL,
    page_count INTEGER NOT NULL,
    evidence_count INTEGER NOT NULL
);
CREATE TABLE evidence (
    evidence_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    publication_key TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    pdf_page INTEGER NOT NULL,
    printed_page TEXT,
    block_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    bbox_x0 REAL,
    bbox_y0 REAL,
    bbox_x1 REAL,
    bbox_y1 REAL,
    extraction_method TEXT NOT NULL,
    observed_metadata TEXT NOT NULL,
    derived_metadata TEXT NOT NULL
);
CREATE INDEX evidence_source_order
    ON evidence(pdf_page, block_index, evidence_id);
"""


def rebuild_evidence_store(
    path: Path | str,
    *,
    artifact: SourceArtifactIdentity,
    evidence: Iterable[SourceEvidence],
) -> None:
    """Atomically replace a local evidence store from validated derived records."""

    if not isinstance(artifact, SourceArtifactIdentity):
        raise ValueError("artifact must be a SourceArtifactIdentity")

    records = tuple(evidence)
    seen_ids: set[str] = set()
    for item in records:
        if not isinstance(item, SourceEvidence):
            raise ValueError("evidence must contain SourceEvidence values")
        if (
            item.source_id != artifact.source_id
            or item.publication_key != artifact.publication_key
            or item.source_sha256 != artifact.sha256
            or item.pdf_page > artifact.page_count
        ):
            raise ValueError("evidence source identity does not match artifact")
        if item.evidence_id in seen_ids:
            raise ValueError(f"duplicate evidence_id: {item.evidence_id}")
        seen_ids.add(item.evidence_id)

    ordered = tuple(sorted(records, key=lambda item: (item.pdf_page, item.block_index, item.evidence_id)))
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    os.close(descriptor)
    temporary = Path(temp_name)

    try:
        with sqlite3.connect(temporary) as database:
            database.executescript(_SCHEMA)
            database.execute(
                """
                INSERT INTO artifact_manifest (
                    schema_version, source_id, publication_key, source_sha256,
                    source_size, page_count, evidence_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    SOURCE_EVIDENCE_STORE_VERSION,
                    artifact.source_id,
                    artifact.publication_key,
                    artifact.sha256,
                    artifact.size,
                    artifact.page_count,
                    len(ordered),
                ),
            )
            for item in ordered:
                if item.bbox is None:
                    bbox = (None, None, None, None)
                else:
                    bbox = item.bbox
                database.execute(
                    """
                    INSERT INTO evidence (
                        evidence_id, source_id, publication_key, source_sha256,
                        pdf_page, printed_page, block_index, text,
                        bbox_x0, bbox_y0, bbox_x1, bbox_y1,
                        extraction_method, observed_metadata, derived_metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.evidence_id,
                        item.source_id,
                        item.publication_key,
                        item.source_sha256,
                        item.pdf_page,
                        item.printed_page,
                        item.block_index,
                        item.text,
                        *bbox,
                        item.extraction_method,
                        _metadata_json(item.observed_metadata),
                        _metadata_json(item.derived_metadata),
                    ),
                )
            database.commit()
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def read_evidence_store(
    path: Path | str,
    *,
    artifact: SourceArtifactIdentity,
) -> tuple[SourceEvidence, ...]:
    """Read and validate a disposable evidence store for one exact artifact."""

    if not isinstance(artifact, SourceArtifactIdentity):
        raise ValueError("artifact must be a SourceArtifactIdentity")
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)

    try:
        with sqlite3.connect(source) as database:
            manifest_rows = database.execute(
                """
                SELECT schema_version, source_id, publication_key, source_sha256,
                       source_size, page_count, evidence_count
                FROM artifact_manifest
                """
            ).fetchall()
            if len(manifest_rows) != 1:
                raise ValueError("artifact manifest must contain exactly one row")
            manifest = manifest_rows[0]
            expected_manifest = (
                SOURCE_EVIDENCE_STORE_VERSION,
                artifact.source_id,
                artifact.publication_key,
                artifact.sha256,
                artifact.size,
                artifact.page_count,
            )
            if manifest[:6] != expected_manifest:
                raise ValueError("artifact manifest does not match requested source artifact")

            rows = database.execute(
                """
                SELECT evidence_id, source_id, publication_key, source_sha256,
                       pdf_page, printed_page, block_index, text,
                       bbox_x0, bbox_y0, bbox_x1, bbox_y1,
                       extraction_method, observed_metadata, derived_metadata
                FROM evidence
                ORDER BY pdf_page, block_index, evidence_id
                """
            ).fetchall()
            if manifest[6] != len(rows):
                raise ValueError("artifact manifest evidence_count does not match stored rows")
    except sqlite3.DatabaseError as exc:
        raise ValueError("invalid source evidence SQLite store") from exc

    restored: list[SourceEvidence] = []
    for row in rows:
        (
            evidence_id,
            source_id,
            publication_key,
            source_sha256,
            pdf_page,
            printed_page,
            block_index,
            text,
            x0,
            y0,
            x1,
            y1,
            extraction_method,
            observed_json,
            derived_json,
        ) = row
        if (source_id, publication_key, source_sha256) != (
            artifact.source_id,
            artifact.publication_key,
            artifact.sha256,
        ):
            raise ValueError("stored evidence source identity does not match artifact manifest")

        bbox_values = (x0, y0, x1, y1)
        if all(value is None for value in bbox_values):
            bbox = None
        elif any(value is None for value in bbox_values):
            raise ValueError("stored evidence bbox must be wholly present or absent")
        else:
            bbox = tuple(float(value) for value in bbox_values)

        restored.append(
            SourceEvidence(
                evidence_id=str(evidence_id),
                source_id=str(source_id),
                publication_key=str(publication_key),
                source_sha256=str(source_sha256),
                pdf_page=int(pdf_page),
                block_index=int(block_index),
                text=str(text),
                bbox=bbox,
                extraction_method=str(extraction_method),
                printed_page=None if printed_page is None else str(printed_page),
                observed_metadata=_metadata_items(observed_json, "observed_metadata"),
                derived_metadata=_metadata_items(derived_json, "derived_metadata"),
            )
        )
    return tuple(restored)


def _metadata_json(items: tuple[tuple[str, object], ...]) -> str:
    return json.dumps(
        dict(items),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        ensure_ascii=False,
    )


def _metadata_items(value: object, label: str) -> tuple[tuple[str, object], ...]:
    if not isinstance(value, str):
        raise ValueError(f"stored {label} must be JSON text")
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"stored {label} is invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"stored {label} must decode to an object")
    return tuple(sorted(payload.items()))
