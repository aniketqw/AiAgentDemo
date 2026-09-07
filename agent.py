"""ReAct agent: Ollama LLM + tool selection.

The agent does NOT contain scraping, parsing, or database logic.
Its only job is to decide which tool to call for a user request.

The heavy lifting lives in the tools/ package; this file just wires the LLM
to those capabilities through LangChain's tool-calling agent framework.
"""

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from config import llm
from tools import (
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
- extract_pdf: use when the user provides a PDF URL.
- save_to_mongodb: use when the user asks to store, save, or persist content.
- search_mongodb: use when the user asks about previously stored content.

Important:
- Call tools with the exact arguments they require.
- Never pretend you used a tool when you did not.
- If a task needs multiple steps (e.g., scrape then save), make each tool call
  separately and use the returned result in the next step.
"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
