from __future__ import annotations

from typing import Protocol

from .models import CrawlRequest, SourceMetadata
from .sites.danawa import DanawaSource
from .sites.joongna import JoongnaSource


class CrawlSource(Protocol):
    metadata: SourceMetadata

    def build_search_url(self, request: CrawlRequest) -> str:
        ...


def available_sources() -> dict[str, CrawlSource]:
    sources: list[CrawlSource] = [
        JoongnaSource(),
        DanawaSource(),
    ]
    return {source.metadata.source: source for source in sources}


def select_sources(request: CrawlRequest, source_name: str | None = None) -> list[CrawlSource]:
    sources = available_sources()
    if source_name:
        source = sources.get(source_name)
        if not source:
            raise ValueError(f"Unknown crawler source: {source_name}")
        selected = [source]
    else:
        selected = list(sources.values())

    if not request.include_used:
        selected = [source for source in selected if not source.metadata.used_only]
    return selected
