"""SQLModel 数据模型"""
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel
from sqlmodel import Column, Field, SQLModel, Text


class RequestStatus(str, Enum):
    """请求状态"""
    PENDING = "pending"      # 等待客户端处理（cue-hub / 模拟器）
    COMPLETED = "completed"   # 已完成（有响应）
    CANCELLED = "cancelled"   # 已取消


class ImageContent(BaseModel):
    """图片内容"""
    mime_type: str  # image/png, image/jpeg 等
    base64_data: str  # base64 编码的图片数据


class UserResponse(BaseModel):
    """用户响应内容"""
    text: str = ""  # 文本内容
    images: list[ImageContent] = []  # 图片列表

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> "UserResponse":
        """从 JSON 字符串解析"""
        return cls.model_validate_json(json_str)


class CueRequest(SQLModel, table=True):
    """MCP → 客户端（cue-hub / 模拟器）的请求"""
    __tablename__ = "cue_requests"

    id: Optional[int] = Field(default=None, primary_key=True)
    request_id: str = Field(unique=True, index=True)
    agent_id: str = Field(default="", index=True)
    prompt: str  # 给用户的回复/总结/消息正文
    payload: Optional[str] = Field(default=None, sa_column=Column(Text))  # 可选结构化载荷（JSON 字符串）
    status: RequestStatus = Field(default=RequestStatus.PENDING)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CueResponse(SQLModel, table=True):
    """客户端（cue-hub / 模拟器）→ MCP 的响应"""
    __tablename__ = "cue_responses"

    id: Optional[int] = Field(default=None, primary_key=True)
    request_id: str = Field(unique=True, index=True, foreign_key="cue_requests.request_id")
    response_json: str = Field(sa_column=Column(Text))  # UserResponse 的 JSON 序列化
    cancelled: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def response(self) -> UserResponse:
        """获取解析后的响应"""
        return UserResponse.from_json(self.response_json)

    @classmethod
    def create(cls, request_id: str, response: UserResponse, cancelled: bool = False):
        """创建响应"""
        return cls(
            request_id=request_id,
            response_json=response.to_json(),
            cancelled=cancelled
        )
