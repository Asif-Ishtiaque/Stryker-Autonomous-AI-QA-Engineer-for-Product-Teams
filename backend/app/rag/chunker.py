"""Simple, dependency-free text chunker with sentence-aware overlap.

Deliberately not using a tokenizer-exact splitter — for the document types
in scope (PRDs, SRS, API specs, release notes) a character-window chunker
with overlap gives good retrieval recall without pulling in a heavyweight
tokenizer dependency per document type.
"""
from __future__ import annotations

import re

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    text = text.strip()
    if not text:
        return []

    sentences = _SENTENCE_BOUNDARY.split(text)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= chunk_size:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                chunks.append(current)
            overlap_text = current[-overlap:] if overlap and current else ""
            current = f"{overlap_text} {sentence}".strip()

    if current:
        chunks.append(current)

    return chunks or [text[:chunk_size]]
