from building_code_ast.section_index import build_section_index, code_address_for_record


def test_code_address_prefers_section_identity_over_page_anchors() -> None:
    record = {
        "record_type": "table",
        "id": "table-1604-5",
        "published_identifier": "1604.5",
        "section_context": "1604.5",
        "anchors": {"printed_page": "3-12", "pdf_page": 328},
    }

    assert code_address_for_record(record) == {
        "publication": "IBC",
        "edition": "2018",
        "kind": "table",
        "locator": "1604.5",
        "context_locator": "1604.5",
        "canonical": "IBC-2018 Table 1604.5",
    }


def test_section_index_groups_by_code_address_without_copying_page_coordinates() -> None:
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

    assert index["addressing_policy"] == "section_first"
    assert index["provenance_policy"] == "page_anchors_remain_on_source_records"
    assert index["entries"] == [
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
    ]
    assert "anchors" not in index["entries"][0]
    assert "printed_page" not in repr(index["entries"])
    assert "pdf_page" not in repr(index["entries"])


def test_section_index_never_uses_page_as_a_fallback_address() -> None:
    record = {
        "record_type": "unknown_observation",
        "id": "page-only",
        "anchors": {"printed_page": "3-12", "pdf_page": 328},
    }

    index = build_section_index([record])

    assert index["entries"] == []
    assert index["unresolved_record_refs"] == [
        {"record_type": "unknown_observation", "id": "page-only"}
    ]


def test_section_index_uses_code_order_instead_of_lexical_page_like_order() -> None:
    records = [
        {"record_type": "internal_cross_reference", "id": "ten", "source_locator": "10.1"},
        {"record_type": "internal_cross_reference", "id": "two", "source_locator": "2.1"},
    ]

    index = build_section_index(records)

    assert [entry["address"]["locator"] for entry in index["entries"]] == ["2.1", "10.1"]


def test_exception_address_uses_parent_provision_not_broader_context() -> None:
    record = {
        "record_type": "exception",
        "id": "exception-1",
        "section_context": "16",
        "parent_locator": "1604.5",
        "exception_number": "1",
    }

    address = code_address_for_record(record)

    assert address is not None
    assert address["locator"] == "1604.5"
    assert address["canonical"] == "IBC-2018 §1604.5 Exception 1"
