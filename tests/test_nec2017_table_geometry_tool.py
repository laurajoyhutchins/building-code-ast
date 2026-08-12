from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import measure_nec2017_table_geometry as runner


class _Rect:
    width = 612.0
    height = 792.0


class _Page:
    rect = _Rect()

    def __init__(self, first: bool) -> None:
        self._first = first

    def get_text(self, mode: str, sort: bool = False) -> dict[str, object]:
        del mode, sort
        if not self._first:
            return {"blocks": []}
        return {
            "blocks": [
                {
                    "type": 0,
                    "number": 7,
                    "bbox": (50.0, 80.0, 250.0, 120.0),
                    "lines": [
                        {
                            "bbox": (50.0, 80.0, 250.0, 90.0),
                            "dir": (1.0, 0.0),
                            "spans": [
                                {
                                    "text": "Table 1",
                                    "bbox": (50.0, 80.0, 90.0, 90.0),
                                    "size": 10.0,
                                    "font": "Synthetic",
                                }
                            ],
                        },
                        {
                            "bbox": (50.0, 100.0, 250.0, 110.0),
                            "dir": (1.0, 0.0),
                            "spans": [
                                {
                                    "text": "Table-shaped row",
                                    "bbox": (50.0, 100.0, 150.0, 110.0),
                                    "size": 10.0,
                                    "font": "Synthetic",
                                }
                            ],
                        },
                    ],
                }
            ]
        }

    def get_drawings(self) -> list[object]:
        return []


class _Document:
    page_count = 881

    def __enter__(self) -> "_Document":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def __getitem__(self, index: int) -> _Page:
        return _Page(index == 0)


class Nec2017TableGeometryToolTests(unittest.TestCase):
    def test_table_announcement_is_counted_once_per_text_block(self) -> None:
        fake_fitz = types.SimpleNamespace(open=lambda _path: _Document())
        with patch.dict(sys.modules, {"fitz": fake_fitz}):
            pages, captions, unsupported = runner._extract(Path("unused.pdf"))
        self.assertEqual(len(pages), 881)
        self.assertEqual(len(captions), 1)
        self.assertEqual(captions[0].caption_id, "p1:b7")
        self.assertEqual(unsupported, 0)


if __name__ == "__main__":
    unittest.main()
