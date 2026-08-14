from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

try:
    import fitz
except ImportError:  # optional PDF enrichment dependency
    fitz = None

from building_code_ast.pdf_enrichment import (
    DescriptiveMetadataOperation,
    EvidenceOrigin,
    OutlineEntry,
    OutlineOperation,
    PageLabelRange,
    PageLabelsOperation,
    PdfEnrichmentPlan,
    PdfSourceIdentity,
    SearchableTextEntry,
    SearchableTextOperation,
    TextOrigin,
    enrich_pdf,
    plan_from_dict,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_source(path: Path, *, existing_outline: bool = False, metadata_title: str = "") -> None:
    doc = fitz.open()
    page1 = doc.new_page(width=612, height=792)
    page1.insert_text((72, 96), "Native synthetic text page one", fontsize=12)

    page2 = doc.new_page(width=612, height=792)
    page2.draw_rect(fitz.Rect(72, 72, 540, 720), color=(0, 0, 0), width=1)

    page3 = doc.new_page(width=612, height=792)
    page3.insert_text((72, 96), "Native synthetic text page three", fontsize=12)

    page4 = doc.new_page(width=612, height=792)
    page4.insert_text((72, 96), "Native synthetic text page four", fontsize=12)

    if metadata_title:
        metadata = doc.metadata
        metadata["title"] = metadata_title
        doc.set_metadata(metadata)
    if existing_outline:
        doc.set_toc([[1, "Existing chapter", 1]])

    catalog = doc.pdf_catalog()
    struct_xref = doc.get_new_xref()
    doc.update_object(struct_xref, "<< /Type /StructTreeRoot /K [] >>")
    doc.xref_set_key(catalog, "StructTreeRoot", f"{struct_xref} 0 R")

    doc.save(path)
    doc.close()


def source_identity(path: Path) -> PdfSourceIdentity:
    with fitz.open(path) as doc:
        return PdfSourceIdentity(
            source_id="source:synthetic:pdf-enrichment",
            sha256=sha256(path),
            size=path.stat().st_size,
            media_type="application/pdf",
            page_count=doc.page_count,
        )


def enrichment_plan(path: Path) -> PdfEnrichmentPlan:
    return PdfEnrichmentPlan(
        source=source_identity(path),
        operations=(
            SearchableTextOperation(
                evidence_origin=EvidenceOrigin.REVIEWED_SOURCE_OBSERVATION,
                entries=(
                    SearchableTextEntry(
                        page_number=2,
                        text="Recovered synthetic raster text",
                        bbox=(72.0, 72.0, 540.0, 720.0),
                        text_origin=TextOrigin.RASTER_RECOVERY,
                    ),
                ),
            ),
            OutlineOperation(
                evidence_origin=EvidenceOrigin.DOCUMENT_AST,
                entries=(
                    OutlineEntry(level=1, title="Synthetic Chapter", page_number=1),
                    OutlineEntry(level=2, title="Synthetic Section", page_number=3),
                ),
            ),
            PageLabelsOperation(
                evidence_origin=EvidenceOrigin.REVIEWED_SOURCE_OBSERVATION,
                ranges=(
                    PageLabelRange(start_page_number=1, style="roman_lower", first_page_number=1),
                    PageLabelRange(start_page_number=3, style="decimal", first_page_number=1),
                ),
            ),
            DescriptiveMetadataOperation(
                evidence_origin=EvidenceOrigin.SOURCE_REGISTER,
                values=(
                    ("title", "Synthetic Enriched Publication"),
                    ("author", "Synthetic Standards Body"),
                ),
            ),
        ),
    )


def contract_plan() -> PdfEnrichmentPlan:
    return PdfEnrichmentPlan(
        source=PdfSourceIdentity(
            source_id="source:synthetic:pdf-enrichment-contract",
            sha256="a" * 64,
            size=100,
            media_type="application/pdf",
            page_count=4,
        ),
        operations=(
            SearchableTextOperation(
                evidence_origin=EvidenceOrigin.REVIEWED_SOURCE_OBSERVATION,
                entries=(
                    SearchableTextEntry(
                        2,
                        "Synthetic recovered text",
                        (72.0, 72.0, 540.0, 720.0),
                        TextOrigin.RASTER_RECOVERY,
                    ),
                ),
            ),
            OutlineOperation(
                evidence_origin=EvidenceOrigin.DOCUMENT_AST,
                entries=(OutlineEntry(1, "Synthetic Chapter", 1),),
            ),
            PageLabelsOperation(
                evidence_origin=EvidenceOrigin.REVIEWED_SOURCE_OBSERVATION,
                ranges=(PageLabelRange(1, "roman_lower"), PageLabelRange(3, "decimal")),
            ),
            DescriptiveMetadataOperation(
                evidence_origin=EvidenceOrigin.SOURCE_REGISTER,
                values=(("title", "Synthetic Publication"),),
            ),
        ),
    )


class PdfEnrichmentContractTests(unittest.TestCase):
    def test_plan_round_trip_is_closed_and_digest_is_deterministic(self) -> None:
        plan = contract_plan()
        encoded = plan.to_dict()
        round_trip = plan_from_dict(encoded)

        self.assertEqual(round_trip, plan)
        self.assertEqual(round_trip.digest(), plan.digest())
        with self.assertRaisesRegex(ValueError, "unsupported fields"):
            plan_from_dict({**encoded, "surprise": True})

    def test_versioned_schemas_are_closed_and_receipt_is_source_safe(self) -> None:
        root = Path(__file__).resolve().parents[1]
        plan_schema = json.loads((root / "schemas" / "pdf-enrichment-plan.schema.json").read_text())
        receipt_schema = json.loads((root / "schemas" / "pdf-enrichment-receipt.schema.json").read_text())

        self.assertFalse(plan_schema["additionalProperties"])
        self.assertFalse(receipt_schema["additionalProperties"])
        searchable = receipt_schema["$defs"]["searchable_text_summary"]["properties"]["entries"]["items"]["properties"]
        outline = receipt_schema["$defs"]["outline_summary"]["properties"]["entries"]["items"]["properties"]
        self.assertEqual(set(searchable), {"page_number", "text_sha256", "text_origin"})
        self.assertEqual(set(outline), {"level", "page_number", "title_sha256"})
        rendered_receipt_schema = json.dumps(receipt_schema, sort_keys=True)
        self.assertNotIn('"provider"', rendered_receipt_schema)
        self.assertNotIn('"object_id"', rendered_receipt_schema)


@unittest.skipUnless(
    fitz is not None and importlib.util.find_spec("pypdf") is not None,
    "PDF enrichment runtime dependencies are not installed",
)
class PdfEnrichmentRuntimeTests(unittest.TestCase):
    def test_enrichment_is_additive_visually_identical_and_source_safe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.pdf"
            output = Path(directory) / "enriched.pdf"
            make_source(source)
            original_bytes = source.read_bytes()
            plan = enrichment_plan(source)

            receipt = enrich_pdf(source, output, plan)

            self.assertEqual(source.read_bytes(), original_bytes)
            self.assertEqual(receipt.source.sha256, sha256(source))
            self.assertEqual(receipt.derivative_sha256, sha256(output))
            self.assertNotEqual(receipt.source.sha256, receipt.derivative_sha256)
            self.assertEqual(receipt.plan_sha256, plan.digest())
            self.assertTrue(receipt.verification.structural_valid)
            self.assertTrue(receipt.verification.visual_pages_identical)
            self.assertTrue(receipt.verification.tagged_structure_preserved)
            self.assertEqual(receipt.verification.independent_backend, "pypdf")
            self.assertEqual(receipt.verification.searchable_text_target_pages, (2,))
            self.assertEqual(receipt.verification.unchanged_native_text_pages, (1, 3, 4))

            with fitz.open(output) as doc:
                self.assertIn("Recovered synthetic raster text", doc[1].get_text())
                self.assertEqual(
                    [(item[0], item[1], item[2]) for item in doc.get_toc()],
                    [(1, "Synthetic Chapter", 1), (2, "Synthetic Section", 3)],
                )
                self.assertEqual(
                    doc.get_page_labels(),
                    [
                        {"startpage": 0, "prefix": "", "firstpagenum": 1, "style": "r"},
                        {"startpage": 2, "prefix": "", "firstpagenum": 1, "style": "D"},
                    ],
                )
                self.assertEqual(doc.metadata["title"], "Synthetic Enriched Publication")
                self.assertEqual(doc.metadata["author"], "Synthetic Standards Body")

            rendered_receipt = json.dumps(receipt.to_dict(), sort_keys=True)
            self.assertNotIn("Recovered synthetic raster text", rendered_receipt)
            self.assertNotIn("Synthetic Chapter", rendered_receipt)
            self.assertIn(hashlib.sha256(b"Recovered synthetic raster text").hexdigest(), rendered_receipt)
            self.assertIn(hashlib.sha256(b"Synthetic Chapter").hexdigest(), rendered_receipt)

    def test_text_enrichment_rejects_page_with_native_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.pdf"
            output = Path(directory) / "enriched.pdf"
            make_source(source)
            plan = PdfEnrichmentPlan(
                source=source_identity(source),
                operations=(
                    SearchableTextOperation(
                        evidence_origin=EvidenceOrigin.REVIEWED_SOURCE_OBSERVATION,
                        entries=(
                            SearchableTextEntry(
                                1,
                                "replacement",
                                (72, 72, 540, 720),
                                TextOrigin.DERIVED_TEXT,
                            ),
                        ),
                    ),
                ),
            )
            with self.assertRaisesRegex(ValueError, "already contains usable text"):
                enrich_pdf(source, output, plan)
            self.assertFalse(output.exists())

    def test_existing_outline_and_metadata_conflicts_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            outlined = Path(directory) / "outlined.pdf"
            make_source(outlined, existing_outline=True)
            plan = PdfEnrichmentPlan(
                source=source_identity(outlined),
                operations=(
                    OutlineOperation(
                        evidence_origin=EvidenceOrigin.DOCUMENT_AST,
                        entries=(OutlineEntry(1, "New chapter", 1),),
                    ),
                ),
            )
            with self.assertRaisesRegex(ValueError, "outline"):
                enrich_pdf(outlined, Path(directory) / "x.pdf", plan)

            metadata = Path(directory) / "metadata.pdf"
            make_source(metadata, metadata_title="Existing Title")
            plan = PdfEnrichmentPlan(
                source=source_identity(metadata),
                operations=(
                    DescriptiveMetadataOperation(
                        evidence_origin=EvidenceOrigin.SOURCE_REGISTER,
                        values=(("title", "Different Title"),),
                    ),
                ),
            )
            with self.assertRaisesRegex(ValueError, "metadata"):
                enrich_pdf(metadata, Path(directory) / "y.pdf", plan)

    def test_source_identity_mismatch_fails_before_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.pdf"
            output = Path(directory) / "enriched.pdf"
            make_source(source)
            identity = source_identity(source)
            plan = PdfEnrichmentPlan(
                source=PdfSourceIdentity(
                    source_id=identity.source_id,
                    sha256="0" * 64,
                    size=identity.size,
                    media_type=identity.media_type,
                    page_count=identity.page_count,
                ),
                operations=(
                    DescriptiveMetadataOperation(
                        evidence_origin=EvidenceOrigin.SOURCE_REGISTER,
                        values=(("title", "Synthetic"),),
                    ),
                ),
            )
            with self.assertRaisesRegex(ValueError, "sha256"):
                enrich_pdf(source, output, plan)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
