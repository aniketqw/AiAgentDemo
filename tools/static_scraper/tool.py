"""LangChain tool wrapper for the static scraper."""

from langchain_core.tools import tool

from tools.static_scraper.core import static_scraper


@tool
def scrape_static(url: str) -> str:
    """Scrape a normal static HTML website.

    Use this when the webpage content is already present in the server
    response and does not require JavaScript.
    """
    return static_scraper(url)
