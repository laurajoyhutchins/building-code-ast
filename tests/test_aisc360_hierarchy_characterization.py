import unittest

from building_code_ast.aisc360_hierarchy_characterization import (
    HierarchyPageObservation,
    characterize_hierarchy,
)


class TestAisc360HierarchyCharacterization(unittest.TestCase):
    def test_characterization_records_text_anchors_without_source_prose(self) -> None:
        result = characterize_hierarchy(
            [
                HierarchyPageObservation(1, "CHAPTER A\nbody"),
                HierarchyPageObservation(2, None),
                HierarchyPageObservation(3, "APPENDIX 1\nbody"),
            ],
            raster_hierarchy_pages=[2],
        )

        self.assertEqual(result["chapter_anchors"], [{"page": 1, "identifier": "A"}])
        self.assertEqual(result["appendix_anchors"], [{"page": 3, "identifier": 1}])
        self.assertEqual(result["raster_hierarchy_pages"], [2])
        self.assertIs(result["embedded_text_only_hierarchy_complete"], False)
        self.assertEqual(
            result["next_parser_boundary"],
            "raster_text_recovery_before_hierarchy_parse",
        )
        self.assertNotIn("body", repr(result))

    def test_characterization_rejects_raster_evidence_on_text_page(self) -> None:
        with self.assertRaisesRegex(ValueError, "image-only"):
            characterize_hierarchy(
                [HierarchyPageObservation(1, "CHAPTER A")],
                raster_hierarchy_pages=[1],
            )


if __name__ == "__main__":
    unittest.main()
