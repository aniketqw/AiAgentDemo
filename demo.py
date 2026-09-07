"""Standalone CLI to test every capability and the full agent.

Run any layer in isolation:

    python demo.py static <URL>
    python demo.py playwright <URL>
    python demo.py pdf <URL>
    python demo.py mongo
    python demo.py agent "<question>"

This proves that tools work without the LLM, and the agent works by
composition of those tools.
"""

from __future__ import annotations

import sys

from agent import agent_executor as agent
from tools import (
    extract_pdf,
    save_to_mongodb,
    scrape_dynamic,
    scrape_static,
    search_mongodb,
)

PREVIEW_LENGTH = 3000


def _print_preview(text: str) -> None:
    """Print the first PREVIEW_LENGTH characters with a clear boundary."""
    print("-" * 60)
    print(text[:PREVIEW_LENGTH])
    print("-" * 60)
    if len(text) > PREVIEW_LENGTH:
        print(f"\n... ({len(text) - PREVIEW_LENGTH} more characters)")


def _usage() -> None:
    print("Usage:")
    print("  python demo.py static <URL>")
    print("  python demo.py playwright <URL>")
    print("  python demo.py pdf <URL>")
    print("  python demo.py mongo [optional_source_filter]")
    print("  python demo.py save <text> <source>")
    print("  python demo.py agent \"<question>\"")


def main() -> int:
    if len(sys.argv) < 2:
        _usage()
        return 1

    command = sys.argv[1].lower()

    # ------------------------------------------------------------------
    # Static scraper
    # ------------------------------------------------------------------
    if command == "static":
        if len(sys.argv) < 3:
            print("Please provide a URL.")
            return 1
        url = sys.argv[2]
        print(f"Static scrape: {url}\n")
        text = scrape_static.invoke(url)
        _print_preview(text)
        return 0

    # ------------------------------------------------------------------
    # Playwright scraper
    # ------------------------------------------------------------------
    if command == "playwright":
        if len(sys.argv) < 3:
            print("Please provide a URL.")
            return 1
        url = sys.argv[2]
        print(f"Playwright scrape: {url}\n")
        text = scrape_dynamic.invoke(url)
        _print_preview(text)
        return 0

    # ------------------------------------------------------------------
    # PDF extractor
    # ------------------------------------------------------------------
    if command == "pdf":
        if len(sys.argv) < 3:
            print("Please provide a PDF URL.")
            return 1
        url = sys.argv[2]
        print(f"PDF extract: {url}\n")
        text = extract_pdf.invoke(url)
        _print_preview(text)
        return 0

    # ------------------------------------------------------------------
    # MongoDB search
    # ------------------------------------------------------------------
    if command == "mongo":
        source_filter = sys.argv[2] if len(sys.argv) > 2 else ""
        print("MongoDB search:\n")
        result = search_mongodb.invoke(source_filter)
        print(result)
        return 0

    # ------------------------------------------------------------------
    # MongoDB save (direct test)
    # ------------------------------------------------------------------
    if command == "save":
        if len(sys.argv) < 4:
            print("Please provide text and source.")
            return 1
        text = sys.argv[2]
        source = sys.argv[3]
        print("MongoDB save:\n")
        result = save_to_mongodb.invoke({"text": text, "source": source})
        print(result)
        return 0

    # ------------------------------------------------------------------
    # Full ReAct agent
    # ------------------------------------------------------------------
    if command == "agent":
        if len(sys.argv) < 3:
            print("Please provide a question.")
            return 1
        question = " ".join(sys.argv[2:])
        print(f"Agent query: {question}\n")
        result = agent.invoke({"input": question})
        print("\nFinal answer:")
        print("-" * 60)
        print(result["output"])
        print("-" * 60)
        return 0

    print(f"Unknown command: {command}\n")
    _usage()
    return 1


if __name__ == "__main__":
    sys.exit(main())
