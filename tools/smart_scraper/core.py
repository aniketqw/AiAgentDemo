"""Smart scrape-with-fallback core.

Tries the fast static scraper first, and only launches the heavier Playwright
browser if the result looks like an empty JavaScript app shell.
"""

from tools.dynamic_scraper.core import playwright_scraper
from tools.static_scraper.core import static_scraper


def _is_js_app_shell(text: str) -> bool:
    """Heuristic: page looks like an empty JS shell if very short or framework-heavy."""
    stripped = text.strip()
    if len(stripped) < 800:
        return True

    agri_terms = {
        "crop",
        "variety",
        "yield",
        "q/ha",
        "fertilizer",
        "seed",
        "agriculture",
        "rabi",
        "kharif",
    }
    lower = stripped.lower()
    if any(term in lower for term in agri_terms):
        return False

    framework_markers = {"react", "ng-app", "vue", "next.js", "__next", "data-reactroot"}
    if any(marker in lower for marker in framework_markers):
        return True

    return False


def scrape_with_fallback(url: str, timeout: int = 60) -> str:
    """Try static scraping first; fall back to Playwright if content looks like a JS shell."""
    text = static_scraper(url, timeout=timeout)
    if _is_js_app_shell(text):
        return playwright_scraper(url, timeout=timeout)
    return text
