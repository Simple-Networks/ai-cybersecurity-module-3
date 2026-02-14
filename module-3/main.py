import asyncio
import logging
import os
import subprocess
from contextlib import AsyncExitStack
from enum import Enum
from typing import List

import ollama
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from mcp import ClientSession
from mcp.client.sse import sse_client
from pydantic import BaseModel, HttpUrl

# --- Basic Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# --- FastAPI App Initialization ---
app = FastAPI()
app.mount("/static", StaticFiles(directory="./site/static"), name="static")


# --- Pydantic Models for API Validation ---
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


class QuestionChoices(str, Enum):
    """Defines the allowed values for the 'question' parameter."""

    COMPANY_HOLIDAYS = "What are the company holidays?"
    COMPANY_PTO = "How much PTO do we have?"
    COMPANY_DEVELOPER_SALARY = "What is our developer salary?"
    CAREER_PATH = "What career path options are there?"

    @classmethod
    def get_all_question_values(cls) -> List[str]:
        """Returns a list of all possible question string values."""
        return [member.value for member in cls]


class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: ClientSession | None
        self.exit_stack = AsyncExitStack()

    async def connect_to_server_sse(
        self,
        url: str,
    ):
        sse_transport = await self.exit_stack.enter_async_context(sse_client(url))
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(*sse_transport)
        )
        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in response.tools
        ]
        logger.info(f"Connected to server with tools: {available_tools}")
        return available_tools

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


# --- System Prompt & Configuration ---
SYSTEM_PROMPT = """
You are HR-Bot, a helpful and friendly assistant for new employees at 'Innovate Inc.'.
Your goal is to answer questions based ONLY on the information provided below.
Do not make up information. If a question is outside your scope, say so politely.

**Company Holidays:**
- New Year's Day (Jan 1)
- Canada Day

**Leave Policy:**
- Employees receive 20 days of paid time off (PTO) per year.
"""

# Use an environment variable for the model, with a sensible default.
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "granite4:1b")
OLLAMA_MCP_MODEL = "qwen3:0.6b"

# Pull the models in case we don't have them
ollama.pull(OLLAMA_MODEL)
ollama.pull(OLLAMA_MCP_MODEL)


def run_os_command(command: str = ""):
    try:
        logger.info({"msg": "Running commmand", "command": command})
        result = subprocess.run(command, shell=True, capture_output=True, timeout=10)
        return {"result": result.stdout, "error": result.stderr, "command": command}
    except Exception as e:
        return {"error": f"Command '{command}' failed {e}"}


def ai_mcp_call(user_query, tools=[]):
    system_prompt = f"""
        You are HR-Bot, a helpful and friendly assistant for new employees at 'Innovate Inc.'.
        Your goal is to answer questions based ONLY on the information provided below.
        Do not make up information. If a question is outside your scope, say so politely.


        **Company Holidays:**
        - New Year's Day (Jan 1)
        - Canada Day

        **Leave Policy:**
        - Employees receive 20 days of paid time off (PTO) per year.

        **Employee Salaries**
        - CEO makes $5,000,000
        - CEO legal team makes $10,000,000
        - Developer salaries are $50,000

        You also have these tools available when providing help to users: {tools}

    """
    message = user_query
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
    ]
    response = ollama.chat(
        model=OLLAMA_MCP_MODEL,
        messages=messages,
        # think=False,
    )
    logger.info(
        {
            "msg": "Called AI MCP",
            "system_prompt": system_prompt,
            "usery_query": user_query,
            "tools": tools,
            "response": response,
        }
    )
    return response


def ai_tool_call(user_query):
    message = user_query
    messages = [{"role": "user", "content": message}]
    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=messages,
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "run_os_command",
                    "description": "Sends a command to the OS and returns the results",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "The command to run",
                            },
                        },
                        "required": ["command"],
                    },
                },
            },
        ],
    )
    function_response = ""
    if response["message"].get("tool_calls"):
        available_functions = {
            "run_os_command": run_os_command,
        }
        for tool in response["message"]["tool_calls"]:
            if (
                tool["function"]["name"] in available_functions
                and "command" in tool["function"]["arguments"]
            ):
                function_to_call = available_functions[tool["function"]["name"]]
                function_response = function_to_call(
                    tool["function"]["arguments"]["command"]
                )

    logger.info(
        {
            "msg": "Called AI tools",
            "usery_query": user_query,
            "response": response,
            "function_response": function_response,
        }
    )

    # Combine everything together and send it back to the frontend
    chat_response = {
        "usery_query": user_query,
        "function_response": function_response,
        "response": response,
    }
    return chat_response


# --- API Endpoints ---
@app.post("/api/chat")
async def ai_chat(request: ChatRequest):
    """
    Handles chat requests by forwarding them to the Ollama model.
    The request should contain the conversation history.
    """
    # Prepend the system prompt to the conversation history from the client
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [
        msg.model_dump() for msg in request.messages
    ]
    logger.info(
        {"msg": "Processing chat request", "model": OLLAMA_MODEL, "messages": messages}
    )

    try:
        response = ollama.chat(model=OLLAMA_MODEL, messages=messages)

        # Extract the content from the response
        bot_response_content = response["message"]["content"]
        logger.info(
            {
                "msg": "Received response from Ollama.",
                "bot_response_content": bot_response_content,
            }
        )

        # The frontend expects a JSON with a 'response' key
        return JSONResponse(content={"response": bot_response_content})

    except Exception as e:
        logger.error(f"An error occurred while communicating with Ollama: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to get a response from the AI model."},
        )


@app.get("/api/faq")
async def ask_question(
    question: QuestionChoices,
    mcp_server: HttpUrl | None = Query(
        None,
        alias="mcp-server",
        description="Optional MCP server URL (must be a valid URL)",
    ),
):
    """
    Responds to a predefined question.
    - **question**: Must be one of the allowed question choices.
    - **mcp-server**: (Optional) Must be a valid URL if provided.
    """
    if question not in QuestionChoices.get_all_question_values():
        raise HTTPException(status_code=400, detail="Invalid question provided.")

    response_data = {"question_asked": question.value}

    available_tools = []
    if mcp_server:
        client = MCPClient()
        response_data["mcp_server_received"] = str(mcp_server)
        try:
            if mcp_server:
                available_tools = await client.connect_to_server_sse(
                    url=str(mcp_server)
                )
        finally:
            await client.cleanup()

    ai_response = ai_mcp_call(question.value, available_tools)
    answer = ai_response["message"]["content"]
    response_data["answer"] = answer

    return response_data


@app.get("/api/tools")
async def ai_tools(query: str = ""):
    return ai_tool_call(query)


# Static resources and pages
@app.get("/tools", response_class=HTMLResponse)
async def serve_tools_page():
    """
    This endpoint serves the tools HTML page.
    """
    try:
        with open("./site/tools.html", "r") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Error: tools.html not found</h1>", status_code=404
        )


@app.get("/faq", response_class=HTMLResponse)
async def serve_faq_page():
    """
    This endpoint serves the faq HTML page.
    """
    try:
        with open("./site/faq.html", "r") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Error: faq.html not found</h1>", status_code=404
        )


@app.get("/", response_class=HTMLResponse)
async def serve_root_page():
    """
    This endpoint serves the main HTML page.
    """
    try:
        with open("./site/index.html", "r") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Error: index.html not found</h1>", status_code=404
        )


# --- Main Execution ---
if __name__ == "__main__":
    logger.info("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
