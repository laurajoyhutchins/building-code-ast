from building_code_ast.ingest.aci318 import parse_aci318_page


def test_aci318_page_parser_exists():
    assert callable(parse_aci318_page)
