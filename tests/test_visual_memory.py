import json
import tempfile
import unittest
from pathlib import Path

from tools.visual_memory.core import (
    VisualObject,
    bm25_scores,
    context_text,
    multiscale_view_boxes,
    verify_private_package,
    visual_cache_key,
)


class VisualMemoryContractTests(unittest.TestCase):
    def test_visual_object_defaults_logical_identity_to_occurrence(self):
        obj = VisualObject(
            corpus_id="demo",
            kind="figure",
            occurrence_id="demo:figure:1@p2",
            label="1",
            page=2,
            source_sha256="a" * 64,
        )
        self.assertEqual(obj.logical_visual_id, "demo:figure:1@p2")

    def test_context_text_prioritizes_structural_evidence_and_omits_degraded_caption(self):
        obj = VisualObject(
            corpus_id="aci-318-2019",
            kind="figure",
            occurrence_id="aci:fig:r10.3.3",
            logical_visual_id="aci:fig:r10.3.3",
            label="R10.3.3",
            title="g@rbled capti0n bytes",
            structural_context="Chapter 10 Synthetic Concrete | Commentary R10.3",
            page=100,
            source_sha256="b" * 64,
            caption_text_quality="degraded",
        )
        packed = context_text(obj, max_words=10)
        self.assertTrue(packed.startswith("R10.3.3"))
        self.assertIn("Chapter", packed)
        self.assertNotIn("g@rbled", packed)
        self.assertLessEqual(len(packed.split()), 10)

    def test_multiscale_views_are_deterministic_and_bounded(self):
        boxes = multiscale_view_boxes(1000, 800, include_fine=True)
        names = [b.name for b in boxes]
        self.assertEqual(names, [
            "global", "medium_ul", "medium_ur", "medium_ll", "medium_lr", "medium_center",
            "fine_ul", "fine_ur", "fine_ll", "fine_lr", "fine_center",
        ])
        for box in boxes:
            self.assertGreaterEqual(box.x0, 0)
            self.assertGreaterEqual(box.y0, 0)
            self.assertLessEqual(box.x1, 1000)
            self.assertLessEqual(box.y1, 800)
            self.assertGreater(box.x1, box.x0)
            self.assertGreater(box.y1, box.y0)

    def test_bm25_prefers_exact_technical_phrase(self):
        docs = [
            "wood fastener connection detail",
            "electrical single line diagram elevator power",
            "sprinkler obstruction clearance diagram",
        ]
        scores = bm25_scores(docs, "electrical single line diagram")
        self.assertEqual(max(range(len(scores)), key=scores.__getitem__), 1)


    def test_visual_cache_key_changes_with_view_policy_and_context(self):
        base = visual_cache_key(
            render_sha256="e" * 64,
            model_sha256="f" * 64,
            include_fine=False,
            context="synthetic figure context",
        )
        same = visual_cache_key(
            render_sha256="e" * 64,
            model_sha256="f" * 64,
            include_fine=False,
            context="synthetic figure context",
        )
        fine = visual_cache_key(
            render_sha256="e" * 64,
            model_sha256="f" * 64,
            include_fine=True,
            context="synthetic figure context",
        )
        changed_context = visual_cache_key(
            render_sha256="e" * 64,
            model_sha256="f" * 64,
            include_fine=False,
            context="different synthetic context",
        )
        self.assertEqual(base, same)
        self.assertNotEqual(base, fine)
        self.assertNotEqual(base, changed_context)

    def test_package_verifier_rejects_source_media(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "manifest.json").write_text(json.dumps({
                "schema": "engineering-visual-memory-package/0.4.0",
                "clip_model_sha256": "c" * 64,
                "source_pdfs_included": False,
                "source_images_included": False,
            }))
            (root / "private-source.pdf").write_bytes(b"%PDF")
            report = verify_private_package(root)
            self.assertFalse(report.ok)
            self.assertIn("private-source.pdf", report.forbidden_files)

    def test_package_verifier_accepts_source_safe_payload(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "manifest.json").write_text(json.dumps({
                "schema": "engineering-visual-memory-package/0.4.0",
                "clip_model_sha256": "d" * 64,
                "source_pdfs_included": False,
                "source_images_included": False,
            }))
            (root / "objects.jsonl").write_text("{}\n")
            report = verify_private_package(root)
            self.assertTrue(report.ok)
            self.assertEqual(report.forbidden_files, [])


if __name__ == "__main__":
    unittest.main()
