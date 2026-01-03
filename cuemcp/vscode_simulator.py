#!/usr/bin/env python3
"""客户端模拟器交互脚本
轮询数据库，处理用户请求
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

# 配置
DB_PATH = Path.home() / ".cue/cue.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=False)
SQLModel.metadata.create_all(engine)


def _read_multiline_text() -> str:
    if not _PROMPT_TOOLKIT_AVAILABLE:
        print("(提示：可选安装 prompt_toolkit 以支持多行编辑：pip install prompt_toolkit)")
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
    """读取图片路径（支持拖拽），返回路径列表。"""
    print("📎 图片（可选）：输入图片路径（可拖拽文件到终端），多张用逗号分隔；直接回车跳过")
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
            print(f"⚠️ 跳过不存在的文件: {path}")
            continue

        mime, _ = mimetypes.guess_type(str(path))
        if not mime:
            mime = "application/octet-stream"
        if not mime.startswith("image/"):
            print(f"⚠️ 跳过非图片文件({mime}): {path}")
            continue

        try:
            data = path.read_bytes()
        except Exception as e:
            print(f"⚠️ 读取失败: {path} ({e})")
            continue

        b64 = base64.b64encode(data).decode("utf-8")
        images.append(ImageContent(mime_type=mime, base64_data=b64))
    return images


async def poll_requests():
    """轮询数据库查找待处理请求"""
    print("🔍 开始监听请求...")
    print(f"📁 数据库: {DB_PATH}\n")

    while True:
        with Session(engine) as session:
            # 查找 pending 状态的请求
            request = session.exec(
                select(CueRequest)
                .where(CueRequest.status == RequestStatus.PENDING)
                .order_by(CueRequest.created_at)
            ).first()

            if request:
                # 处理请求
                await handle_request(request)

        # 每 500ms 检查一次
        await asyncio.sleep(0.5)


async def handle_request(request: CueRequest):
    """处理单个请求"""
    print("=" * 60)
    print(f"📨 收到新请求: {request.request_id}")
    print(f"📝 内容: {request.prompt}")
    if request.payload:
        try:
            print(render_payload(request.payload, debug=False))
        except Exception:
            print("🧩 Payload(原始):")
            print(request.payload)
    print("=" * 60)

    # 获取用户输入
    print("\n💬 请输入你的回复（Enter 提交；Ctrl+J 或 Alt+Enter 换行）:")
    user_text = await asyncio.to_thread(_read_multiline_text)

    image_paths = await asyncio.to_thread(_read_image_paths)
    images = _encode_images(image_paths)

    # 创建响应对象
    user_response = UserResponse(text=user_text, images=images)

    # 写入响应
    with Session(engine) as session:
        response = CueResponse.create(
            request_id=request.request_id,
            response=user_response,
            cancelled=(not user_text and not images)
        )
        session.add(response)

        # 更新请求状态
        db_request = session.get(CueRequest, request.id)
        if db_request:
            db_request.status = RequestStatus.COMPLETED
            db_request.updated_at = datetime.now(timezone.utc)
            session.add(db_request)

        session.commit()

    if user_text:
        print(f"✅ 已发送响应: {user_text[:50]}{'...' if len(user_text) > 50 else ''}\n")
    else:
        print("✅ 已发送结束信号\n")


async def _amain() -> None:
    """主函数"""
    print("🚀 Windsurf Ask Continue - 客户端模拟器")
    print("=" * 60)

    try:
        await poll_requests()
    except KeyboardInterrupt:
        print("\n\n👋 已停止监听")


def main() -> None:
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
