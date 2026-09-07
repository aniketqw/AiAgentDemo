"""ReAct agent: Ollama LLM + tool selection.

The agent does NOT contain scraping, parsing, or database logic.
Its only job is to decide which tool to call for a user request.

The heavy lifting lives in the tools/ package; this file just wires the LLM
to those capabilities through LangGraph's prebuilt ReAct agent.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from config import llm
from tools import (
    extract_and_save_hindi_pdf,
    extract_hindi_pdf,
    extract_pdf,
    save_to_mongodb,
    scrape_dynamic,
    scrape_static,
    scrape_web,
    search_mongodb,
)

# All capabilities exposed to the agent.
tools = [
    scrape_static,
    scrape_dynamic,
    scrape_web,
    extract_pdf,
    extract_hindi_pdf,
    extract_and_save_hindi_pdf,
    save_to_mongodb,
    search_mongodb,
]

SYSTEM_PROMPT = """\
You are a helpful research assistant with access to data-acquisition tools.

Your job is to choose the correct tool for each user request, observe the
result, and answer concisely.

Tool selection rules:
- scrape_static: use for normal static HTML pages where content is already
  present in the server response.
- scrape_dynamic: use for JavaScript-rendered pages that need a real browser.
- scrape_web: use when you are unsure whether the page is static or dynamic;
  it tries static first and falls back to the browser automatically.
- extract_pdf: use when the user provides an English / Latin-script / text-based
  PDF URL.
- extract_hindi_pdf: use when the user wants ONLY the raw text of a Hindi /
  Devanagari scanned PDF (for example, a UP Agriculture Department circular).
  Do not use this tool when the user also asks to save the result.
- extract_and_save_hindi_pdf: use when the user wants to extract a Hindi /
  Devanagari scanned PDF AND save/persist/store it. This single tool downloads
  the PDF, extracts Hindi text with PaddleOCR, and inserts it into MongoDB in
  one call. It returns the real MongoDB insertion message. This is the safest
  choice for Hindi PDF storage because the local LLM does not have to copy
  extracted text across two separate tool calls.
- save_to_mongodb: use when the user asks to store, save, or persist content
  that came from a web scraper or from extract_pdf (English PDFs).
- search_mongodb: use when the user asks about previously stored content.

Important:
- Call tools with the exact arguments they require.
- Never pretend you used a tool when you did not.
- Never invent extracted text, source URLs, or document IDs.
- When a tool returns a result, report that result to the user exactly.
- If a task needs multiple steps (e.g., scrape then save), make each tool call
  separately and use the returned result in the next step.
"""

agent_executor = create_react_agent(
    model=llm,
    tools=tools,
    prompt=SYSTEM_PROMPT,
    checkpointer=MemorySaver(),
)
