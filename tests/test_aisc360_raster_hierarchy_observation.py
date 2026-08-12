from building_code_ast.aisc360_raster_hierarchy_observation import (
    AISC360_DERIVATIVE_SHA256,
    RasterHierarchyPageObservation,
    summarize_raster_hierarchy_observations,
)


def _observation(*, page: int, text: str, source_sha256: str = AISC360_DERIVATIVE_SHA256):
    return RasterHierarchyPageObservation(
        page_number=page,
        source_derivative_sha256=source_sha256,
        render_sha256="a" * 64,
        render_dpi=600,
        recovery_backend="source-safe-test",
        recovered_text=text,
    )


def test_raster_observation_emits_source_safe_locator_evidence() -> None:
    result = summarize_raster_hierarchy_observations(
        [_observation(page=243, text="1.3. SYNTHETIC HEADING\nsynthetic body")]
    )

    assert result == {
        "schema": "aisc360-raster-hierarchy-observation-v1",
        "source_derivative_sha256": AISC360_DERIVATIVE_SHA256,
        "observations": [
            {
                "page": 243,
                "source_kind": "raster_recovery",
                "render_sha256": "a" * 64,
                "render_dpi": 600,
                "recovery_backend": "source-safe-test",
                "recovered_text_sha256": "3d727c41e458c3a07cad471106bf66e37916644d9ac5a72ceab65f9fc3628e24",
                "dotted_hierarchy_locators": ["1.3"],
            }
        ],
        "parser_promotion_performed": False,
    }
    assert "SYNTHETIC HEADING" not in repr(result)
    assert "synthetic body" not in repr(result)


def test_raster_observation_rejects_wrong_source_identity() -> None:
    try:
        summarize_raster_hierarchy_observations(
            [_observation(page=243, text="1.3. SYNTHETIC", source_sha256="b" * 64)]
        )
    except ValueError as exc:
        assert "source derivative" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_raster_observation_does_not_infer_single_level_numbering() -> None:
    result = summarize_raster_hierarchy_observations(
        [_observation(page=285, text="3. SYNTHETIC CHILD\n4.2. SYNTHETIC SECTION")]
    )

    assert result["observations"][0]["dotted_hierarchy_locators"] == ["4.2"]


def test_raster_observation_requires_recovery_provenance() -> None:
    try:
        RasterHierarchyPageObservation(
            page_number=243,
            source_derivative_sha256=AISC360_DERIVATIVE_SHA256,
            render_sha256="a" * 64,
            render_dpi=0,
            recovery_backend="",
            recovered_text="1.3. SYNTHETIC",
        )
    except ValueError as exc:
        assert "render_dpi" in str(exc) or "recovery_backend" in str(exc)
    else:
        raise AssertionError("expected ValueError")
