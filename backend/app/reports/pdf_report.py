"""Renders an already-generated Markdown report to PDF. No second LLM call —
PDF is purely a presentation transform of the same content used for the
Markdown/JSON reports.
"""
from __future__ import annotations

from markdown_it import MarkdownIt
from weasyprint import HTML

_md = MarkdownIt()

_CSS = """
body { font-family: -apple-system, Helvetica, Arial, sans-serif; color: #111; line-height: 1.5; margin: 2.5cm; }
h1, h2 { color: #0f172a; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.3em; }
code { background: #f1f5f9; padding: 0.1em 0.3em; border-radius: 4px; }
"""


def render_pdf(markdown: str, title: str) -> bytes:
    html_body = _md.render(markdown)
    full_html = f"<html><head><meta charset='utf-8'><title>{title}</title><style>{_CSS}</style></head><body>{html_body}</body></html>"
    return HTML(string=full_html).write_pdf()
