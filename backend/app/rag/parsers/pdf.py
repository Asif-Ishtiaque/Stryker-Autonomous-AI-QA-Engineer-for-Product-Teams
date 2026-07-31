from __future__ import annotations

import io

from pypdf import PdfReader


def parse_pdf(raw: bytes, filename: str) -> list[str]:
    reader = PdfReader(io.BytesIO(raw))
    blocks: list[str] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            blocks.append(f"[{filename} p.{page_number}] {text}")
    return blocks
