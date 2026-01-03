#!/usr/bin/env python3
"""测试脚本"""
import asyncio
from pathlib import Path

from fastmcp import Client
from sqlmodel import create_engine, SQLModel

# 配置
DB_PATH = Path.home() / "Library/Application Support/windsurf-assistant/ask-continue.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"


async def test_ask_continue():
    """测试 ask_continue 工具"""
    print("🧪 测试 Ask Continue MCP Server (SQLModel 版本)")
    print("=" * 60)

    # 确保数据库存在
    engine = create_engine(DATABASE_URL, echo=False)
    SQLModel.metadata.create_all(engine)

    print(f"📁 数据库: {DB_PATH}")
    print("\n⚠️  请在另一个终端运行: python vscode_simulator.py")
    print("⚠️  然后按回车继续测试...\n")
    input()

    # 连接到 MCP server
    async with Client("server.py:mcp") as client:
        print("✅ 已连接到 MCP server\n")

        # 列出工具
        tools = await client.list_tools()
        print(f"📦 可用工具: {[t.name for t in tools.tools]}\n")

        # 调用 cue
        print("🔧 调用 cue 工具...")
        result = await client.call_tool(
            "cue",
            {"prompt": "测试新架构 - 请输入任意内容", "agent_id": "test-agent"}
        )

        print("\n📨 收到响应:")
        for content in result.content:
            if hasattr(content, 'text'):
                print(f"  {content.text}")

    print("\n✅ 测试完成")


if __name__ == "__main__":
    asyncio.run(test_ask_continue())
