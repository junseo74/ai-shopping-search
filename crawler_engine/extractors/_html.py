from __future__ import annotations

from html.parser import HTMLParser
from typing import Optional


class ScriptExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.scripts: list[dict[str, str | None]] = []
        self._current: Optional[dict[str, str | None]] = None
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        attr_map = {key.lower(): value for key, value in attrs}
        self._current = {
            "type": attr_map.get("type"),
            "id": attr_map.get("id"),
            "content": "",
        }
        self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "script" or self._current is None:
            return
        self._current["content"] = "".join(self._buffer)
        self.scripts.append(self._current)
        self._current = None
        self._buffer = []


def extract_scripts(html: str) -> list[dict[str, str | None]]:
    parser = ScriptExtractor()
    parser.feed(html)
    return parser.scripts
