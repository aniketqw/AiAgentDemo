"""LangChain tool wrapper for the smart static-then-Playwright scraper."""

from langchain_core.tools import tool

from tools.smart_scraper.core import scrape_with_fallback


@tool
def scrape_web(url: str) -> str:
    """Scrape a webpage using the smart static-then-Playwright fallback.

    Use this when you are unsure whether the page is static or dynamic.
    It will try a fast static fetch first and only launch Chromium if the
    result looks like an empty JavaScript shell.
    """
    return scrape_with_fallback(url)
