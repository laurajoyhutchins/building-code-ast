import unittest

from building_code_ast.section_index import build_section_index, code_address_for_record


class SectionIndexTests(unittest.TestCase):
    def test_code_address_prefers_section_identity_over_page_anchors(self) -> None:
        record = {
            "record_type": "table",
            "id": "table-1604-5",
            "published_identifier": "1604.5",
            "section_context": "1604.5",
            "anchors": {"printed_page": "3-12", "pdf_page": 328},
        }

        self.assertEqual(
            code_address_for_record(record),
            {
                "publication": "IBC",
                "edition": "2018",
                "kind": "table",
                "locator": "1604.5",
                "context_locator": "1604.5",
                "canonical": "IBC-2018 Table 1604.5",
            },
        )

    def test_section_index_groups_without_copying_page_coordinates(self) -> None:
        records = [
            {
                "record_type": "internal_cross_reference",
                "id": "ref-a",
                "source_locator": "1604.5",
                "anchors": {"printed_page": "3-12", "pdf_page": 328},
            },
            {
                "record_type": "internal_cross_reference",
                "id": "ref-b",
                "source_locator": "1604.5",
                "anchors": {"printed_page": "3-13", "pdf_page": 329},
            },
        ]

        index = build_section_index(records)

        self.assertEqual(index["addressing_policy"], "section_first")
        self.assertEqual(
            index["provenance_policy"],
            "page_anchors_remain_on_source_records",
        )
        self.assertEqual(
            index["entries"],
            [
                {
                    "address": {
                        "publication": "IBC",
                        "edition": "2018",
                        "kind": "section",
                        "locator": "1604.5",
                        "canonical": "IBC-2018 §1604.5",
                    },
                    "record_refs": [
                        {"record_type": "internal_cross_reference", "id": "ref-a"},
                        {"record_type": "internal_cross_reference", "id": "ref-b"},
                    ],
                }
            ],
        )
        self.assertNotIn("anchors", index["entries"][0])
        self.assertNotIn("printed_page", repr(index["entries"]))
        self.assertNotIn("pdf_page", repr(index["entries"]))

    def test_section_index_never_uses_page_as_a_fallback_address(self) -> None:
        record = {
            "record_type": "unknown_observation",
            "id": "page-only",
            "anchors": {"printed_page": "3-12", "pdf_page": 328},
        }

        index = build_section_index([record])

        self.assertEqual(index["entries"], [])
        self.assertEqual(
            index["unresolved_record_refs"],
            [{"record_type": "unknown_observation", "id": "page-only"}],
        )

    def test_section_index_uses_code_order_not_lexical_order(self) -> None:
        records = [
            {
                "record_type": "internal_cross_reference",
                "id": "ten",
                "source_locator": "10.1",
            },
            {
                "record_type": "internal_cross_reference",
                "id": "two",
                "source_locator": "2.1",
            },
        ]

        index = build_section_index(records)

        self.assertEqual(
            [entry["address"]["locator"] for entry in index["entries"]],
            ["2.1", "10.1"],
        )

    def test_exception_address_uses_parent_provision(self) -> None:
        record = {
            "record_type": "exception",
            "id": "exception-1",
            "section_context": "16",
            "parent_locator": "1604.5",
            "exception_number": "1",
        }

        address = code_address_for_record(record)

        self.assertIsNotNone(address)
        assert address is not None
        self.assertEqual(address["locator"], "1604.5")
        self.assertEqual(
            address["canonical"],
            "IBC-2018 §1604.5 Exception 1",
        )


if __name__ == "__main__":
    unittest.main()
