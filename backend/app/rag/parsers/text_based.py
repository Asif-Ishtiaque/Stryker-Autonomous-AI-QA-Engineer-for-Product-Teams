from __future__ import annotations

from markdown_it import MarkdownIt

_md = MarkdownIt()


def parse_txt(raw: bytes, filename: str) -> list[str]:
    return [raw.decode("utf-8", errors="replace")]


def parse_markdown(raw: bytes, filename: str) -> list[str]:
    text = raw.decode("utf-8", errors="replace")
    # Render then strip tags via the token stream so headings/lists/tables read
    # as plain sentences rather than raw markdown syntax — better embeddings.
    tokens = _md.parse(text)
    blocks: list[str] = []
    buffer: list[str] = []
    for token in tokens:
        if token.type in ("heading_open",) and buffer:
            blocks.append(" ".join(buffer))
            buffer = []
        if token.type == "inline":
            buffer.append(token.content)
    if buffer:
        blocks.append(" ".join(buffer))
    return blocks or [text]
