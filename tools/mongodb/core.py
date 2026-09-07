"""MongoDB persistence core.

Plain Python functions for inserting and searching documents in the shared
collection configured in config.py.
"""

from bson import ObjectId

from config import collection


def mongo_insert(text: str, source: str) -> str:
    """Insert a document with source URL and extracted text."""
    document = {"source": source, "text": text}
    result = collection.insert_one(document)
    return f"Inserted document {result.inserted_id}"


def mongo_find(source: str = "") -> str:
    """Search stored documents; optionally filter by source."""
    query = {}
    if source:
        query["source"] = source

    documents = collection.find(query).limit(10)
    results = []
    for doc in documents:
        results.append({
            "id": str(doc["_id"]),
            "source": doc.get("source"),
            "text": doc.get("text", "")[:500],
        })
    return str(results)
