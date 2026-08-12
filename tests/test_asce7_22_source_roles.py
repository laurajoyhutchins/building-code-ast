from building_code_ast.ingest.asce7_22 import Asce7Observation
from building_code_ast.ingest.asce7_22_source_roles import (
    Asce7SourceRole,
    RoleQualifiedAsce7Observation,
    normative_structural_observations,
    observations_by_role,
)
from building_code_ast.ingest.pdf_layout import PdfBlock


def _observation(text: str, page: int) -> Asce7Observation:
    return Asce7Observation(
        block=PdfBlock(
            page_number=page,
            block_number=0,
            bbox=(72.0, 100.0, 300.0, 120.0),
            text=text,
        )
    )


def test_only_explicit_normative_observations_feed_structural_promotion() -> None:
    normative = RoleQualifiedAsce7Observation(
        _observation("1.1 Scope", 30),
        Asce7SourceRole.NORMATIVE,
        "body declaration region",
    )
    commentary = RoleQualifiedAsce7Observation(
        _observation("C1.1 Scope", 500),
        Asce7SourceRole.COMMENTARY,
        "commentary publication region",
    )
    reference = RoleQualifiedAsce7Observation(
        _observation("1.1 Scope ........ 30", 8),
        Asce7SourceRole.REFERENCE,
        "contents/reference region",
    )

    selected = normative_structural_observations((reference, commentary, normative))

    assert selected == (normative.observation,)


def test_non_normative_evidence_is_preserved_by_role() -> None:
    commentary = RoleQualifiedAsce7Observation(
        _observation("C1.3 Basic Requirements", 500),
        Asce7SourceRole.COMMENTARY,
        "commentary publication region",
    )
    ambiguous = RoleQualifiedAsce7Observation(
        _observation("1.3 Basic Requirements", 12),
        Asce7SourceRole.AMBIGUOUS,
        "locator-shaped text without declaration evidence",
    )

    partitioned = observations_by_role((commentary, ambiguous))

    assert partitioned[Asce7SourceRole.COMMENTARY] == (commentary,)
    assert partitioned[Asce7SourceRole.AMBIGUOUS] == (ambiguous,)
    assert partitioned[Asce7SourceRole.NORMATIVE] == ()


def test_role_evidence_cannot_be_implicit() -> None:
    try:
        RoleQualifiedAsce7Observation(
            _observation("1.1 Scope", 30),
            Asce7SourceRole.NORMATIVE,
            "   ",
        )
    except ValueError as exc:
        assert "evidence" in str(exc)
    else:
        raise AssertionError("missing role evidence must fail closed")
