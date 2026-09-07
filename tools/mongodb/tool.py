"""LangChain tool wrappers for MongoDB persistence."""

from langchain_core.tools import tool

from tools.mongodb.core import mongo_find, mongo_insert


@tool
def save_to_mongodb(text: str, source: str) -> str:
    """Save extracted content into MongoDB.

    Use this when the user explicitly asks to store, save, or persist
    scraped or extracted information.
    """
    return mongo_insert(text, source)


@tool
def search_mongodb(source: str = "") -> str:
    """Search previously stored documents in MongoDB.

    Use this when the user asks about information that was previously saved,
    or asks what documents are in the database.
    """
    return mongo_find(source)
