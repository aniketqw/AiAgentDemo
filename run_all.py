"""End-to-end runner: download every source, run each tool, run the agent.

This script demonstrates the full acquisition pipeline in one command:

1. Reads sources.csv.
2. Downloads each source to data/<source_id>/raw.<ext>.
3. Extracts text with the right tool and saves data/<source_id>/extracted.txt.
4. Persists the extracted text to MongoDB.
5. Asks the agent to perform the same task end-to-end and saves the response.

All output is logged to logs/run_all.log.

Usage:
    python run_all.py
"""

from __future__ import annotations

import csv
import io
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

from agent import agent_executor as agent
from config import test_mongodb
from tools import (
    extract_and_save_hindi_pdf,
    extract_hindi_pdf,
    extract_pdf,
    save_to_mongodb,
    scrape_dynamic,
    scrape_web,
)
from tools.hindi_pdf_extractor.core import hindi_pdf_extractor

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
SOURCE_CSV = Path(
    "/Users/aniketsaxena/Documents/p/from_aug_1/p0/dailyPrep/5sep/sources.csv"
)

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("run_all")
logger.setLevel(logging.INFO)
logger.propagate = False
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

file_handler = logging.FileHandler(LOGS_DIR / "run_all.log", mode="w", encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_sources(csv_path: Path) -> list[dict[str, str]]:
    """Load the source registry CSV."""
    with csv_path.open("r", encoding="utf-8") as f:
        return [row for row in csv.DictReader(f)]


def _filename_from_url(url: str) -> str:
    """Pick a sensible raw filename from a URL."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        return "raw"
    last = path.split("/")[-1]
    # If the last segment looks like a file extension, keep it.
    if "." in last[-8:]:
        return last[:128]
    return "raw"


def _extension_from_url(url: str) -> str:
    """Guess a file extension from a URL."""
    parsed = urlparse(url)
    path = parsed.path.lower()
    if path.endswith(".pdf"):
        return ".pdf"
    if path.endswith((".html", ".htm")):
        return ".html"
    if path.endswith(".json"):
        return ".json"
    if path.endswith(".txt"):
        return ".txt"
    return ".html"


# Browser-like headers so sites like ICAR-IIPR do not block plain requests.
DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def download_source(source: dict[str, str]) -> Path:
    """Download the raw source bytes and save under data/<source_id>/."""
    source_id = source["source_id"]
    url = source["url"]
    modality = source["modality"].lower().strip()

    out_dir = DATA_DIR / source_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # For PDFs keep the .pdf extension so tools can read the file directly.
    if modality == "pdf":
        ext = ".pdf"
        filename = "raw.pdf"
    else:
        ext = _extension_from_url(url)
        filename = f"raw{ext}"

    out_path = out_dir / filename

    logger.info("[%s] Downloading %s -> %s", source_id, url, out_path)
    response = requests.get(url, headers=DOWNLOAD_HEADERS, timeout=120)
    response.raise_for_status()
    out_path.write_bytes(response.content)
    logger.info("[%s] Saved %d bytes", source_id, len(response.content))

    return out_path


# ---------------------------------------------------------------------------
# Tool routing
# ---------------------------------------------------------------------------


def extract_with_tool(source: dict[str, str]) -> tuple[str, str]:
    """Pick the right tool for a source and return (tool_name, extracted_text)."""
    modality = source["modality"].lower().strip()
    url = source["url"]
    source_id = source["source_id"]

    # UP Agriculture seed-rates PDF is scanned Hindi; force PaddleOCR.
    if source_id == "up_agri_seed_rates":
        logger.info("[%s] Overriding modality '%s' -> extract_hindi_pdf", source_id, modality)
        return "extract_hindi_pdf", extract_hindi_pdf.invoke(url)

    if modality == "dynamic_web":
        return "scrape_dynamic", scrape_dynamic.invoke(url)

    if modality in ("web", "web_doc"):
        return "scrape_web", scrape_web.invoke(url)

    if modality == "pdf":
        return "extract_pdf", extract_pdf.invoke(url)

    raise ValueError(f"Unknown modality '{modality}' for source {source_id}")


# ---------------------------------------------------------------------------
# Agent prompt factory
# ---------------------------------------------------------------------------


def agent_prompt_for(source: dict[str, str]) -> str:
    """Create a natural-language task for the agent to mirror the tool run."""
    modality = source["modality"].lower().strip()
    url = source["url"]
    source_id = source["source_id"]
    name = source.get("name", source_id)

    if source_id == "up_agri_seed_rates" or modality == "pdf" and "up.gov.in" in url:
        return (
            f"Extract this Hindi UP Agriculture PDF and save it to MongoDB: {url}"
        )

    if modality == "pdf":
        return f"Extract text from this PDF and save it to MongoDB: {url}"

    if modality == "dynamic_web":
        return (
            f"Use Playwright to scrape this JavaScript-rendered page and save "
            f"the result to MongoDB: {url}"
        )

    return (
        f"Acquire the content from this agriculture source and save it to "
        f"MongoDB: {url}"
    )


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------


def run_all() -> int:
    logger.info("=" * 80)
    logger.info("END-TO-END RUNNER")
    logger.info("Project: %s", PROJECT_ROOT)
    logger.info("Sources: %s", SOURCE_CSV)
    logger.info("Data dir: %s", DATA_DIR)
    logger.info("Started at: %s", datetime.now(timezone.utc).isoformat())
    logger.info("=" * 80)

    try:
        test_mongodb()
        logger.info("MongoDB connection: OK")
    except Exception as exc:
        logger.error("MongoDB connection failed: %s", exc)
        return 1

    sources = load_sources(SOURCE_CSV)
    logger.info("Loaded %d source(s)", len(sources))

    results: list[dict] = []

    for source in sources:
        source_id = source["source_id"]
        logger.info("")
        logger.info("-" * 80)
        logger.info("SOURCE: %s (%s)", source_id, source.get("name", ""))
        logger.info("MODALITY: %s", source["modality"])
        logger.info("URL: %s", source["url"])
        logger.info("-" * 80)

        result = {
            "source_id": source_id,
            "download": None,
            "tool": None,
            "tool_chars": 0,
            "tool_error": "",
            "agent": None,
            "agent_answer": "",
            "agent_error": "",
        }

        # Step 1: Download
        try:
            raw_path = download_source(source)
            result["download"] = str(raw_path)
        except Exception as exc:
            logger.error("[%s] Download failed: %s", source_id, exc)
            result["tool_error"] = f"Download failed: {exc}"
            results.append(result)
            continue

        # Step 2: Extract with the right tool
        try:
            tool_name, extracted = extract_with_tool(source)
            result["tool"] = tool_name
            result["tool_chars"] = len(extracted)
            extracted_path = DATA_DIR / source_id / "extracted.txt"
            extracted_path.write_text(extracted, encoding="utf-8")
            logger.info(
                "[%s] Tool '%s' extracted %d chars -> %s",
                source_id, tool_name, len(extracted), extracted_path,
            )

            # Step 3: Save to MongoDB
            insert_result = save_to_mongodb.invoke({
                "text": extracted,
                "source": source["url"],
            })
            logger.info("[%s] MongoDB: %s", source_id, insert_result)
        except Exception as exc:
            logger.error("[%s] Tool extraction/save failed: %s", source_id, exc)
            result["tool_error"] = f"Tool extraction failed: {exc}"
            results.append(result)
            continue

        # Step 4: Run the agent end-to-end
        prompt = agent_prompt_for(source)
        logger.info("[%s] Agent prompt: %s", source_id, prompt)
        try:
            response = agent.invoke(
                {"messages": [{"role": "user", "content": prompt}]},
                config={"configurable": {"thread_id": f"run-all-{source_id}"}},
            )
            answer = response["messages"][-1].content
            result["agent"] = "success"
            result["agent_answer"] = answer
            agent_path = DATA_DIR / source_id / "agent_answer.txt"
            agent_path.write_text(answer, encoding="utf-8")
            logger.info("[%s] Agent answer -> %s", source_id, agent_path)
            logger.info("[%s] Agent answer preview: %s", source_id, answer[:300].replace("\n", " "))
        except Exception as exc:
            logger.error("[%s] Agent failed: %s", source_id, exc)
            result["agent"] = "failed"
            result["agent_error"] = str(exc)

        results.append(result)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    logger.info("")
    logger.info("=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    for r in results:
        status = "OK" if not r["tool_error"] else "TOOL_FAIL"
        agent_status = r["agent"] if r["agent"] else "SKIPPED"
        logger.info(
            "%s | download=%s | tool=%s (%d chars) | agent=%s",
            r["source_id"],
            "OK" if r["download"] else "FAIL",
            r["tool"] if not r["tool_error"] else r["tool_error"][:60],
            r["tool_chars"],
            agent_status,
        )
    logger.info("=" * 80)

    # Write a machine-readable summary file as well.
    summary_path = DATA_DIR / "summary.txt"
    summary_lines = [
        f"Run at: {datetime.now(timezone.utc).isoformat()}",
        f"Sources: {len(sources)}",
        "",
    ]
    for r in results:
        summary_lines.append(
            f"{r['source_id']} | tool={r['tool']} | tool_chars={r['tool_chars']} | "
            f"agent={r['agent']} | tool_error={r['tool_error']} | agent_error={r['agent_error']}"
        )
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
    logger.info("Summary written to: %s", summary_path)

    return 0


if __name__ == "__main__":
    sys.exit(run_all())
