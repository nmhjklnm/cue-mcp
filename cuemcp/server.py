#!/usr/bin/env python3
"""
Cue MCP Server
Communicates via a shared SQLite database
"""
import asyncio
import uuid
from pathlib import Path
from datetime import datetime

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
    "重要：【Human Agent Protocol 强制遵循】你必须遵循Human Agent Protocol协议：在每次完成我的指令之前或回答问题时，必须向我 cue（即调用 cue(prompt, agent_id, payload?) 让我继续输入）。未实际调用 cue之前，不得结束回复；\n\n"
    "重要：【todo_list 强制检查】开始执行此条用户指令前，请检查当前 todo_list，并确保最后一条任务为'用 cue发送{{用户这条指令所对应的可能的响应}}'。 若不存在，必须立即补充添加。"
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

    Call this at the start of a conversation to get a human-friendly agent_id, e.g. "tavilron".
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
        if timeout is not None and asyncio.get_event_loop().time() - start_time > timeout:
            raise TimeoutError(f"Timed out waiting for response: {request_id}")

        # Retry after 500ms
        await asyncio.sleep(0.5)


def _build_tool_result_from_user_response(user_response: UserResponse) -> list[TextContent | ImageContent]:
    result: list[TextContent | ImageContent] = []

    # Add text
    if user_response.text.strip():
        result.append(
            TextContent(
                type="text",
                text=f"用户希望继续，并提供了以下指令：\n\n{user_response.text.strip()}",
            )
        )
    elif user_response.images:
        result.append(TextContent(type="text", text="用户希望继续，并附加了图片："))

    # Add images
    for img in user_response.images:
        result.append(ImageContent(type="image", data=img.base64_data, mimeType=img.mime_type))

    result.append(TextContent(type="text", text=("\n\n" + CUE_TODO_CONSTRAINT_TEXT)))
    return result


@mcp.tool()
async def pause(agent_id: str, prompt: str | None = None) -> list[TextContent]:
    """Pause the agent indefinitely until the user clicks Continue in the console.

    This tool sends a single-action *confirm* payload (no cancel button) to cue-console.

    Payload JSON format:
        {
          "type": "confirm",
          "variant": "pause",
          "text": "Paused. Click Continue when you are ready.",
          "confirm_label": "Continue",
          "cancel_label": ""
        }
    """
    pause_prompt = prompt or "Waiting for your confirmation. Click Continue when you are ready."
    payload = '{"type":"confirm","variant":"pause","text":"Paused. Click Continue when you are ready.","confirm_label":"Continue","cancel_label":""}'

    request_id = f"req_{uuid.uuid4().hex[:12]}"
    request = CueRequest(
        request_id=request_id,
        agent_id=agent_id,
        prompt=pause_prompt,
        payload=payload,
    )

    with Session(engine) as session:
        session.add(request)
        session.commit()


    db_response = await wait_for_response(request_id, timeout=None)
    if db_response.cancelled:
        return [
            TextContent(
                type="text",
                text=(
                    "The user did not continue. Call pause(agent_id) to suspend and wait for resume.\n\n"
                    + CUE_TODO_CONSTRAINT_TEXT
                ),
            )
        ]

    user_response = db_response.response
    if not user_response.text.strip() and not user_response.images:
        return [
            TextContent(
                type="text",
                text=(
                    "The user resumed the conversation.\n\n" + CUE_TODO_CONSTRAINT_TEXT
                ),
            )
        ]

    return _build_tool_result_from_user_response(user_response)


@mcp.tool()
async def cue(prompt: str, agent_id: str, payload: str | None = None) -> list[TextContent | ImageContent]:
    """
    Send the user a cue.

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
        try:
            db_response = await wait_for_response(request_id)
        except (asyncio.CancelledError, TimeoutError) as e:
            with Session(engine) as session:
                existing_response = session.exec(
                    select(CueResponse).where(CueResponse.request_id == request_id)
                ).first()
                if not existing_response:
                    response = CueResponse.create(
                        request_id=request_id,
                        response=UserResponse(text="", images=[]),
                        cancelled=True,
                    )
                    session.add(response)

                db_request = session.exec(
                    select(CueRequest).where(CueRequest.request_id == request_id)
                ).first()
                if db_request:
                    db_request.status = RequestStatus.CANCELLED
                    db_request.updated_at = datetime.now()
                    session.add(db_request)

                session.commit()

            msg = (
                "Timed out waiting for user response. Call pause(agent_id) to suspend and wait for resume.\n\n"
                if isinstance(e, TimeoutError)
                else "Tool call was cancelled. Call pause(agent_id) to suspend and wait for resume.\n\n"
            )
            return [TextContent(type="text", text=msg)]

        if db_response.cancelled:
            return [
                TextContent(
                    type="text",
                    text=(
                        "The user did not continue. Call pause(agent_id) to suspend and wait for resume.\n\n"
                    ),
                )
            ]

        # Parse response
        user_response = db_response.response

        if not user_response.text.strip() and not user_response.images:
            with Session(engine) as session:
                db_request = session.exec(
                    select(CueRequest).where(CueRequest.request_id == request_id)
                ).first()
                if db_request:
                    db_request.status = RequestStatus.COMPLETED
                    db_request.updated_at = datetime.now()
                    session.add(db_request)
                    session.commit()
            return [
                TextContent(
                    type="text",
                    text=(
                        "No user input received. Call pause(agent_id) to suspend and wait for resume.\n\n"
                        + CUE_TODO_CONSTRAINT_TEXT
                    ),
                )
            ]

        # Build result
        result = []

        # Add text
        if user_response.text.strip():
            result.append(TextContent(type="text", text=f"用户希望继续，并提供了以下指令：\n\n{user_response.text.strip()}"))
        elif user_response.images:
            result.append(TextContent(type="text", text="用户希望继续，并附加了图片："))

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
