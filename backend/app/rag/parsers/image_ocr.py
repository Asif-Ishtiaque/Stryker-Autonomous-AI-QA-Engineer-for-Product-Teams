from __future__ import annotations

import io

import pytesseract
from PIL import Image


def parse_image(raw: bytes, filename: str) -> list[str]:
    image = Image.open(io.BytesIO(raw))
    text = pytesseract.image_to_string(image).strip()
    return [f"[OCR:{filename}] {text}"] if text else []
