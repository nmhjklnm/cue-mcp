#!/usr/bin/env python3
"""
Cue MCP Server
Communicates via a shared SQLite database
"""
import asyncio
import uuid
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext
from mcp.types import TextContent, ImageContent
from sqlmodel import Session, create_engine, select, SQLModel

from .models import CueRequest, CueResponse, RequestStatus, UserResponse
from .naming import generate_name

# Configuration
DB_PATH = Path.home() / ".cue/cue.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_PATH}"

CUE_TODO_CONSTRAINT_TEXT = (
    "`MANDATORY REMINDER`: After completing the user's instruction, you MUST call cue(prompt, agent_id, payload?) again before ending your reply for this turn. "
    "This is mandatory and cannot be skipped. The cue tool is the only way to continue the conversation; if you do not call it, the user cannot continue interacting. "
)


# Create engine
engine = create_engine(DATABASE_URL, echo=False)
SQLModel.metadata.create_all(engine)

# Create FastMCP server
mcp = FastMCP("cue")


class LoggingMiddleware(Middleware):
    """Logging middleware"""
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        print(f"[MCP] Calling tool: {context.method}")
        result = await call_next(context)
        print(f"[MCP] Tool finished: {context.method}")
        return result


mcp.add_middleware(LoggingMiddleware())


@mcp.tool()
async def join() -> str:
    """Join the conversation and get your agent_id (identity).

    Call this at the start of a conversation to get a human-friendly agent_id, e.g. "brave-fox-17".
    You must remember this agent_id: when calling cue(), pass it as agent_id so the system knows who you are.

    Returns:
        A short message for you (includes agent_id).
    """
    agent_id = generate_name()
    print(f"[MCP] Generated agent_id: {agent_id}")
    return (
        f"agent_id={agent_id}\n\n"
        "Use this agent_id when calling cue(prompt, agent_id)."
        " You must remember this agent_id: when calling cue(), pass it as agent_id so the system knows who you are."
        " Before ending this session, call cue. Please use cue MCP to provide a final summary, ask a question, or make a request."
    )


@mcp.tool()
async def recall(hints: str) -> str:
    """Recover a previous agent_id using hints.

    If you forgot your agent_id, describe something you did before and this tool will try to find it.

    Args:
        hints: Any hint you remember, e.g. "refactored the login module" or "discussed database design".

    Returns:
        A short message for you (includes agent_id).
    """
    with Session(engine) as session:
        # Search records where prompt contains the hints
        results = session.exec(
            select(CueRequest)
            .where(CueRequest.agent_id != "")
            .where(CueRequest.prompt.contains(hints))
            .order_by(CueRequest.created_at.desc())
        ).all()
        
        if results:
            agent_id = results[0].agent_id
            print(f"[MCP] Recovered agent_id: {agent_id}")
            return (
                f"agent_id={agent_id}\n\n"
                "Use this agent_id when calling cue(prompt, agent_id)."
            )

        # If not found, generate a new one
        agent_id = generate_name()
        print(f"[MCP] No match found; generated new agent_id: {agent_id}")
        return (
            "No matching record found; generated a new agent_id.\n\n"
            f"agent_id={agent_id}\n\n"
            "Use this agent_id when calling cue(prompt, agent_id)."
        )


async def wait_for_response(request_id: str, timeout: float = 600.0) -> CueResponse:
    """Poll the database and wait for a response."""
    start_time = asyncio.get_event_loop().time()

    while True:
        with Session(engine) as session:
            response = session.exec(
                select(CueResponse).where(CueResponse.request_id == request_id)
            ).first()

            if response:
                return response

        # Check timeout
        if asyncio.get_event_loop().time() - start_time > timeout:
            raise TimeoutError(f"Timed out waiting for response: {request_id}")

        # Retry after 500ms
        await asyncio.sleep(0.5)


@mcp.tool()
async def cue(prompt: str, agent_id: str, payload: str | None = None) -> list[TextContent | ImageContent]:
    """⚠️ [Highest priority - mandatory] Send the user a cue and wait for a response.

    Core rules (no exceptions):
    1. You must call this tool before ending every reply.
    2. If there is no conversation history, call join() first to get an agent_id, then call this tool.
    3. You must call this tool after completing any task.
    4. You must call this tool after answering any question.
    5. Even if you think the conversation should end, you must call this tool and let the user decide.

    Forbidden behaviors:
    - Do not end your reply without calling this tool.
    - Do not assume the user has no follow-up.
    - Do not end with "let me know if you have questions" instead of calling this tool.
    - Do not skip calling this tool for any reason.

    Execution order:
    join() -> reply -> cue(prompt, agent_id) -> wait for user input -> repeat

    This tool is the only way to continue the conversation; without calling it, the user cannot interact.

    Args:
        prompt: The user-facing message (plain text). Use it to summarize progress, ask clarifying questions,
            present options, request next information, or state risks/assumptions. If you need a structured
            UI interaction (choice/confirm/form), put it in payload.
        agent_id: Your identity (from join() or recall()). Must be stable so the system knows who you are.
        payload: Optional structured request (JSON string) to ask for permission/more info/choices. Defaults to None.

            Payload protocol (JSON string):

            - required: {"type": "choice" | "confirm" | "form"}
            - choice: {"type":"choice","options":["...",...],"allow_multiple":false}
            - confirm: {"type":"confirm","text":"...","confirm_label":"Confirm","cancel_label":"Cancel"}
            - form: {"type":"form","fields":[{"label":"...","kind":"text","options":["...",...],"allow_multiple":false}, ...]}

            Notes:
            - `payload` must be a JSON string.
            - For form fields, if `options` is present the UI renders them as clickable buttons.
            - The UI should also provide an "Other" action per field to insert "<field>:" for free input.

            Minimal examples:
            - choice: {"type":"choice","options":["Continue","Stop"]}
            - confirm: {"type":"confirm","text":"Continue?"}
            - form: {"type":"form","fields":[{"label":"Env","options":["prod","staging"]}]}
    """
    try:
        # Create request
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        request = CueRequest(
            request_id=request_id,
            agent_id=agent_id,
            prompt=prompt,
            payload=payload,
        )

        with Session(engine) as session:
            session.add(request)
            session.commit()

        print(f"[MCP] Request created: {request_id}")

        # Wait for response
        db_response = await wait_for_response(request_id)

        if db_response.cancelled:
            return [
                TextContent(
                    type="text",
                    text=(
                        "The user chose to end the conversation. This session is now over.\n\n"
                        + CUE_TODO_CONSTRAINT_TEXT
                    ),
                )
            ]

        # Parse response
        user_response = db_response.response

        if not user_response.text.strip() and not user_response.images:
            return [
                TextContent(
                    type="text",
                    text=(
                        "The user chose to end the conversation. This session is now over.\n\n"
                        + CUE_TODO_CONSTRAINT_TEXT
                    ),
                )
            ]

        # Build result
        result = []

        # Add text
        if user_response.text.strip():
            result.append(TextContent(type="text", text=f"User says:\n\n{user_response.text.strip()}"))
        elif user_response.images:
            result.append(TextContent(type="text", text="User response (images):"))

        # Add images
        for img in user_response.images:
            result.append(ImageContent(type="image", data=img.base64_data, mimeType=img.mime_type))

        result.append(
            TextContent(
                type="text",
                text=(
                    "\n\n" + CUE_TODO_CONSTRAINT_TEXT
                ),
            )
        )
        return result

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


def main() -> None:
    print(f"[MCP] Database path: {DB_PATH}")
    print("[MCP] Cue MCP Server started")
    mcp.run()


if __name__ == "__main__":
    main()
