#!/usr/bin/env python3
"""Client simulator interactive script.

Polls the database and handles user requests.
"""
import asyncio
import base64
import json
import mimetypes
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session, create_engine, select, SQLModel

from .models import CueRequest, CueResponse, ImageContent, RequestStatus, UserResponse
from .terminal_render import render_payload

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import KeyBindings

    _PROMPT_TOOLKIT_AVAILABLE = True
except Exception:
    _PROMPT_TOOLKIT_AVAILABLE = False

# Configuration
DB_PATH = Path.home() / ".cue/cue.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=False)
SQLModel.metadata.create_all(engine)


def _read_multiline_text() -> str:
    if not _PROMPT_TOOLKIT_AVAILABLE:
        print("(Tip: optionally install prompt_toolkit for multiline editing: pip install prompt_toolkit)")
        try:
            return input("> ").strip()
        except EOFError:
            return ""

    kb = KeyBindings()

    @kb.add("enter")
    def _(event):
        event.app.exit(result=event.app.current_buffer.text)

    @kb.add("c-j")
    def _(event):
        event.app.current_buffer.insert_text("\n")

    @kb.add("escape", "enter")
    def _(event):
        event.app.current_buffer.insert_text("\n")

    @kb.add("c-d")
    def _(event):
        event.app.exit(result=event.app.current_buffer.text)

    session = PromptSession(key_bindings=kb, multiline=True)
    text = session.prompt("> ")
    return (text or "").strip()


def _read_image_paths() -> list[str]:
    """Read image paths (supports drag & drop) and return a list of paths."""
    print("📎 Images (optional): enter image paths (you can drag files into the terminal), separate multiple with commas; press Enter to skip")
    try:
        raw = input("> ").strip()
    except EOFError:
        return []

    if not raw:
        return []

    parts = [p.strip().strip('"').strip("'") for p in raw.split(",")]
    return [p for p in parts if p]


def _encode_images(paths: list[str]) -> list[ImageContent]:
    images: list[ImageContent] = []
    for p in paths:
        path = Path(p).expanduser()
        if not path.exists() or not path.is_file():
            print(f"⚠️ Skipping missing file: {path}")
            continue

        mime, _ = mimetypes.guess_type(str(path))
        if not mime:
            mime = "application/octet-stream"
        if not mime.startswith("image/"):
            print(f"⚠️ Skipping non-image file ({mime}): {path}")
            continue

        try:
            data = path.read_bytes()
        except Exception as e:
            print(f"⚠️ Failed to read: {path} ({e})")
            continue

        b64 = base64.b64encode(data).decode("utf-8")
        images.append(ImageContent(mime_type=mime, base64_data=b64))
    return images


async def poll_requests():
    """Poll the database for pending requests."""
    print("🔍 Listening for requests...")
    print(f"📁 Database: {DB_PATH}\n")

    while True:
        with Session(engine) as session:
            # Find the first pending request
            request = session.exec(
                select(CueRequest)
                .where(CueRequest.status == RequestStatus.PENDING)
                .order_by(CueRequest.created_at)
            ).first()

            if request:
                # Handle request
                await handle_request(request)

        # Check every 500ms
        await asyncio.sleep(0.5)


async def handle_request(request: CueRequest):
    """Handle a single request."""
    print("=" * 60)
    print(f"📨 New request: {request.request_id}")
    print(f"📝 Prompt: {request.prompt}")
    if request.payload:
        try:
            print(render_payload(request.payload, debug=False))
        except Exception:
            print("🧩 Payload (raw):")
            print(request.payload)
    print("=" * 60)

    # Get user input
    print("\n💬 Enter your reply (Enter to submit; Ctrl+J or Alt+Enter for newline):")
    user_text = await asyncio.to_thread(_read_multiline_text)

    image_paths = await asyncio.to_thread(_read_image_paths)
    images = _encode_images(image_paths)

    # Create response object
    user_response = UserResponse(text=user_text, images=images)

    # Write response
    with Session(engine) as session:
        response = CueResponse.create(
            request_id=request.request_id,
            response=user_response,
            cancelled=(not user_text and not images)
        )
        session.add(response)

        # Update request status
        db_request = session.get(CueRequest, request.id)
        if db_request:
            db_request.status = RequestStatus.COMPLETED
            db_request.updated_at = datetime.now(timezone.utc)
            session.add(db_request)

        session.commit()

    if user_text:
        print(f"✅ Response sent: {user_text[:50]}{'...' if len(user_text) > 50 else ''}\n")
    else:
        print("✅ End signal sent\n")


async def _amain() -> None:
    """Main function."""
    print("🚀 Windsurf Ask Continue - Client Simulator")
    print("=" * 60)

    try:
        await poll_requests()
    except KeyboardInterrupt:
        print("\n\n👋 Stopped listening")


def main() -> None:
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
