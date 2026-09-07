"""LangChain tool wrapper for Hindi PDF extraction + MongoDB persistence."""

from langchain_core.tools import tool

from tools.pipelines.core import extract_and_save_hindi_pdf_core


@tool
def extract_and_save_hindi_pdf(url: str) -> str:
    """Download a scanned Hindi/Devanagari PDF, extract text with PaddleOCR, and save it to MongoDB.

    Use this single tool when the user wants to extract Hindi text from a PDF
    and persist the result. Do NOT invent the extracted text or the source URL;
    this tool handles both extraction and insertion internally.
    """
    return extract_and_save_hindi_pdf_core(url)
