#!/usr/bin/env python3
"""Build source-safe 2018 IBC inventory artifacts from private page evidence."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from building_code_ast.ibc2018_corpus import (
    CORPUS_SCHEMA_VERSION,
    COUNTING_POLICY_VERSION,
    ReviewState,
    SOURCE_SHA256,
    attach_figure_context,
    attach_reference_relationships,
    attach_table_context,
    build_attachment_inventory,
    build_coverage_report,
    build_cross_reference_summary,
    build_detection_inventory,
    build_reference_crosschecks,
    build_semantic_pilot,
    build_source_manifest,
    classify_figures,
    classify_tables,
    inventory_captions,
    inventory_chapter35,
    inventory_cross_references,
    inventory_definitions,
    inventory_diagrams,
    inventory_equations,
    inventory_exceptions,
    inventory_external_citations,
    inventory_incidental_layouts,
    load_page_lines,
    normalize_external_families,
    printed_page,
    publication_context,
    stable_id,
    validate_inventory,
    validate_private_evidence_identity,
)
from building_code_ast.evidence.model import (
    AccessScope,
    AstSourceIdentity,
    EvidenceRole,
    PublicationIdentity,
    RightsStatus,
    SourceRegister,
    SourceRegisterEntry,
)

PARSER_VERSION = "ibc-2018-corpus-builder/0.1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--page-lines", type=Path, required=True)
    parser.add_argument("--chapter-2-seed", type=Path, required=True)
    parser.add_argument("--image-regions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--generated-at", default="2026-08-03T19:30:00Z")
    return parser.parse_args()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_csv(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    fields = sorted({key for record in records for key in record})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow({field: scalar(record.get(field)) for field in fields})


def write_inventory_markdown(path: Path, title: str, records: Sequence[Mapping[str, Any]]) -> None:
    by_state: dict[str, int] = {}
    for record in records:
        state = str(record.get("review_state", "unknown"))
        by_state[state] = by_state.get(state, 0) + 1
    lines = [f"# {title}", "", f"Total records: **{len(records)}**.", "", "## Review states", ""]
    for state, count in sorted(by_state.items()):
        lines.append(f"- `{state}`: {count}")
    lines.extend(["", "## Records", "", "| ID | Published identifier / term | PDF page | State |", "|---|---|---:|---|"])
    for record in records:
        anchor = record.get("source_anchor") or (record.get("anchors") or [{}])[0]
        label = (
            record.get("published_identifier")
            or record.get("observed_term")
            or record.get("observed_designation_with_edition")
            or record.get("equation_identifier")
            or record.get("parent_locator")
            or ""
        )
        lines.append(
            f"| `{record['id']}` | {str(label).replace('|', '\\|')} | {anchor.get('pdf_page', '')} | `{record.get('review_state', '')}` |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    pages = load_page_lines(args.page_lines)
    chapter2_seed = json.loads(args.chapter_2_seed.read_text(encoding="utf-8"))
    image_regions = json.loads(args.image_regions.read_text(encoding="utf-8"))
    validate_private_evidence_identity(pages, chapter2_seed, image_regions)

    source_manifest = build_source_manifest(
        pdf_metadata={
            "format": "PDF 1.7",
            "title": "",
            "author": "",
            "subject": "",
            "keywords": "",
            "creator": "VeryDOC PS to PDF Converter Command Line, Build: Aug  7 2016",
            "producer": "VeryDOC PS to PDF Converter Command Line (http://www.verydoc.com)",
            "creation_date": "2017-11-20T21:48:22+05:00",
            "modification_date": "2020-09-05T14:39:04+04:30",
            "xmp_toolkit": "NitroPro",
            "tagged": False,
            "optimized": False,
            "page_size_points": [612, 792],
            "outline_entry_count": 0,
        },
        ingestion_timestamp=args.generated_at,
        parser_version=PARSER_VERSION,
    )

    tables = inventory_captions(pages, "table")
    classify_tables(tables)
    figures = inventory_captions(pages, "figure")
    classify_figures(figures)
    diagrams = inventory_diagrams(pages, image_regions, figures)
    equations = inventory_equations(pages, tables, figures)
    definitions = inventory_definitions(pages, chapter2_seed)
    exceptions = inventory_exceptions(pages)
    attach_table_context(pages, tables, exceptions)
    attach_figure_context(pages, figures, exceptions)
    chapter35 = inventory_chapter35(pages)
    external_families = normalize_external_families(chapter35)
    external_citations, unmatched_citations = inventory_external_citations(pages, chapter35)
    cross_references = inventory_cross_references(pages, tables, figures, equations)
    attach_reference_relationships(
        tables, figures, equations, exceptions, cross_references, external_citations
    )
    incidental = inventory_incidental_layouts(pages, tables, figures)
    semantic_pilot = build_semantic_pilot(tables, figures, equations, chapter35, definitions, exceptions)
    detections = build_detection_inventory(pages, tables, figures, incidental, equations, diagrams)
    attachments = build_attachment_inventory(tables, figures, equations, exceptions)
    reference_crosschecks = build_reference_crosschecks(chapter35, external_families, external_citations)
    cross_reference_summary = build_cross_reference_summary(cross_references)

    inventories: dict[str, Sequence[Mapping[str, Any]]] = {
        "tables": tables,
        "incidental_layouts": incidental,
        "figures": figures,
        "diagrams": diagrams,
        "equations": equations,
        "definitions": definitions,
        "exceptions": exceptions,
        "chapter35_rows": chapter35,
        "external_families": external_families,
        "external_citations": external_citations,
        "cross_references": cross_references,
        "semantic_pilot": semantic_pilot,
        "detections": detections,
        "attachments": attachments,
    }
    coverage = build_coverage_report(
        inventories, cross_references, chapter35, external_families, external_citations
    )
    discrepancies = validate_inventory(source_manifest, inventories)
    review_queue = [
        {
            "record_id": record["id"],
            "record_type": record["record_type"],
            "review_state": record.get("review_state", ReviewState.PROVISIONAL.value),
            "reason": "provisional_or_disputed_inventory_record",
        }
        for records in inventories.values()
        for record in records
        if record.get("review_state") in {ReviewState.PROVISIONAL.value, ReviewState.DISPUTED.value}
    ]
    review_queue.extend(
        {
            "record_id": item.get("record_id", stable_id("discrepancy", json.dumps(item, sort_keys=True))),
            "record_type": "discrepancy",
            "review_state": ReviewState.DISPUTED.value,
            "reason": item["code"],
        }
        for item in discrepancies
    )

    counts = coverage["counts"]
    corpus_manifest = {
        "schema_version": CORPUS_SCHEMA_VERSION,
        "record_type": "corpus_manifest",
        "corpus_id": "icc:ibc:2018:structural-inventory",
        "source_sha256": SOURCE_SHA256,
        "counting_policy_version": COUNTING_POLICY_VERSION,
        "parser_version": PARSER_VERSION,
        "generated_at": args.generated_at,
        "expected_artifact_counts": {
            name: {"value": value, "status": ReviewState.PROVISIONAL.value}
            for name, value in counts.items()
        },
        "incidental_layout_counts": {
            "broad": sum(bool(item["broad_classification"]) for item in incidental),
            "strict": sum(bool(item["strict_classification"]) for item in incidental),
        },
        "verification_state": ReviewState.PROVISIONAL.value,
        "known_limitations": coverage["known_limitations"],
        "inventory_files": sorted(path.name for path in output.iterdir()) if output.exists() else [],
        "correction_history": [
            {
                "correction_id": "ibc2018-correction:caption-occurrence-consolidation",
                "prior_assertion": 266,
                "corrected_value": len(tables),
                "unit": "logical_formally_captioned_tables",
                "reason": "Repeated continuation captions and repeat markers are occurrences, not additional logical tables.",
                "prior_status": ReviewState.SUPERSEDED.value,
                "corrected_status": ReviewState.PROVISIONAL.value,
            },
            {
                "correction_id": "ibc2018-correction:embedded-table-labels",
                "prior_assertion": len(tables) + 4,
                "corrected_value": len(tables),
                "unit": "logical_formally_captioned_tables",
                "reason": "Four TABLE 2304.10.1 labels on PDF page 556 are embedded labels inside Figure 2308.6.7.2.",
                "prior_status": ReviewState.REJECTED.value,
                "corrected_status": ReviewState.PROVISIONAL.value,
            },
            {
                "correction_id": "ibc2018-correction:exception-block-count",
                "prior_assertion": 1294,
                "corrected_value": len(exceptions),
                "unit": "explicit_exception_marker_blocks",
                "reason": "Numbered children remain nested evidence and no longer inflate the parent exception-block count.",
                "prior_status": ReviewState.SUPERSEDED.value,
                "corrected_status": ReviewState.PROVISIONAL.value,
            },
            {
                "correction_id": "ibc2018-correction:displayed-equation-block-count",
                "prior_assertion": 762,
                "corrected_value": len(equations),
                "unit": "displayed_equation_or_formula_blocks",
                "reason": "The broad lexical scan included prose measurements, unit fragments, standards designations, variable definitions, figure labels, and continuation lines that are not independent displayed equations.",
                "prior_status": ReviewState.SUPERSEDED.value,
                "corrected_status": ReviewState.PROVISIONAL.value,
            },
        ],
        "caption_occurrence_counts": {
            "table": sum(len(item.get("anchors", ())) for item in tables),
            "figure": sum(len(item.get("anchors", ())) for item in figures),
        },
        "reference_crosscheck_file": "ibc-2018-reference-crosschecks.json",
    }

    source_register = SourceRegister(
        entries=(
            SourceRegisterEntry(
                source_id="source:icc:ibc:2018:pdf:c8f0b755",
                ast_source=AstSourceIdentity(
                    artifact_id="icc:ibc",
                    edition_id=f"2018:pdf:sha256:{SOURCE_SHA256}",
                ),
                title="2018 International Building Code",
                issuing_body="International Code Council, Inc.",
                evidence_role=EvidenceRole.NORMATIVE_TEXT,
                publication=PublicationIdentity(
                    publication_family="International Building Code",
                    edition="2018",
                    printing="First Printing, August 2017",
                    published_on="2017-08-31",
                ),
                retrieved_at=args.generated_at.replace("Z", "+00:00"),
                sha256=SOURCE_SHA256,
                media_type="application/pdf",
                access_scope=AccessScope.PRIVATE_LOCAL,
                rights_status=RightsStatus.UNCERTAIN_RESTRICTED,
                source_url=None,
                jurisdiction=None,
                rights_note=(
                    "User-supplied copyrighted ICC source. Retain exact bytes, page images, "
                    "and reconstructive extracts only in private local evidence storage."
                ),
            ),
        )
    ).to_dict()

    write_json(output / "ibc-2018-source-manifest.json", source_manifest)
    write_json(output / "ibc-2018-source-register.json", source_register)
    write_json(output / "ibc-2018-corpus-manifest.json", corpus_manifest)
    datasets = {
        "ibc-2018-table-inventory": tables,
        "ibc-2018-incidental-layout-inventory": incidental,
        "ibc-2018-figure-inventory": figures,
        "ibc-2018-diagram-inventory": diagrams,
        "ibc-2018-equation-inventory": equations,
        "ibc-2018-definition-inventory": definitions,
        "ibc-2018-exception-inventory": exceptions,
        "ibc-2018-chapter-35-inventory": chapter35,
        "ibc-2018-external-reference-inventory": external_families,
        "ibc-2018-external-citation-inventory": external_citations,
        "ibc-2018-cross-reference-inventory": cross_references,
        "ibc-2018-semantic-pilot": semantic_pilot,
        "ibc-2018-detection-inventory": detections,
        "ibc-2018-attachment-inventory": attachments,
    }
    for stem, records in datasets.items():
        write_json(output / f"{stem}.json", records)
        write_csv(output / f"{stem}.csv", records)
    write_inventory_markdown(output / "ibc-2018-table-inventory.md", "IBC 2018 Formally Captioned Tables", tables)
    write_inventory_markdown(output / "ibc-2018-figure-inventory.md", "IBC 2018 Formally Captioned Figures", figures)
    write_inventory_markdown(output / "ibc-2018-definition-inventory.md", "IBC 2018 Definitions", definitions)
    write_inventory_markdown(output / "ibc-2018-exception-inventory.md", "IBC 2018 Exceptions", exceptions)
    write_json(output / "ibc-2018-coverage-report.json", coverage)
    write_json(output / "ibc-2018-reference-crosschecks.json", reference_crosschecks)
    write_json(output / "ibc-2018-cross-reference-summary.json", cross_reference_summary)
    write_json(output / "ibc-2018-incidental-layout-broad-inventory.json", incidental)
    write_csv(output / "ibc-2018-incidental-layout-broad-inventory.csv", incidental)
    strict_incidental = [item for item in incidental if item["strict_classification"]]
    write_json(output / "ibc-2018-incidental-layout-strict-inventory.json", strict_incidental)
    write_csv(output / "ibc-2018-incidental-layout-strict-inventory.csv", strict_incidental)

    image_count_by_page = {
        int(item["pdf_page"]): len(item.get("images", ())) for item in image_regions
    }
    page_map = []
    page_evidence_index = []
    for pdf_page in range(1, 762):
        chapter, appendix = publication_context(pdf_page)
        if pdf_page <= 3:
            publication_section = "cover_and_copyright"
        elif pdf_page <= 27:
            publication_section = "front_matter"
        elif pdf_page <= 669:
            publication_section = "chapters"
        elif pdf_page <= 713:
            publication_section = "appendices"
        elif pdf_page <= 759:
            publication_section = "subject_index"
        else:
            publication_section = "trailing_blank_pages"
        page_map.append(
            {
                "pdf_page": pdf_page,
                "printed_page": printed_page(pdf_page),
                "chapter": chapter,
                "appendix": appendix,
                "publication_section": publication_section,
            }
        )
        page_evidence_index.append(
            {
                "pdf_page": pdf_page,
                "positioned_line_count": len(pages[pdf_page]),
                "image_region_count": image_count_by_page.get(pdf_page, 0),
                "raw_evidence_availability": "private_local",
                "public_projection": "anchors_hashes_and_counts_only",
            }
        )
    write_json(output / "ibc-2018-page-map.json", page_map)
    write_json(output / "ibc-2018-page-evidence-index.json", page_evidence_index)

    coverage_lines = [
        "# IBC 2018 Structural Coverage Report",
        "",
        f"Source SHA-256: `{SOURCE_SHA256}`",
        "",
        "## Counts",
        "",
    ]
    coverage_lines.extend(f"- {name}: **{value}**" for name, value in sorted(counts.items()))
    coverage_lines.extend([
        "",
        "## Incidental layouts",
        "",
        f"- Broad geometry policy: **{corpus_manifest['incidental_layout_counts']['broad']}**",
        f"- Strict row-keyed policy: **{corpus_manifest['incidental_layout_counts']['strict']}**",
        "",
        "## Internal-reference resolution",
        "",
    ])
    coverage_lines.extend(
        f"- {state}: **{count}**"
        for state, count in sorted(coverage["internal_reference_resolution"].items())
    )
    coverage_lines.extend([
        "",
        "## Chapter 35 and external references",
        "",
        f"- Chapter 35 rows: **{coverage['chapter35']['row_count']}**",
        f"- Distinct observed designations with editions: **{coverage['chapter35']['individual_designation_count']}**",
        f"- Normalized external-document families: **{coverage['chapter35']['normalized_family_count']}**",
        f"- External citation occurrences outside Chapter 35: **{coverage['external_references']['citation_occurrence_count']}**",
        f"- Unmatched external citation occurrences: **{coverage['external_references']['unmatched_occurrence_count']}**",
        "",
        "## Exception structure",
        "",
        f"- Explicit exception marker blocks: **{coverage['exception_structure']['explicit_marker_block_count']}**",
        f"- Nested numbered exception children: **{coverage['exception_structure']['nested_numbered_child_count']}**",
        "",
        "## Counts by chapter and appendix",
        "",
    ])
    for inventory_name in ("tables", "figures", "incidental_layouts", "equations", "definitions", "exceptions"):
        coverage_lines.append(f"### {inventory_name.replace('_', ' ').title()}")
        coverage_lines.append("")
        for context, count in coverage["counts_by_context"].get(inventory_name, {}).items():
            coverage_lines.append(f"- {context}: **{count}**")
        coverage_lines.append("")
    coverage_lines.extend(["## Semantic extraction pilot", ""])
    coverage_lines.append(f"- Representative source-linked records: **{len(semantic_pilot)}**")
    pilot_features = sorted(
        {
            feature
            for item in semantic_pilot
            for feature in item["structural_verification"]["features"]
        }
    )
    coverage_lines.extend(f"- Exercised feature: `{feature}`" for feature in pilot_features)
    coverage_lines.extend(["", "## Known limitations", ""])
    coverage_lines.extend(f"- {item}" for item in coverage["known_limitations"])
    (output / "ibc-2018-coverage-report.md").write_text("\n".join(coverage_lines) + "\n", encoding="utf-8")

    pilot_lines = [
        "# IBC 2018 Semantic Extraction Pilot",
        "",
        "The pilot verifies source identity, record shape, structural attachment, and serialization across representative IBC domains. It does not verify legal effect, applicability, normative status, or compliance meaning.",
        "",
        f"Representative records: **{len(semantic_pilot)}**.",
        "",
        "## Feature coverage",
        "",
    ]
    pilot_lines.extend(f"- `{feature}`" for feature in pilot_features)
    pilot_lines.extend([
        "",
        "## Records",
        "",
        "| Chapter | Source type | Source record | Exercised features | Semantic interpretation verified |",
        "|---:|---|---|---|---|",
    ])
    for item in semantic_pilot:
        verification = item["structural_verification"]
        features = ", ".join(f"`{feature}`" for feature in verification["features"]) or "none"
        pilot_lines.append(
            f"| {item.get('chapter', '')} | `{item['source_record_type']}` | `{item['source_record_id']}` | {features} | no |"
        )
    pilot_lines.extend([
        "",
        "All semantic classifications remain provisional. A record may demonstrate a structural feature while its engineering or legal interpretation remains unknown or disputed.",
    ])
    (output / "ibc-2018-semantic-pilot-report.md").write_text(
        "\n".join(pilot_lines) + "\n", encoding="utf-8"
    )

    discrepancy_lines = ["# IBC 2018 Discrepancies", ""]
    if discrepancies:
        discrepancy_lines.extend(
            f"- `{item['code']}`: `{item.get('record_id', '')}` ({item['severity']})"
            for item in discrepancies
        )
    else:
        discrepancy_lines.append("No deterministic contract discrepancies were detected.")
    (output / "ibc-2018-discrepancies.md").write_text("\n".join(discrepancy_lines) + "\n", encoding="utf-8")
    write_csv(output / "ibc-2018-review-queue.csv", review_queue)

    reference_map = [
        "# IBC 2018 External Reference Map",
        "",
        f"Chapter 35 rows: **{len(chapter35)}**.",
        f"Distinct observed designations with editions: **{coverage['chapter35']['individual_designation_count']}**.",
        f"Normalized document families: **{len(external_families)}**.",
        f"Lexically detected citation occurrences outside Chapter 35: **{len(external_citations)}**.",
        f"Unmatched citation occurrences: **{len(unmatched_citations)}**.",
        f"Chapter 35 families not lexically detected elsewhere: **{len(reference_crosschecks['chapter35_families_not_detected_elsewhere'])}**.",
        f"Alias or duplicate family candidates: **{len(reference_crosschecks['duplicate_or_alias_families'])}**.",
        "",
        "Chapter 35 rows, individual designations, normalized families, and citation occurrences are separate records.",
    ]
    (output / "ibc-2018-reference-map.md").write_text("\n".join(reference_map) + "\n", encoding="utf-8")

    # Rewrite manifest after all inventory files exist.
    corpus_manifest["inventory_files"] = sorted(path.name for path in output.iterdir())
    write_json(output / "ibc-2018-corpus-manifest.json", corpus_manifest)
    print(json.dumps({"counts": counts, "incidental": corpus_manifest["incidental_layout_counts"], "discrepancies": len(discrepancies)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
