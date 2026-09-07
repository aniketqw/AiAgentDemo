"""LLM-based cleanup for Hindi OCR text.

Raw OCR output from scanned government PDFs is often noisy: words are split
across lines, Latin characters are mis-recognized in place of Devanagari glyphs,
and tables lose their structure. This module sends the raw text to a local
Ollama model with a strict prompt that asks it to reconstruct readable Hindi
paragraphs and tables while preserving every fact (dates, numbers, names,
order references, prices).

The cleaned text is returned as the "readable" version; the raw OCR text can
still be kept for comparison.
"""

from __future__ import annotations

import json
import os

import requests

from config import OLLAMA_BASE_URL, OLLAMA_MODEL


CLEANUP_PROMPT = """\
You are a Hindi document cleanup assistant. I will give you raw OCR text from a scanned Uttar Pradesh Agriculture Department government order written in Devanagari script.

Your job:
1. Reconstruct the text into clean, readable Hindi paragraphs.
2. Fix obvious OCR misrecognitions where Latin characters were substituted for Devanagari characters (for example "Plofah" should become "प्रदाय", "OhoG" should become "विभाग", "h?h" should become "पर" or "हेतु" depending on context, "PaJha" should become "प्रभाव", "IGP" should become "रु0", "b/h" should become "प्रति", "Illth ki" should become "प्रति कुन्तल", etc.).
3. Preserve all factual information exactly as written: order numbers, dates, prices (e.g. 4,275.00, 4,500.00, 1,275.00, 14,500.00), file references, and names of crops (गेहूँ, सरसों, अलसी, मटर, मसूर, etc.).
4. Format the seed-rate table clearly using a simple Markdown table with columns: क्र., फसल/प्रजाति, कृषि विभाग हेतु प्रदाय दर, फुटकर विक्रय दर.
5. Do NOT invent any information. If a word is too garbled to recover, keep the original OCR fragment in square brackets like [Plofah?].
6. Return ONLY the cleaned Hindi/Devanagari text with headings, paragraphs, and the table. Do not add any explanation or English commentary outside the document.

Raw OCR text:
{text}

Cleaned Hindi document:
"""


def _ollama_generate(prompt: str, timeout: int = 120) -> str:
    """Call Ollama /api/generate directly with a timeout."""
    url = os.path.join(OLLAMA_BASE_URL, "api", "generate")
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 2048,
        },
    }
    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    return data.get("response", "").strip()


def format_hindi_ocr_text(raw_text: str, timeout: int = 120) -> str:
    """Clean and reformat raw Hindi OCR text using the local Ollama LLM.

    Args:
        raw_text: Raw OCR text from PaddleOCR.
        timeout: Seconds to wait for the Ollama response.

    Returns:
        Cleaned, readable Hindi text.
    """
    if not raw_text or not raw_text.strip():
        return ""

    prompt = CLEANUP_PROMPT.format(text=raw_text)
    return _ollama_generate(prompt, timeout=timeout)
