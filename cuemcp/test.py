#!/usr/bin/env python3
"""Test script."""
import asyncio
from pathlib import Path

from fastmcp import Client
from sqlmodel import create_engine, SQLModel

# Configuration
DB_PATH = Path.home() / "Library/Application Support/windsurf-assistant/ask-continue.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"


async def test_ask_continue():
    """Test the ask_continue tool."""
    print("🧪 Testing Ask Continue MCP Server (SQLModel version)")
    print("=" * 60)

    # Ensure the database exists
    engine = create_engine(DATABASE_URL, echo=False)
    SQLModel.metadata.create_all(engine)

    print(f"📁 Database: {DB_PATH}")
    print("\n⚠️  In another terminal, run: python vscode_simulator.py")
    print("⚠️  Then press Enter to continue the test...\n")
    input()

    # Connect to MCP server
    async with Client("server.py:mcp") as client:
        print("✅ Connected to MCP server\n")

        # List tools
        tools = await client.list_tools()
        print(f"📦 Available tools: {[t.name for t in tools.tools]}\n")

        # Call cue
        print("🔧 Calling cue tool...")
        result = await client.call_tool(
            "cue",
            {"prompt": "Testing new architecture - enter any text", "agent_id": "test-agent"}
        )

        print("\n📨 Response received:")
        for content in result.content:
            if hasattr(content, 'text'):
                print(f"  {content.text}")

    print("\n✅ Test finished")


if __name__ == "__main__":
    asyncio.run(test_ask_continue())
