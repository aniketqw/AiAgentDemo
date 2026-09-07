"""LangChain tool wrapper for the PDF extractor."""

from langchain_core.tools import tool

from tools.pdf_extractor.core import pdf_extractor


@tool
def extract_pdf(url: str) -> str:
    """Download a PDF and extract its text.

    Uses PDF text extraction first, then OCR fallback for scanned/image PDFs.
    """
    return pdf_extractor(url)
