"""Static web scraping core.

Plain Python function using requests + BeautifulSoup.
No browser, no JavaScript execution.
"""

import re

import requests
from bs4 import BeautifulSoup


def _clean_text(text: str) -> str:
    """Collapse runs of whitespace and keep paragraph breaks readable."""
    if not text:
        return ""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def static_scraper(url: str, timeout: int = 60) -> str:
    """Fetch a static HTML page and return cleaned visible text."""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; StudentAgentDemo/1.0)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove non-content elements.
    for selector in ["script", "style", "nav", "footer", "header", "aside", "noscript"]:
        for tag in soup.find_all(selector):
            tag.decompose()

    # Prefer article/main content; fallback to whole body or full document.
    main = soup.find("main") or soup.find("article") or soup.find(
        "div", class_=re.compile(r"content|main")
    )
    if main:
        text = main.get_text(separator="\n", strip=True)
    else:
        text = soup.get_text(separator="\n", strip=True)

    return _clean_text(text)
