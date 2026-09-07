# Test Suite for Agriculture Sources

This folder tests every source from the original `sources.csv` in **no-LLM mode**.
That means each capability is called directly — no agent, no reasoning layer — so
we can verify that scraping, browser rendering, PDF extraction, and MongoDB
persistence all work on real agriculture URLs.

## What the test produces

Running `python test/test_sources.py` creates:

```text
test/
├── logs/
│   ├── upag_market_intelligence.log
│   ├── iipr_varieties.log
│   ├── iipr_new_varieties.log
│   ├── iipr_technologies.log
│   ├── up_agri_seed_rates.log
│   └── gda_rapeseed_2024.log
├── outputs/
│   ├── upag_market_intelligence.txt
│   ├── iipr_varieties.txt
│   ├── iipr_new_varieties.txt
│   ├── iipr_technologies.txt
│   ├── up_agri_seed_rates.txt          # now extracted with PaddleOCR
│   └── gda_rapeseed_2024.txt
├── summary.txt
└── README.md          # this file
```

| Artifact | Purpose |
|---|---|
| `logs/<source_id>.log` | Full terminal output for that source, including tool invocation, character count, file save path, and MongoDB insertion result. |
| `outputs/<source_id>.txt` | Final extracted text returned by the tool. |
| `summary.txt` | One-line status for every source after the run. |
| MongoDB `documents` collection | One document per source, stored as `{source: <url>, text: <extracted_text>}`. |

## How to run

### 1. Start MongoDB

If MongoDB is not running, the test will fail immediately with a clear message.

**macOS with Homebrew:**

```bash
brew tap mongodb/brew
brew install mongodb-community@7.0
brew services start mongodb-community@7.0
```

**Verify it is running:**

```bash
mongosh --eval "db.adminCommand('ping')"
```

### 2. Run the test runner

```bash
cd /Users/aniketsaxena/Documents/p/from_aug_1/p0/dailyPrep/7sep/AiAgentDemo
python test/test_sources.py
```

### 3. Inspect results

Check the summary:

```bash
cat test/summary.txt
```

Look at a specific log:

```bash
cat test/logs/iipr_varieties.log
```

Look at extracted text:

```bash
cat test/outputs/iipr_varieties.txt
```

Query MongoDB:

```bash
mongosh agent_demo --eval 'db.documents.find({source: "https://www.icar-iipr.org.in/varity/"}, {_id: 1, source: 1})'
```

## Source mapping

| Source ID | Modality | Tool used |
|---|---|---|
| `upag_market_intelligence` | `dynamic_web` | `scrape_dynamic` (Playwright) |
| `iipr_varieties` | `web` | `scrape_web` (smart static fallback) |
| `iipr_new_varieties` | `web` | `scrape_web` (smart static fallback) |
| `iipr_technologies` | `web` | `scrape_web` (smart static fallback) |
| `up_agri_seed_rates` | `pdf` (overridden) | `extract_hindi_pdf` (PaddleOCR `lang='hi'`) |
| `gda_rapeseed_2024` | `web_doc` | `scrape_web` (smart static fallback) |

## MongoDB Compass: what to screenshot

Open **MongoDB Compass** (or any MongoDB GUI). Use these steps to capture
exactly what the test saved.

### Screenshot 1 — Connection screen

1. Open MongoDB Compass.
2. Create or select the connection: `mongodb://localhost:27017`.
3. Click **Connect**.
4. ![alt text](images/image.png)

### Screenshot 2 — Database + collection list

1. In the left sidebar, click on **`agent_demo`** database.
2. You should see the `documents` collection.
3. ![alt text](images/image-1.png)

### Screenshot 3 — Documents list view

1. Click on the **`documents`** collection.
2. Make sure the **Documents** tab is selected (not Aggregations / Schema).
3. ![alt text](images/image2.png) Each row shows:
   - `_id`
   - `source` (the URL)
   - `text` (preview, truncated)


### Screenshot 4 — Filtered view for one source

1. In the filter bar at the top, type:
   ```json
   {"source": "https://www.icar-iipr.org.in/varity/"}
   ```
2. Press Enter or click **Find**.
   ![alt text](images/image3.png)


## Note on the UP Agriculture seed-rates PDF

The `up_agri_seed_rates` source is a scanned **Hindi / Devanagari** PDF. The
base `extract_pdf` tool uses Tesseract with default Latin models, which produces
gibberish on Devanagari glyphs.

For this specific source, use the Hindi-aware tool instead:

```bash
python demo.py hindi_pdf https://agridarshan.up.gov.in/api/v2/downloadPublic/0a7396d2-8cea-4112-9d4f-9cf9e7bd634d
```

Output is written to:

- `test/outputs/up_agri_seed_rates.txt` — automated OCR + heuristic formatting
- `test/outputs/up_agri_seed_rates_reference.txt` — manually corrected transcript
  from the scanned image, for comparison only (not produced by the pipeline)

Or run the single agent, which includes the combined `extract_and_save_hindi_pdf`
pipeline and will extract and persist the Hindi PDF in one tool call (more
reliable with a local LLM):

```bash
python demo.py agent "Extract this Hindi UP Agriculture PDF and save it to MongoDB: https://agridarshan.up.gov.in/api/v2/downloadPublic/0a7396d2-8cea-4112-9d4f-9cf9e7bd634d"
```

Agent run is logged in:

- `logs/run_all_console.txt` (when using `run_all.py`)

The final MongoDB state after the test suite + agent is logged in:

- `logs/final_mongo_run_all.txt`

### What the saved file looks like

PaddleOCR returns the text, but scanned government PDFs still contain OCR noise:
Devanagari words may be run together, Latin characters can replace Hindi glyphs
(e.g. `Plofah` instead of `प्रदाय`), and prices can be mis-recognized. The
default `"heuristic"` formatting mode improves readability by rebuilding
paragraphs and attempting a Markdown table, but it does **not** change any
words or numbers, so the file remains a faithful (if noisy) extraction.

To switch modes programmatically:

```python
from tools.hindi_pdf_extractor.core import hindi_pdf_extractor

# default: safe reformatting, no content changes
text = hindi_pdf_extractor(url, format_mode="heuristic")

# raw OCR lines for debugging recognition
text = hindi_pdf_extractor(url, format_mode="raw")

# local LLM cleanup: more readable, but may invent rows/prices
text = hindi_pdf_extractor(url, format_mode="llm")
```

For a production knowledge base you would either use a stronger OCR model or
review the scanned page manually.

PaddleOCR downloads the Hindi model on first run, so the first execution may
take a minute or two.

## Expected final state

After a successful run of `test/test_sources.py`:

- 6 `.log` files in `test/logs/`
- 6 `.txt` files in `test/outputs/`
- 6 documents in MongoDB `agent_demo.documents`
- `test/summary.txt` shows all sources as `success`

If you also run the agent (`demo.py agent ...`) on the UP Agriculture PDF,
a 7th document is inserted for the same source.

## Troubleshooting

### MongoDB connection refused

```text
ERROR: Cannot connect to MongoDB: localhost:27017: [Errno 61] Connection refused
```

Fix: start MongoDB.

```bash
brew services start mongodb-community@7.0
```

If you do not have it installed:

```bash
brew tap mongodb/brew
brew install mongodb-community@7.0
brew services start mongodb-community@7.0
```

### Playwright browser missing

```text
Playwright is required for dynamic-web scraping.
```

Fix:

```bash
playwright install chromium
```

