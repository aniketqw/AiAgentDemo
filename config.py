"""Shared configuration and clients for the student LangChain + Ollama demo.

This module keeps all external service setup in one place:
- Ollama LLM client
- MongoDB client and collection

Every other module imports clients from here so there is no hidden
configuration inside tools or the agent.
"""

import os

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from pymongo import MongoClient

# Load environment variables from .env if present.
load_dotenv()

# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

llm = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_BASE_URL,
    temperature=0,
)

# ---------------------------------------------------------------------------
# MongoDB
# ---------------------------------------------------------------------------
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "agent_demo")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "documents")

mongo_client = MongoClient(MONGODB_URI)
db = mongo_client[MONGODB_DB_NAME]
collection = db[MONGODB_COLLECTION]


def test_mongodb() -> bool:
    """Ping MongoDB to verify the connection is alive."""
    mongo_client.admin.command("ping")
    return True
