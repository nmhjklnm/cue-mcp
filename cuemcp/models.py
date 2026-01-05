"""SQLModel data models."""
import json
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel
from sqlmodel import Column, Field, SQLModel, Text


 # Debug: 联调失败优先查调用是否到达/是否入库，不要先怀疑 status 大小写
class RequestStatus(str, Enum):
    """Request status."""
    PENDING = "PENDING"      # Waiting for client handling (cue-hub / simulator)
    COMPLETED = "COMPLETED"   # Completed (has response)
    CANCELLED = "CANCELLED"   # Cancelled


class ImageContent(BaseModel):
    """Image content."""
    mime_type: str  # image/png, image/jpeg, etc.
    base64_data: str  # base64-encoded image bytes


class UserResponse(BaseModel):
    """User response content."""
    text: str = ""  # Text content
    images: list[ImageContent] = []  # Image list

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> "UserResponse":
        """Parse from JSON string."""
        return cls.model_validate_json(json_str)


class CueRequest(SQLModel, table=True):
    """Request from MCP -> client (cue-hub / simulator)."""
    __tablename__ = "cue_requests"

    id: Optional[int] = Field(default=None, primary_key=True)
    request_id: str = Field(unique=True, index=True)
    agent_id: str = Field(default="", index=True)
    prompt: str  # Message body shown to the user
    payload: Optional[str] = Field(default=None, sa_column=Column(Text))  # Optional structured payload (JSON string)
    status: RequestStatus = Field(default=RequestStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class CueResponse(SQLModel, table=True):
    """Response from client (cue-hub / simulator) -> MCP."""
    __tablename__ = "cue_responses"

    id: Optional[int] = Field(default=None, primary_key=True)
    request_id: str = Field(unique=True, index=True, foreign_key="cue_requests.request_id")
    response_json: str = Field(sa_column=Column(Text))  # JSON-serialized UserResponse
    cancelled: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def response(self) -> UserResponse:
        """Return the parsed response."""
        return UserResponse.from_json(self.response_json)

    @classmethod
    def create(cls, request_id: str, response: UserResponse, cancelled: bool = False):
        """Create a response."""
        return cls(
            request_id=request_id,
            response_json=response.to_json(),
            cancelled=cancelled
        )
