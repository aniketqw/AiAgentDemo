"""Hindi / Devanagari scanned PDF extraction core.

Tesseract often fails on Devanagari-script government PDFs because it tries to
fit the glyphs into Latin character models. This module uses PaddleOCR with
lang='hi' to extract Hindi text from scanned PDFs.

Pipeline:
1. Download the PDF via requests.
2. Render each page to a PNG image using PyMuPDF.
3. Run PaddleOCR (Hindi model) on each image.
4. Concatenate page text and return.
"""

from __future__ import annotations

import io
import re
from typing import Any

import numpy as np
import pymupdf
import requests
from PIL import Image

from tools.hindi_pdf_extractor.heuristic_formatter import format_hindi_ocr_heuristic
from tools.hindi_pdf_extractor.layout import format_ocr_page
from tools.hindi_pdf_extractor.llm_formatter import format_hindi_ocr_text


def _clean_text(text: str) -> str:
    """Collapse runs of whitespace and keep paragraph breaks readable."""
    if not text:
        return ""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def _get_paddle_ocr() -> Any:
    """Lazy-import PaddleOCR and return a Hindi-configured instance."""
    try:
        from paddleocr import PaddleOCR
    except ImportError as exc:
        raise ImportError(
            "PaddleOCR is required for Hindi PDF extraction. "
            "Install with: pip install paddlepaddle paddleocr"
        ) from exc

    # use_angle_cls helps with rotated text; lang='hi' loads the Hindi model.
    # show_log=False keeps console output quiet.
    return PaddleOCR(
        use_angle_cls=True,
        lang="hi",
        show_log=False,
    )


def _page_image_to_numpy(doc: pymupdf.Document, page_no: int, dpi: int = 300) -> np.ndarray:
    """Render one PDF page to a numpy RGB array for PaddleOCR."""
    page = doc[page_no]
    pix = page.get_pixmap(dpi=dpi)
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    return np.array(img)


def _extract_page_text(ocr: Any, image_np: np.ndarray) -> str:
    """Run PaddleOCR on a single page image and format it into readable lines.

    Uses layout-aware formatting to keep columns and horizontal lines separate.
    """
    # PaddleOCR 2.x: pass cls=True to run angle classification.
    result = ocr.ocr(image_np, cls=True)

    # PaddleOCR returns None for empty pages.
    if result is None or result[0] is None:
        return ""

    page_width = image_np.shape[1]
    return format_ocr_page(result[0], page_width)


def hindi_pdf_extractor(
    url: str,
    timeout: int = 120,
    format_mode: str = "heuristic",
) -> str:
    """Download a Hindi/Devanagari PDF and extract text with PaddleOCR.

    Args:
        url: URL of the scanned Hindi PDF.
        timeout: Request timeout in seconds.
        format_mode: One of:
            - "raw": layout-grouped OCR text exactly as recognized.
            - "heuristic" (default): safe whitespace/table reformatting without
              changing any words or numbers. Recommended for factual work.
            - "llm": local LLM cleanup. More readable but may hallucinate
              table rows or prices; use only when readability matters more
              than perfect factual fidelity.

    Returns:
        Extracted Hindi text, page blocks separated by blank lines.
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    pdf_bytes = response.content

    ocr = _get_paddle_ocr()
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")

    pages: list[str] = []
    try:
        for page_no in range(doc.page_count):
            image_np = _page_image_to_numpy(doc, page_no)
            page_text = _extract_page_text(ocr, image_np)
            if page_text.strip():
                pages.append(page_text)
    finally:
        doc.close()

    raw_text = _clean_text("\n\n".join(pages))

    if format_mode == "raw":
        return raw_text

    if format_mode == "heuristic":
        return format_hindi_ocr_heuristic(raw_text)

    if format_mode == "llm":
        try:
            return format_hindi_ocr_text(raw_text)
        except Exception:
            # If the LLM is unavailable or fails, fall back to heuristic.
            return format_hindi_ocr_heuristic(raw_text)

    raise ValueError(f"Unknown format_mode '{format_mode}'. Use 'raw', 'heuristic', or 'llm'.")
