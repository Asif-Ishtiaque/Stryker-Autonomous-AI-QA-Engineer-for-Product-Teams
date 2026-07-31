"""Parser plugin registry — every KnowledgeSourceType maps to a function
`(raw_bytes, filename) -> list[str]` that extracts plain-text blocks ready
for chunking. Adding support for a new document type is one function plus
one `register_parser` call; the ingestion pipeline never branches on file
extension itself.
"""
from __future__ import annotations

from collections.abc import Callable

from app.domain.enums import KnowledgeSourceType

ParserFn = Callable[[bytes, str], list[str]]

_REGISTRY: dict[KnowledgeSourceType, ParserFn] = {}


def register_parser(source_type: KnowledgeSourceType, fn: ParserFn) -> None:
    _REGISTRY[source_type] = fn


def get_parser(source_type: KnowledgeSourceType) -> ParserFn:
    try:
        return _REGISTRY[source_type]
    except KeyError as exc:
        raise ValueError(f"No parser registered for knowledge source type: {source_type}") from exc
