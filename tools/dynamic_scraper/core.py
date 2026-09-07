"""Dynamic web scraping core.

Launches Chromium via Playwright, waits for JavaScript rendering, and extracts
visible text that a static scraper cannot see.
"""

import re


def _clean_text(text: str) -> str:
    """Collapse runs of whitespace and keep paragraph breaks readable."""
    if not text:
        return ""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def playwright_scraper(url: str, timeout: int = 60) -> str:
    """Render a JavaScript-heavy page with Chromium and return visible text."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ImportError(
            "Playwright is required for dynamic-web scraping. "
            "Install with: pip install playwright && playwright install chromium"
        ) from exc

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
        page.wait_for_timeout(2000)

        text = page.evaluate(
            """
            () => {
                const clone = document.body.cloneNode(true);
                clone.querySelectorAll(
                    'script,style,nav,footer,header,aside,noscript'
                ).forEach(element => element.remove());
                return clone.innerText;
            }
            """
        )
        browser.close()

    return _clean_text(text)
