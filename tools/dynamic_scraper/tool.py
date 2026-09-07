"""LangChain tool wrapper for the dynamic / Playwright scraper."""

from langchain_core.tools import tool

from tools.dynamic_scraper.core import playwright_scraper


@tool
def scrape_dynamic(url: str) -> str:
    """Render a JavaScript-heavy website using Playwright/Chromium.

    Use this when webpage content is dynamically generated and a normal
    static scraper cannot see it.
    """
    return playwright_scraper(url)
