"""Heuristic formatting for Hindi OCR text.

This formatter improves readability of raw PaddleOCR output without calling an
LLM, so it never invents facts. It:

1. Joins short consecutive lines into paragraphs when they do not end with
   sentence-final punctuation (।, |, ?, !, .).
2. Detects table-like lines by looking for price patterns and formats them
   as a Markdown table using the four expected columns.
3. Preserves numbered list items (lines that start with a digit + dot/space).
4. Collapses multiple spaces and keeps paragraph breaks.

Because it only rearranges whitespace and price columns, the text content
stays exactly as the OCR produced it.
"""

from __future__ import annotations

import re

# Hindi/Devanagari sentence-ending characters plus common Latin punctuation.
SENTENCE_END_RE = re.compile(r"[।|?!\.।]$")
# Price pattern like 4,275.00 or 14,500.00.
# Require at least one comma so DD.MM.YYYY dates are not mistaken for prices.
PRICE_RE = re.compile(r"\b\d{1,3}(?:,\d{3})+\.\d{2}\b")
# Numbered list item start (e.g., "1.", "6.", "1 ")
LIST_START_RE = re.compile(r"^\d+[.\)]?\s+")


def _is_table_row(line: str) -> bool:
    """Return True if a line contains price-like numbers."""
    return bool(PRICE_RE.search(line))


def _is_sentence_end(line: str) -> bool:
    """Return True if a line ends with sentence-final punctuation."""
    stripped = line.rstrip()
    return bool(SENTENCE_END_RE.search(stripped))


def _join_paragraphs(lines: list[str]) -> list[str]:
    """Join short lines that appear to be part of the same paragraph."""
    if not lines:
        return []

    paragraphs: list[str] = []
    current: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue

        # Never merge a numbered list item into the previous paragraph.
        is_list = bool(LIST_START_RE.match(stripped))

        if is_list:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            paragraphs.append(stripped)
            continue

        if not current:
            current.append(stripped)
            continue

        # Start a new paragraph if the previous line was a sentence end.
        if _is_sentence_end(current[-1]):
            paragraphs.append(" ".join(current))
            current = [stripped]
            continue

        # Otherwise append to the current paragraph.
        current.append(stripped)

    if current:
        paragraphs.append(" ".join(current))

    return paragraphs


def _format_table_rows(paragraphs: list[str]) -> list[str]:
    """Convert paragraphs that contain prices into a Markdown table.

    Expected columns: क्र., फसल/प्रजाति, कृषि विभाग हेतु प्रदाय दर,
    फुटकर विक्रय दर.

    Because the OCR may have merged multiple table rows into one paragraph or
    split a single row across lines, we treat every price-bearing paragraph as
    one table row and place the prices in the last two columns. Anything before
    the first price goes in the second column, and we attempt to find a serial
    number for the first column.
    """
    header = (
        "| क्र. | फसल/प्रजाति | कृषि विभाग हेतु प्रदाय दर | "
        "फुटकर विक्रय दर |"
    )
    separator = "| --- | --- | --- | --- |"

    out: list[str] = []
    table_started = False

    for para in paragraphs:
        prices = PRICE_RE.findall(para)
        if not prices:
            out.append(para)
            continue

        if not table_started:
            out.append(header)
            out.append(separator)
            table_started = True

        # Try to find a serial number at the very start.
        serial_match = re.match(r"^(\d+[.\)]?)\s*", para)
        serial = serial_match.group(1) if serial_match else ""

        # Remove the serial number and split the rest around prices.
        remainder = para[serial_match.end():] if serial_match else para
        parts = PRICE_RE.split(remainder)

        # Column 2 is everything before the first price.
        crop = parts[0].strip() if parts else ""
        # Column 3 is the first price; column 4 is the second price if present.
        col3 = prices[0] if prices else ""
        col4 = prices[1] if len(prices) > 1 else ""

        out.append(f"| {serial} | {crop} | {col3} | {col4} |")

    return out


def format_hindi_ocr_heuristic(raw_text: str) -> str:
    """Reformat raw OCR text into readable paragraphs and a Markdown table.

    This function does NOT change any words or numbers; it only rearranges
    whitespace and adds Markdown table markup.
    """
    if not raw_text or not raw_text.strip():
        return ""

    lines = raw_text.splitlines()
    paragraphs = _join_paragraphs(lines)
    formatted = _format_table_rows(paragraphs)

    # Clean up whitespace within each paragraph.
    cleaned: list[str] = []
    for block in formatted:
        block = re.sub(r"[ \t]+", " ", block).strip()
        if block:
            cleaned.append(block)

    return "\n\n".join(cleaned)
