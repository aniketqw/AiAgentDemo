"""Tools package: each capability lives in its own subpackage.

This top-level module re-exports all LangChain tool wrappers so the agent
and demo scripts can import them from one place.
"""

from tools.dynamic_scraper.tool import scrape_dynamic
from tools.hindi_pdf_extractor.tool import extract_hindi_pdf
from tools.mongodb.tool import save_to_mongodb, search_mongodb
from tools.pdf_extractor.tool import extract_pdf
from tools.pipelines.tool import extract_and_save_hindi_pdf
from tools.smart_scraper.tool import scrape_web
from tools.static_scraper.tool import scrape_static

__all__ = [
    "scrape_static",
    "scrape_dynamic",
    "scrape_web",
    "extract_pdf",
    "extract_hindi_pdf",
    "extract_and_save_hindi_pdf",
    "save_to_mongodb",
    "search_mongodb",
]
