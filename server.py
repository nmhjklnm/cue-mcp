#!/usr/bin/env python3
"""
Cue MCP Server
使用共享 SQLite 数据库进行通信
"""
import asyncio
import uuid
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext
from mcp.types import TextContent, ImageContent
from sqlmodel import Session, create_engine, select, SQLModel

from models import CueRequest, CueResponse, RequestStatus, UserResponse
from naming import generate_name

# 配置
DB_PATH = Path.home() / ".cue/cue.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_PATH}"

CUE_TODO_CONSTRAINT_TEXT = (
    "额外约束（为了避免遗漏）：你必须在 todo_list 末尾新增一条待办任务："
    "`使用 cue mcp 给我最终的总结或者向我提问或者请求`，在你真正调用 cue() 后再标记为 completed。"
)


# 创建引擎
engine = create_engine(DATABASE_URL, echo=False)
SQLModel.metadata.create_all(engine)

# 创建 FastMCP 服务器
mcp = FastMCP("cue")


class LoggingMiddleware(Middleware):
    """日志中间件"""
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        print(f"[MCP] 调用工具: {context.method}")
        result = await call_next(context)
        print(f"[MCP] 工具完成: {context.method}")
        return result


mcp.add_middleware(LoggingMiddleware())


@mcp.tool()
async def join() -> str:
    """加入对话，获取你的 agent_id（身份标识）。
    
    在对话开始时调用此工具，获取一个人性化的 agent_id，如 "brave-fox-17"。
    你必须记住这个 agent_id：后续调用 cue() 时需要传入它，用来告诉系统“你是谁”。
    
    Returns:
        一段给你看的说明消息（包含 agent_id）。
    """
    agent_id = generate_name()
    print(f"[MCP] 生成 agent_id: {agent_id}")
    return (
        f"你的 agent_id 是: {agent_id}\n\n"
        "请牢记这个 agent_id：后续调用 cue(prompt, agent_id) 时，agent_id 参数就是你的身份标识。\n"
        "请在当前会话结束前调用 cue，请必须使用 cue mcp 给我最终的总结或者向我提问或者请求。"
    )


@mcp.tool()
async def recall(hints: str) -> str:
    """根据线索找回之前的 agent_id。
    
    如果你忘记了自己的 agent_id，可以用此工具通过描述之前做过的事情来找回。
    
    Args:
        hints: 你记得的任何线索，如 "用户让我重构登录模块" 或 "讨论过数据库设计"
    
    Returns:
        一段给你看的说明消息（包含 agent_id）
    """
    with Session(engine) as session:
        # 搜索 prompt 字段包含 hints 关键词的记录
        results = session.exec(
            select(CueRequest)
            .where(CueRequest.agent_id != "")
            .where(CueRequest.prompt.contains(hints))
            .order_by(CueRequest.created_at.desc())
        ).all()
        
        if results:
            agent_id = results[0].agent_id
            print(f"[MCP] 找回 agent_id: {agent_id}")
            return (
                f"找到你的 agent_id: {agent_id}\n\n"
                "后续调用 cue(prompt, agent_id) 时，请填写这个 agent_id。"
            )
        
        # 找不到则生成新名字
        agent_id = generate_name()
        print(f"[MCP] 未找到匹配，生成新 agent_id: {agent_id}")
        return (
            f"未找到匹配的记录，已为你生成新的 agent_id: {agent_id}\n\n"
            "调用 cue(prompt, agent_id) 时，请填写这个 agent_id。\n"
            "请在当前会话结束前调用 cue()，请必须使用 cue mcp 给我最终的总结或者向我提问或者请求。"
        )


async def wait_for_response(request_id: str, timeout: float = 600.0) -> CueResponse:
    """轮询数据库等待响应"""
    start_time = asyncio.get_event_loop().time()

    while True:
        with Session(engine) as session:
            response = session.exec(
                select(CueResponse).where(CueResponse.request_id == request_id)
            ).first()

            if response:
                return response

        # 检查超时
        if asyncio.get_event_loop().time() - start_time > timeout:
            raise TimeoutError(f"等待响应超时: {request_id}")

        # 等待 500ms 后重试
        await asyncio.sleep(0.5)


