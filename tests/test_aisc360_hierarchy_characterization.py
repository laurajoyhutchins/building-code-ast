from building_code_ast.aisc360_hierarchy_characterization import (
    HierarchyPageObservation,
    characterize_hierarchy,
)


def test_characterization_records_text_anchors_without_source_prose() -> None:
    result = characterize_hierarchy(
        [
            HierarchyPageObservation(1, "CHAPTER A\nbody"),
            HierarchyPageObservation(2, None),
            HierarchyPageObservation(3, "APPENDIX 1\nbody"),
        ],
        raster_hierarchy_pages=[2],
    )

    assert result["chapter_anchors"] == [{"page": 1, "identifier": "A"}]
    assert result["appendix_anchors"] == [{"page": 3, "identifier": 1}]
    assert result["raster_hierarchy_pages"] == [2]
    assert result["embedded_text_only_hierarchy_complete"] is False
    assert result["next_parser_boundary"] == "raster_text_recovery_before_hierarchy_parse"
    assert "body" not in repr(result)


def test_characterization_rejects_raster_evidence_on_text_page() -> None:
    try:
        characterize_hierarchy(
            [HierarchyPageObservation(1, "CHAPTER A")],
            raster_hierarchy_pages=[1],
        )
    except ValueError as exc:
        assert "image-only" in str(exc)
    else:
        raise AssertionError("expected ValueError")
