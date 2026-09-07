"""No-LLM test runner for every source in sources.csv.

This script loads the original source registry, tests each acquisition
capability directly (no agent, no LLM), and produces:

  - test/logs/<source_id>.log     full terminal output for that source
  - test/outputs/<source_id>.txt  final extracted text
  - MongoDB documents             one per source in the configured collection

Usage:
    python test/test_sources.py

It also prints a final summary table to the terminal.
"""

from __future__ import annotations

import csv
import logging
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is importable when running from test/.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import test_mongodb
from tools.dynamic_scraper.tool import scrape_dynamic
from tools.mongodb.tool import save_to_mongodb
from tools.pdf_extractor.tool import extract_pdf
from tools.smart_scraper.tool import scrape_web

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SOURCE_CSV = Path("/Users/aniketsaxena/Documents/p/from_aug_1/p0/dailyPrep/5sep/sources.csv")

TEST_DIR = Path(__file__).resolve().parent
LOGS_DIR = TEST_DIR / "logs"
OUTPUTS_DIR = TEST_DIR / "outputs"

LOGS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Tool router
# ---------------------------------------------------------------------------

TOOL_ROUTER = {
    "web": scrape_web,
    "web_doc": scrape_web,
    "dynamic_web": scrape_dynamic,
    "pdf": extract_pdf,
}


def load_sources(csv_path: Path) -> list[dict[str, str]]:
    """Load the source registry CSV."""
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def setup_logger(source_id: str) -> logging.Logger:
    """Create a logger that writes to both terminal and a per-source log file."""
    logger = logging.getLogger(source_id)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Clear any existing handlers from previous runs in this process.
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Terminal output
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # File output
    log_file = LOGS_DIR / f"{source_id}.log"
    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger, log_file


def test_source(source: dict[str, str]) -> dict[str, str]:
    """Run the appropriate acquisition tool for one source and save everything."""
    source_id = source["source_id"]
    modality = source["modality"].lower().strip()
    url = source["url"]
    name = source.get("name", source_id)

    logger, log_file = setup_logger(source_id)
    result = {
        "source_id": source_id,
        "modality": modality,
        "url": url,
        "status": "pending",
        "chars": "0",
        "mongodb_id": "",
        "output_file": "",
        "log_file": str(log_file),
        "error": "",
    }

    logger.info("=" * 70)
    logger.info("SOURCE: %s", source_id)
    logger.info("NAME:   %s", name)
    logger.info("MODALITY: %s", modality)
    logger.info("URL:    %s", url)
    logger.info("=" * 70)

    tool_func = TOOL_ROUTER.get(modality)
    if tool_func is None:
        message = f"Unknown modality '{modality}' — no tool available."
        logger.error(message)
        result["status"] = "skipped"
        result["error"] = message
        return result

    try:
        logger.info("Invoking tool: %s", tool_func.name)
        extracted_text = tool_func.invoke(url)

        if not extracted_text or not extracted_text.strip():
            raise ValueError("Tool returned empty text.")

        char_count = len(extracted_text)
        logger.info("Extraction successful: %d characters", char_count)

        # Save extracted text to file
        output_file = OUTPUTS_DIR / f"{source_id}.txt"
        output_file.write_text(extracted_text, encoding="utf-8")
        logger.info("Saved extracted text to: %s", output_file)

        # Save to MongoDB
        insert_result = save_to_mongodb.invoke({
            "text": extracted_text,
            "source": url,
        })
        logger.info("MongoDB: %s", insert_result)

        result["status"] = "success"
        result["chars"] = str(char_count)
        result["mongodb_id"] = insert_result
        result["output_file"] = str(output_file)

    except Exception as exc:
        error_message = f"{type(exc).__name__}: {exc}"
        logger.error("FAILED: %s", error_message)
        logger.debug(traceback.format_exc())
        result["status"] = "failed"
        result["error"] = error_message

    logger.info("Source run finished: %s", result["status"])
    logger.info("=" * 70)

    return result


def print_summary(results: list[dict[str, str]]) -> None:
    """Print a formatted summary table of all source runs."""
    print("\n" + "=" * 100)
    print("TEST RUN SUMMARY")
    print("=" * 100)
    print(
        f"{'Source ID':<30} {'Modality':<12} {'Status':<10} "
        f"{'Chars':<10} {'MongoDB ID':<30} {'Log File':<30}"
    )
    print("-" * 100)

    for result in results:
        print(
            f"{result['source_id']:<30} "
            f"{result['modality']:<12} "
            f"{result['status']:<10} "
            f"{result['chars']:<10} "
            f"{result['mongodb_id']:<30} "
            f"{Path(result['log_file']).name:<30}"
        )
        if result["error"]:
            print(f"  ERROR: {result['error']}")

    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")
    skipped_count = sum(1 for r in results if r["status"] == "skipped")

    print("-" * 100)
    print(f"Total: {len(results)} | Success: {success_count} | Failed: {failed_count} | Skipped: {skipped_count}")
    print("=" * 100)


def main() -> int:
    print(f"Starting no-LLM source test run at {datetime.now(timezone.utc).isoformat()}")
    print(f"Reading sources from: {SOURCE_CSV}\n")

    if not SOURCE_CSV.exists():
        print(f"ERROR: Source CSV not found at {SOURCE_CSV}", file=sys.stderr)
        return 1

    # Pre-flight MongoDB check so we fail fast with a clear message.
    try:
        test_mongodb()
        print("MongoDB connection: OK\n")
    except Exception as exc:
        print(f"ERROR: Cannot connect to MongoDB: {exc}", file=sys.stderr)
        print("Please start MongoDB and rerun. See test/README.md for instructions.", file=sys.stderr)
        return 1

    sources = load_sources(SOURCE_CSV)
    if not sources:
        print("ERROR: No sources found in CSV.", file=sys.stderr)
        return 1

    print(f"Loaded {len(sources)} source(s).\n")

    results = []
    for source in sources:
        result = test_source(source)
        results.append(result)

    print_summary(results)

    # Also save summary to a file
    summary_file = TEST_DIR / "summary.txt"
    lines = [
        f"Test run at {datetime.now(timezone.utc).isoformat()}\n",
        f"Total sources: {len(results)}\n",
    ]
    for result in results:
        lines.append(
            f"{result['source_id']} | {result['modality']} | {result['status']} | "
            f"chars={result['chars']} | mongodb={result['mongodb_id']} | error={result['error']}\n"
        )
    summary_file.write_text("".join(lines), encoding="utf-8")
    print(f"\nSummary written to: {summary_file}")

    return 0 if all(r["status"] == "success" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
