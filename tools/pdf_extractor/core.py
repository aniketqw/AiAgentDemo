"""PDF extraction core.

Downloads a PDF and extracts text through a fallback chain:
1. pypdf (fast, text-based PDFs)
2. pymupdf (better encoding support)
3. OCR via pymupdf + pytesseract (scanned / image PDFs)
"""

from __future__ import annotations

import io
from typing import Any

import pymupdf
from PIL import Image
from pypdf import PdfReader


def _clean_text(text: str) -> str:
    """Collapse runs of whitespace and keep paragraph breaks readable."""
    if not text:
        return ""
    import re

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def _extract_with_pypdf(pdf_bytes: bytes) -> list[dict[str, Any]]:
    """Strategy 1: fast text extraction for normal PDFs."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages: list[dict[str, Any]] = []
    for page_no, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        text = _clean_text(raw)
        if text:
            pages.append({"page": page_no, "text": text})
    return pages


def _extract_with_pymupdf(pdf_bytes: bytes) -> list[dict[str, Any]]:
    """Strategy 2: better encoding support."""
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    pages: list[dict[str, Any]] = []
    for page_no in range(doc.page_count):
        text = _clean_text(doc[page_no].get_text())
        if text:
            pages.append({"page": page_no + 1, "text": text})
    doc.close()
    return pages


def _extract_with_ocr(pdf_bytes: bytes, dpi: int = 300) -> list[dict[str, Any]]:
    """Strategy 3: OCR for scanned / image PDFs."""
    try:
        import pytesseract
    except ImportError as exc:
        raise ImportError(
            "OCR fallback requires pytesseract. Install with: pip install pytesseract"
        ) from exc

    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    pages: list[dict[str, Any]] = []
    for page_no in range(doc.page_count):
        pix = doc[page_no].get_pixmap(dpi=dpi)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text = _clean_text(pytesseract.image_to_string(img))
        if text:
            pages.append({"page": page_no + 1, "text": text, "ocr": True})
    doc.close()
    return pages


def pdf_extractor(url: str, timeout: int = 60) -> str:
    """Download a PDF and extract text using pypdf -> pymupdf -> OCR fallback chain."""
    import requests

    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    pdf_bytes = response.content

    # Strategy 1: pypdf
    pages = _extract_with_pypdf(pdf_bytes)
    if pages:
        return "\n\n".join(p["text"] for p in pages)

    # Strategy 2: pymupdf
    pages = _extract_with_pymupdf(pdf_bytes)
    if pages:
        return "\n\n".join(p["text"] for p in pages)

    # Strategy 3: OCR
    pages = _extract_with_ocr(pdf_bytes)
    return "\n\n".join(p["text"] for p in pages)
