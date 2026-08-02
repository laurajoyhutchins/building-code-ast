from __future__ import annotations

from html.parser import HTMLParser
from urllib.request import Request, urlopen

from building_code_ast.evidence.amendments import (
    _group_clause_texts,
    _parse_official_blocks,
    _wac_sections,
)


URL = "https://app.leg.wa.gov/WAC/default.aspx?cite=51-50-0403"
TARGETS = ("403.4.8.3", "403.5.4", "51-50-0403")


class LayoutParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, str | None]] = []
        self.paths: dict[str, list[str]] = {target: [] for target in TARGETS}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        self.stack.append((tag, values.get("class")))

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        for target in TARGETS:
            if target not in data:
                continue
            path = "/".join(
                f"{tag}.{class_name}" if class_name else tag
                for tag, class_name in self.stack[-8:]
            )
            if path not in self.paths[target]:
                self.paths[target].append(path)


def main() -> None:
    with urlopen(Request(URL, headers={"User-Agent": "building-code-ast-validation/1.0"}), timeout=60) as response:
        content = response.read()
    parser = LayoutParser()
    parser.feed(content.decode("utf-8", errors="replace"))
    blocks = _parse_official_blocks(content)
    sections = _wac_sections(blocks)
    print(
        {
            "target_paths": parser.paths,
            "block_count": len(blocks),
            "section_count": len(sections),
            "section_clause_locators": {
                citation: [locator for locator, _ in _group_clause_texts(body)]
                for citation, body in sections
            },
        }
    )


if __name__ == "__main__":
    main()
