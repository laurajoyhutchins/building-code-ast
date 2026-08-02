from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


USER_AGENT = (
    "building-code-ast-official-evidence-validation/0.1 "
    "(+https://github.com/laurajoyhutchins/building-code-ast)"
)


@dataclass(frozen=True)
class FetchResult:
    url: str
    final_url: str | None
    status: int | None
    media_type: str | None
    byte_count: int
    sha256: str | None
    error: str | None


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            values = dict(attrs)
            self._href = values.get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            text = " ".join("".join(self._text).split())
            self.links.append((text, self._href))
            self._href = None
            self._text = []


def fetch(url: str) -> tuple[FetchResult, bytes]:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urlopen(request, timeout=60) as response:
            content = response.read()
            media_type = response.headers.get_content_type()
            result = FetchResult(
                url=url,
                final_url=response.geturl(),
                status=response.status,
                media_type=media_type,
                byte_count=len(content),
                sha256=sha256(content).hexdigest(),
                error=None,
            )
            return result, content
    except HTTPError as exc:
        content = exc.read()
        return (
            FetchResult(
                url=url,
                final_url=exc.geturl(),
                status=exc.code,
                media_type=exc.headers.get_content_type() if exc.headers else None,
                byte_count=len(content),
                sha256=sha256(content).hexdigest() if content else None,
                error=f"HTTPError: {exc.reason}",
            ),
            content,
        )
    except (URLError, TimeoutError) as exc:
        return (
            FetchResult(
                url=url,
                final_url=None,
                status=None,
                media_type=None,
                byte_count=0,
                sha256=None,
                error=f"{type(exc).__name__}: {exc}",
            ),
            b"",
        )


def filtered_links(content: bytes, patterns: tuple[str, ...]) -> list[dict[str, str]]:
    text = content.decode("utf-8", errors="replace")
    parser = LinkParser()
    parser.feed(text)
    matches: list[dict[str, str]] = []
    for label, href in parser.links:
        haystack = f"{label} {href}".casefold()
        if any(pattern.casefold() in haystack for pattern in patterns):
            matches.append({"label": label[:160], "href": href})
    return matches


def main() -> None:
    targets = {
        "icc_content_updates": "https://www.iccsafe.org/contentupdates/",
        "icc_group_a": (
            "https://www.iccsafe.org/products-and-services/i-codes/"
            "code-development-process/2024-2026-group-a/"
        ),
        "icc_2021_ibc_errata_html": (
            "https://codes.iccsafe.org/content/IBC2021P2/"
            "editorial-changes-second-printing"
        ),
        "washington_wac_chapter": (
            "https://app.leg.wa.gov/WAC/default.aspx?cite=51-50&full=true"
        ),
        "washington_wac_0403": (
            "https://app.leg.wa.gov/WAC/default.aspx?cite=51-50-0403"
        ),
    }

    fetched: dict[str, dict[str, object]] = {}
    bodies: dict[str, bytes] = {}
    for name, url in targets.items():
        result, content = fetch(url)
        fetched[name] = asdict(result)
        bodies[name] = content

    discovery = {
        "schema_version": "0.1.0",
        "sources": fetched,
        "icc_content_update_links": filtered_links(
            bodies["icc_content_updates"],
            ("2021 international building code", "2021 ibc", "ibc errata"),
        ),
        "icc_development_links": filtered_links(
            bodies["icc_group_a"],
            (
                "ibc general 2024",
                "complete code change monograph",
                "report of the committee action hearing",
            ),
        ),
        "wac_chapter_markers": {
            "wac_heading_count": len(
                re.findall(rb"51-50-[0-9]+", bodies["washington_wac_chapter"])
            ),
            "statutory_authority_count": bodies["washington_wac_chapter"].lower().count(
                b"statutory authority"
            ),
        },
        "wac_0403_markers": {
            "iso_date_count": len(
                re.findall(
                    rb"20[0-9]{2}-[0-9]{2}-[0-9]{2}",
                    bodies["washington_wac_0403"],
                )
            ),
            "effective_word_count": bodies["washington_wac_0403"].lower().count(
                b"effective"
            ),
        },
        "errata_markers": {
            "page_entry_count": len(
                re.findall(rb"Page\s+[A-Z0-9-]+", bodies["icc_2021_ibc_errata_html"])
            ),
            "second_printing_count": bodies["icc_2021_ibc_errata_html"].lower().count(
                b"second printing"
            ),
        },
    }

    output = Path("official-evidence-discovery.json")
    output.write_text(json.dumps(discovery, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
