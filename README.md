# Student LangChain + Ollama Agent Demo

A deliberately small, step-by-step reproduction of the acquisition capabilities
from the larger UP Agriculture knowledge-base pipeline, built with **LangChain**,
**Ollama**, and **MongoDB**.

The original pipeline has 10 demos covering chunking, structured extraction,
validation, and async batching. This project keeps only the first, most
educational layer:

```text
User
  ↓
LangChain ReAct Agent + Ollama
  ↓
┌──────────────┬──────────────┬──────────────┐
│ static       │ dynamic      │ PDF          │
│ scraper      │ scraper      │ extractor    │
│ (requests+BS)│ (Playwright) │ (pypdf→OCR)  │
└──────────────┴──────────────┴──────────────┘
  ↓
MongoDB tools (save / search)
```

## What this teaches

- **Capabilities are plain Python functions.** Every scraper, extractor, and
  MongoDB helper lives in a `tools/<capability>/core.py` file and works without
  any LLM.
- **LangChain `@tool` only adds intent.** Each `tools/<capability>/tool.py`
  file wraps the plain function and tells the agent *when* to use it.
- **The agent is a decision layer.** It does not scrape, parse, or store data.
  It only chooses which tool to call.

## Prerequisites

- Python 3.10+
- MongoDB running locally (or update `MONGODB_URI`)
- Ollama running locally with a model pulled, e.g.:
  ```bash
  ollama pull llama3.1
  ```

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Install Chromium for Playwright
playwright install chromium

# Copy environment template and edit if needed
cp .env.example .env
```

The default `.env` assumes local services:

```env
OLLAMA_MODEL=llama3.1
OLLAMA_BASE_URL=http://localhost:11434
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=agent_demo
MONGODB_COLLECTION=documents
```

### Install and start MongoDB (macOS with Homebrew)

If MongoDB is not installed:

```bash
brew tap mongodb/brew
brew trust mongodb/brew
brew install mongodb-community@7.0
```

Start MongoDB and verify:

```bash
brew services start mongodb/brew/mongodb-community@7.0
mongosh --eval "db.adminCommand('ping')"
```

You should see `{ ok: 1 }`.

## Project layout

```text
.
├── .env                 # local service configuration
├── .env.example         # template
├── requirements.txt     # Python dependencies
├── config.py            # shared Ollama + MongoDB clients
├── agent.py             # ReAct agent assembly
├── demo.py              # CLI to test every layer standalone
├── tools/               # one subpackage per capability
│   ├── __init__.py      # re-exports all @tool wrappers
│   ├── static_scraper/
│   │   ├── core.py      # requests + BeautifulSoup logic
│   │   └── tool.py      # scrape_static @tool wrapper
│   ├── dynamic_scraper/
│   │   ├── core.py      # Playwright/Chromium logic
│   │   └── tool.py      # scrape_dynamic @tool wrapper
│   ├── pdf_extractor/
│   │   ├── core.py      # pypdf → pymupdf → OCR logic
│   │   └── tool.py      # extract_pdf @tool wrapper
│   ├── mongodb/
│   │   ├── core.py      # pymongo insert/find logic
│   │   └── tool.py      # save_to_mongodb / search_mongodb
│   └── smart_scraper/
│       ├── core.py      # static-then-Playwright fallback logic
│       └── tool.py      # scrape_web @tool wrapper
└── test/                # no-LLM agriculture source test suite
    ├── test_sources.py  # runner for every source in sources.csv
    ├── README.md        # setup + MongoDB screenshot guide
    ├── logs/            # per-source terminal output
    ├── outputs/         # per-source extracted text
    └── summary.txt      # final status table after each run
