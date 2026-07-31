"""Parsers for OpenAPI/Swagger specs and Postman collections.

These don't just dump raw JSON into the knowledge base — they extract one
readable sentence per endpoint/request so semantic search actually matches
"how do I create an invoice" against the right operation instead of a wall
of nested JSON tokens.
"""
from __future__ import annotations

import json


def parse_openapi(raw: bytes, filename: str) -> list[str]:
    spec = json.loads(raw)
    blocks: list[str] = []
    info = spec.get("info", {})
    if info:
        blocks.append(f"API: {info.get('title', filename)} v{info.get('version', '?')} — {info.get('description', '')}")

    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            if not isinstance(operation, dict):
                continue
            summary = operation.get("summary") or operation.get("operationId") or ""
            description = operation.get("description", "")
            params = ", ".join(p.get("name", "") for p in operation.get("parameters", []) if isinstance(p, dict))
            blocks.append(
                f"{method.upper()} {path} — {summary}. {description} "
                f"Parameters: {params or 'none'}."
            )
    return blocks


def parse_postman_collection(raw: bytes, filename: str) -> list[str]:
    collection = json.loads(raw)
    blocks: list[str] = []

    def walk(item: dict) -> None:
        if "item" in item:
            for child in item["item"]:
                walk(child)
            return
        request = item.get("request", {})
        method = request.get("method", "GET")
        url = request.get("url", {})
        url_str = url if isinstance(url, str) else url.get("raw", "")
        name = item.get("name", "")
        description = request.get("description", "")
        blocks.append(f"{method} {url_str} — {name}. {description}")

    for item in collection.get("item", []):
        walk(item)

    return blocks
