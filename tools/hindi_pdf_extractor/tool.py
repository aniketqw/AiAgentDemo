"""LangChain tool wrapper for Hindi / Devanagari PDF extraction."""

from langchain_core.tools import tool

from tools.hindi_pdf_extractor.core import hindi_pdf_extractor


@tool
def extract_hindi_pdf(url: str) -> str:
    """Download a scanned Hindi/Devanagari PDF and extract text using PaddleOCR.

    Use this when the PDF is in Hindi script (Devanagari), such as government
    circulars from Uttar Pradesh Agriculture Department. For English text-based
    PDFs, use extract_pdf instead.
    """
    return hindi_pdf_extractor(url)