```

## Tool name reference

Each capability has a **core function** (plain Python) and a **tool name** (what the agent and demo CLI use).

| Capability | Folder | Core function | Tool name | CLI command |
|---|---|---|---|---|
| Static web scraper | `tools/static_scraper/` | `static_scraper()` | `scrape_static` | `python demo.py static <url>` |
| Dynamic / Playwright scraper | `tools/dynamic_scraper/` | `playwright_scraper()` | `scrape_dynamic` | `python demo.py playwright <url>` |
| Smart scraper with fallback | `tools/smart_scraper/` | `scrape_with_fallback()` | `scrape_web` | `python demo.py web <url>` |
| PDF extractor | `tools/pdf_extractor/` | `pdf_extractor()` | `extract_pdf` | `python demo.py pdf <url>` |
| MongoDB save | `tools/mongodb/` | `mongo_insert()` | `save_to_mongodb` | `python demo.py save "<text>" "<source>"` |
| MongoDB search | `tools/mongodb/` | `mongo_find()` | `search_mongodb` | `python demo.py mongo [source_filter]` |

## How the tools package is organized

Every capability follows the same two-file pattern:

```text
tools/<capability>/
├── core.py   ← plain Python function (testable without LangChain)
└── tool.py   ← @tool wrapper that exposes it to the agent
```

This separation makes it obvious what the LLM actually adds: **nothing except
a decision about which core function to call.**

Import examples:

```python
# From the package level (used by agent.py and demo.py)
from tools import scrape_static, scrape_dynamic, extract_pdf, save_to_mongodb, search_mongodb

# From a specific capability core (used for unit testing)
from tools.static_scraper.core import static_scraper
from tools.mongodb.core import mongo_find
```

## Run standalone capability tests

These commands test each tool **without the LLM**, which is the best way to
debug one layer at a time. Use the table above to map a task to the right tool.

### 1. Static scraper (`scrape_static`)

Use this for normal HTML pages where the content is already in the server response.

```bash
python demo.py static https://example.com
```

Uses `requests` + `BeautifulSoup`. Strips scripts, styles, nav, footer, etc.

### 2. Dynamic / Playwright scraper (`scrape_dynamic`)

Use this for JavaScript-rendered pages that need a real browser.

```bash
python demo.py playwright https://example.com
```

Launches headless Chromium, waits for JavaScript rendering, then extracts
visible text.

### 3. Smart scraper (`scrape_web`)

Use this when you are unsure whether a page is static or dynamic.

```bash
python demo.py web https://example.com
```

Tries a fast static fetch first; falls back to Playwright only if the result
looks like an empty JavaScript shell.

### 4. PDF extractor (`extract_pdf`)

Use this for PDF URLs.

```bash
python demo.py pdf https://example.com/sample.pdf
```

Tries `pypdf`, then `pymupdf`, then OCR via `pytesseract`.

### 5. MongoDB save / search (`save_to_mongodb` / `search_mongodb`)

```bash
# Save directly
python demo.py save "Some extracted text" "https://example.com"

# List stored documents
python demo.py mongo

# Filter by source
python demo.py mongo https://example.com
```

## Run the full ReAct agent

```bash
python demo.py agent "Scrape https://example.com and store the result in MongoDB"
```

You should see the agent reason step by step:

1. Decide to call `scrape_static`.
2. Receive the cleaned text.
3. Decide to call `save_to_mongodb`.
4. Return a final answer.

Other examples:

```bash
python demo.py agent "What PDFs have I stored?"
python demo.py agent "Extract text from https://example.com/file.pdf"
python demo.py agent "Use Playwright to inspect https://example.com"
```

## Run the agriculture source test suite

The `test/` folder contains a no-LLM runner that tests every source from the
original `sources.csv` and saves results.

```bash
python test/test_sources.py
```

This produces:

- `test/logs/<source_id>.log` — full terminal output per source
- `test/outputs/<source_id>.txt` — extracted text per source
- `test/summary.txt` — final status table
- one MongoDB document per source in `agent_demo.documents`

The source CSV is loaded from the original repo path:

```text
/Users/aniketsaxena/Documents/p/from_aug_1/p0/dailyPrep/5sep/sources.csv
```

See `test/README.md` for full setup, troubleshooting, and **MongoDB Compass
screenshot directions**.

## Architecture

```text
                    ┌──────────────────────┐
                    │       User           │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ LangChain ReAct      │
                    │ Agent + Ollama       │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
       scrape_static   scrape_dynamic   extract_pdf
       (requests+BS)   (Playwright)     (pypdf→OCR)
              │                │                │
              └────────────────┼────────────────┘
                               │
                               ▼
              ┌──────────────────────────────────┐
              │      save_to_mongodb             │
              │      search_mongodb              │
              └────────────────┬─────────────────┘
                               │
                               ▼
                            MongoDB
```


