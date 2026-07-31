"""Registers every built-in parser against its KnowledgeSourceType. Import
this module once at startup (app.main does) before any ingestion runs.
"""
from app.domain.enums import KnowledgeSourceType
from app.rag.parsers.api_spec import parse_openapi, parse_postman_collection
from app.rag.parsers.base import get_parser, register_parser
from app.rag.parsers.csv_parser import parse_csv
from app.rag.parsers.docx_parser import parse_docx
from app.rag.parsers.image_ocr import parse_image
from app.rag.parsers.pdf import parse_pdf
from app.rag.parsers.text_based import parse_markdown, parse_txt

register_parser(KnowledgeSourceType.MARKDOWN, parse_markdown)
register_parser(KnowledgeSourceType.TXT, parse_txt)
register_parser(KnowledgeSourceType.SQL, parse_txt)
register_parser(KnowledgeSourceType.PDF, parse_pdf)
register_parser(KnowledgeSourceType.DOCX, parse_docx)
register_parser(KnowledgeSourceType.CSV, parse_csv)
register_parser(KnowledgeSourceType.IMAGE, parse_image)
register_parser(KnowledgeSourceType.SCREENSHOT, parse_image)
register_parser(KnowledgeSourceType.SWAGGER, parse_openapi)
register_parser(KnowledgeSourceType.OPENAPI, parse_openapi)
register_parser(KnowledgeSourceType.POSTMAN, parse_postman_collection)

__all__ = ["get_parser", "register_parser"]