@mcp.tool()
async def cue(prompt: str, agent_id: str, payload: str | None = None) -> list[TextContent | ImageContent]:
    """⚠️ 【最高优先级 - 强制执行】给用户一个 cue，等待响应。

    🔴 核心规则（无任何例外）：
    1. 你必须在【每次回复结束前】调用此工具
    2. 你必须在无任何对话历史时先调用 join() 获取名字，再调用此工具
    3. 你必须在【完成任何任务后】调用此工具
    4. 你必须在【回答任何问题后】调用此工具
    5. 即使你认为对话应该结束，也必须调用此工具让用户决定

    🔴 绝对禁止的行为：
    - 禁止在不调用此工具的情况下结束回复
    - 禁止假设用户没有后续需求
    - 禁止在回复末尾说"有问题请告诉我"而不调用此工具
    - 禁止以任何理由跳过调用此工具

    🔴 执行顺序：
    join() 获取 agent_id → 回复内容 → cue(prompt, agent_id) → 等待用户输入 → 重复

    此工具是对话继续的唯一方式，不调用则用户无法继续交互。

    Args:
        prompt: 给用户的回复/总结/消息正文（纯文本）。如果你需要用户做选择/确认/填写表单等，请把结构化请求放到 payload。
        agent_id: 你的身份标识（通过 join() 或 recall() 获取）。必须稳定传入，用来告诉系统“你是谁”。
        payload: 可选结构化请求（JSON 字符串）。用于向用户请求授权/更多信息/选择等。不填则为 None。

            推荐结构（JSON 对象序列化后的字符串）：

            - 必填：{"type": "choice" | "confirm" | "form"}
            - type=choice：{"type":"choice","options":[{"id":"A","label":"..."}, ...],"allow_multiple":false}
            - type=confirm：{"type":"confirm","text":"...","confirm_label":"确认","cancel_label":"取消"}
            - type=form：{"type":"form","fields":[{"id":"title","label":"标题","kind":"text"}, ...]}

            示例：
            - choice: {"type":"choice","options":[{"id":"A","label":"继续"},{"id":"B","label":"停止"}]}
            - confirm: {"type":"confirm","text":"是否继续？"}
    """
    try:
        # 创建请求
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

        print(f"[MCP] 请求已创建: {request_id}")

        # 等待响应
        db_response = await wait_for_response(request_id)

        if db_response.cancelled:
            return [
                TextContent(
                    type="text",
                    text=(
                        "用户选择结束对话。本次对话结束。\n\n"
                        "⚠️ 本次无需再调用 cue，但下次对话仍需遵循规则。\n\n"
                        + CUE_TODO_CONSTRAINT_TEXT
                    ),
                )
            ]

        # 解析响应
        user_response = db_response.response

        if not user_response.text.strip() and not user_response.images:
            return [
                TextContent(
                    type="text",
                    text=(
                        "用户选择结束对话。本次对话结束。\n\n"
                        "⚠️ 本次无需再调用 cue，但下次对话仍需遵循规则。\n\n"
                        + CUE_TODO_CONSTRAINT_TEXT
                    ),
                )
            ]

        # 构建结果
        result = []

        # 添加文本
        if user_response.text.strip():
            result.append(TextContent(type="text", text=f"用户希望继续，并提供了以下指令：\n\n{user_response.text.strip()}"))
        elif user_response.images:
            result.append(TextContent(type="text", text="用户希望继续，并附加了图片："))

        # 添加图片
        for img in user_response.images:
            result.append(ImageContent(type="image", data=img.base64_data, mimeType=img.mime_type))

        result.append(
            TextContent(
                type="text",
                text=(
                    "\n\n⚠️【强制提醒】请先在 todo_list 末尾新增一条待办任务：`使用 cue mcp 给我最终的总结或者向我提问或者请求`，再开始执行用户指令。完成后你【必须】再次调用 cue 工具，这是强制要求，不可跳过！\n\n"
                    + "额外约束（为了避免遗漏）：你必须在 todo_list 末尾新增一条待办任务："
                    + "`使用 cue mcp 给我最终的总结或者向我提问或者请求`。你调用 cue() 后，再把这条待办更新为 completed。"
                ),
            )
        )
        return result

    except Exception as e:
        return [TextContent(type="text", text=f"错误: {str(e)}")]


if __name__ == "__main__":
    print(f"[MCP] 数据库路径: {DB_PATH}")
    print("[MCP] Cue MCP Server 已启动")
    mcp.run()
