import unittest

from building_code_ast.document_model import DocumentNodeType, DocumentSourceArtifact
from building_code_ast.ingest.asce7_22 import Asce7Observation, parse_asce7_22_observations
from building_code_ast.ingest.asce7_22_source_roles import (
    Asce7SourceRole,
    RoleQualifiedAsce7Observation,
    normative_structural_observations,
    observations_by_role,
)
from building_code_ast.ingest.pdf_layout import PdfBlock, PdfLine, PdfSpan


ARTIFACT = DocumentSourceArtifact(
    artifact_id="sha256:522d341d8ab21eb254c8af2d853910633233285eb3704933729e0aeefdc88eb0",
    edition_id="asce-7-22",
)


def _observation(
    text: str,
    page: int,
    *,
    font: str | None = None,
    size: float = 9.5,
    block_number: int = 0,
    x0: float = 72.0,
) -> Asce7Observation:
    lines = ()
    if font is not None:
        span = PdfSpan(
            bbox=(x0, 100.0, 300.0, 120.0),
            text=text,
            font=font,
            size=size,
            flags=4,
        )
        lines = (
            PdfLine(
                bbox=(x0, 100.0, 300.0, 120.0),
                spans=(span,),
            ),
        )
    return Asce7Observation(
        block=PdfBlock(
            page_number=page,
            block_number=block_number,
            bbox=(x0, 100.0, 300.0, 120.0),
            text=text,
            lines=lines,
        )
    )


def _qualified(
    observation: Asce7Observation,
    role: Asce7SourceRole = Asce7SourceRole.NORMATIVE,
) -> RoleQualifiedAsce7Observation:
    return RoleQualifiedAsce7Observation(
        observation,
        role,
        "synthetic role evidence",
    )


class Asce722SourceRoleTests(unittest.TestCase):
    def test_only_explicit_normative_observations_feed_structural_promotion(self) -> None:
        normative = _qualified(_observation("Synthetic prose", 30))
        commentary = _qualified(
            _observation("C1.1 SYNTHETIC", 500),
            Asce7SourceRole.COMMENTARY,
        )
        reference = _qualified(
            _observation("1.1 SYNTHETIC ........ 30", 8),
            Asce7SourceRole.REFERENCE,
        )

        selected = normative_structural_observations((reference, commentary, normative))

        self.assertEqual(selected, (normative.observation,))

    def test_bold_9_5_normative_candidate_is_explicit_declaration_context(self) -> None:
        # Exact-source collision family 7.1.2: normative page 117 uses bold 9.5 pt.
        declaration = _qualified(
            _observation("7.1.2 SYNTHETIC HEADING", 117, font="Synthetic.B", size=9.5)
        )

        selected = normative_structural_observations((declaration,))

        self.assertIs(selected[0].section_declaration, True)

    def test_regular_numeric_leading_candidate_fails_closed_as_non_declaration(self) -> None:
        # Exact-source collision family 1.1: page 178 is regular 9.5 pt, not a declaration.
        lookalike = _qualified(
            _observation("1.1 SYNTHETIC NUMERIC PROSE", 178, font="Synthetic", size=9.5)
        )

        selected = normative_structural_observations((lookalike,))

        self.assertIs(selected[0].section_declaration, False)

    def test_bold_italic_candidate_fails_closed_as_non_declaration(self) -> None:
        # Exact-source collision family 7.1.2: page 235 is bold-italic 9.5 pt.
        lookalike = _qualified(
            _observation(
                "7.1.2 SYNTHETIC ROLE-DISTINCT HEADING",
                235,
                font="Synthetic.BI",
                size=9.5,
            )
        )

        selected = normative_structural_observations((lookalike,))

        self.assertIs(selected[0].section_declaration, False)

    def test_numeric_candidate_without_span_evidence_fails_closed(self) -> None:
        candidate = _qualified(_observation("4.10 SYNTHETIC", 81))

        selected = normative_structural_observations((candidate,))

        self.assertIs(selected[0].section_declaration, False)

    def test_declaration_context_suppresses_numeric_lookalike_section_promotion(self) -> None:
        chapter = _qualified(
            _observation(
                "CHAPTER 7 SYNTHETIC",
                177,
                font="Synthetic.B",
                block_number=1,
                x0=274.0,
            )
        )
        lookalike = _qualified(
            _observation(
                "1.1 SYNTHETIC NUMERIC PROSE",
                178,
                font="Synthetic",
                size=9.5,
                block_number=2,
            )
        )

        selected = normative_structural_observations((chapter, lookalike))
        ast = parse_asce7_22_observations(selected, source_artifact=ARTIFACT)

        self.assertIs(ast.root.children[0].node_type, DocumentNodeType.CHAPTER)
        self.assertIs(ast.root.children[0].children[0].node_type, DocumentNodeType.PARAGRAPH)

    def test_non_normative_evidence_is_preserved_by_role(self) -> None:
        commentary = _qualified(
            _observation("C1.3 SYNTHETIC", 500),
            Asce7SourceRole.COMMENTARY,
        )
        ambiguous = _qualified(
            _observation("1.3 SYNTHETIC", 12),
            Asce7SourceRole.AMBIGUOUS,
        )

        partitioned = observations_by_role((commentary, ambiguous))

        self.assertEqual(partitioned[Asce7SourceRole.COMMENTARY], (commentary,))
        self.assertEqual(partitioned[Asce7SourceRole.AMBIGUOUS], (ambiguous,))
        self.assertEqual(partitioned[Asce7SourceRole.NORMATIVE], ())

    def test_role_evidence_cannot_be_implicit(self) -> None:
        with self.assertRaisesRegex(ValueError, "evidence"):
            RoleQualifiedAsce7Observation(
                _observation("1.1 SYNTHETIC", 30),
                Asce7SourceRole.NORMATIVE,
                "   ",
            )


if __name__ == "__main__":
    unittest.main()
