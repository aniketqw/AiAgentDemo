"""End-to-end pipeline helpers.

These functions combine extraction + persistence in a single call so that a
local LLM does not have to remember the exact text across two separate tool
calls. They are still built on top of the standalone tools; only the agent-level
tool wrapper changes.
"""

from tools.hindi_pdf_extractor.core import hindi_pdf_extractor
from tools.mongodb.core import mongo_insert


def extract_and_save_hindi_pdf_core(url: str) -> str:
    """Extract Hindi text from *url* and immediately save it to MongoDB.

    Returns a message containing the number of characters extracted and the
    MongoDB insertion result.
    """
    text = hindi_pdf_extractor(url)
    insert_msg = mongo_insert(text, url)
    return (
        f"Extracted {len(text)} characters from {url}. {insert_msg}. "
        "Return only this message to the user."
    )
