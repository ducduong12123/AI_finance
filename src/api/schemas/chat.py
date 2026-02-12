"""
Chat-related Pydantic schemas.

This module defines schemas for chat functionality.
These schemas mirror the Zod schemas defined in frontend/types/schemas/chat.ts

FE-BE Contract:
- All fields must match between Pydantic (BE) and Zod (FE)
- Validation rules should be equivalent
- Types must be compatible
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator


# ============================================
# Enums
# ============================================


class MessageRole(str, Enum):
    """Message role enum."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageStatus(str, Enum):
    """Message status enum for streaming."""

    STREAMING = "streaming"
    COMPLETE = "complete"
    ERROR = "error"


class ModelOption(str, Enum):
    """Available AI models."""

    GEMINI_2_0_FLASH = "gemini-2.0-flash"
    GEMINI_1_5_PRO = "gemini-1.5-pro"


class AGUIEventType(str, Enum):
    """AG-UI event types for streaming."""

    TEXT_MESSAGE_START = "TextMessageStart"
    TEXT_MESSAGE_CONTENT = "TextMessageContent"
    TEXT_MESSAGE_END = "TextMessageEnd"
    RUN_FINISHED = "RunFinished"
    RUN_ERROR = "RunError"


# ============================================
# Message Schemas
# ============================================


class Message(BaseModel):
    """Chat message schema.

    Matches: zodMessageSchema (Zod) in frontend
    """

    model_config = {"populate_by_name": True, "extra": "allow"}

    message_id: Optional[str] = Field(
        default=None, alias="messageId", description="Unique message ID (UUID)"
    )
    role: MessageRole = Field(
        ..., description="Message role: user, assistant, or system"
    )
    content: str = Field(..., min_length=1, description="Message content")
    status: Optional[MessageStatus] = Field(
        default=None, description="Message status for streaming"
    )
    timestamp: Optional[datetime] = Field(default=None, description="Message timestamp")
    parts: Optional[list[dict]] = Field(
        default=None, description="Message parts (Vercel AI SDK format)"
    )
    name: Optional[str] = Field(default=None, description="Optional message name")

    @field_validator("content", mode="before")
    @classmethod
    def extract_content(cls, v: Any, info) -> str:
        """Extract content from parts if needed (for Vercel AI SDK compatibility)."""
        if v and isinstance(v, str):
            return v

        # Try to extract from parts
        values = info.data
        if "parts" in values and values["parts"]:
            parts = values["parts"]
            if isinstance(parts, list):
                texts = []
                for part in parts:
                    if isinstance(part, dict):
                        text = part.get("text", "")
                        if text:
                            texts.append(text)
                    elif isinstance(part, str):
                        texts.append(part)
                if texts:
                    return "\n".join(texts)

        return v or ""


# ============================================
# Chat Request/Response Schemas
# ============================================


class ChatRequest(BaseModel):
    """Chat request schema.

    Matches: zodChatRequestSchema (Zod) in frontend
    """

    model_config = {"populate_by_name": True}

    messages: list[Message] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Conversation history",
    )
    session_id: Optional[str] = Field(
        default=None,
        alias="sessionId",
        description="Unique session ID (deprecated, use conversationId)",
    )
    conversation_id: Optional[str] = Field(
        default=None,
        alias="conversationId",
        description="Conversation ID to continue existing chat (UUID)",
    )
    context_id: Optional[str] = Field(
        default=None, alias="contextId", description="RAG context ID (UUID)"
    )
    file_ids: Optional[list[str]] = Field(
        default=None, alias="fileIds", description="Attached file IDs for RAG"
    )
    stream: bool = Field(default=True, description="Enable streaming response")
    model: ModelOption = Field(
        default=ModelOption.GEMINI_2_0_FLASH, description="AI model to use"
    )
    temperature: float = Field(
        default=0.7, ge=0, le=2, description="Temperature for creativity (0-2)"
    )


class ChatResponse(BaseModel):
    """Chat response schema (non-streaming).

    Matches: zodChatResponseSchema (Zod) in frontend
    """

    success: bool = Field(..., description="Whether the request was successful")
    message_id: str = Field(..., alias="messageId", description="Response message ID")
    content: Optional[str] = Field(
        default=None, description="Response content (if not streaming)"
    )
    data: Optional[Any] = Field(default=None, description="Additional data")


# ============================================
# AG-UI Event Schemas (Streaming Protocol)
# ============================================


class TextMessageStart(BaseModel):
    """AG-UI event: Start of a new assistant message.

    Matches: zodTextMessageStartSchema (Zod) in frontend
    """

    type: Literal["TextMessageStart"] = Field(default="TextMessageStart")
    message_id: str = Field(..., alias="messageId", description="Unique message ID")
    role: str = Field(default="assistant", description="Message role")


class TextMessageContent(BaseModel):
    """AG-UI event: Streaming content chunk.

    Matches: zodTextMessageContentSchema (Zod) in frontend
    """

    type: Literal["TextMessageContent"] = Field(default="TextMessageContent")
    message_id: str = Field(
        ..., alias="messageId", description="Message ID this content belongs to"
    )
    content: str = Field(..., description="Content chunk")


class TextMessageEnd(BaseModel):
    """AG-UI event: End of a message.

    Matches: zodTextMessageEndSchema (Zod) in frontend
    """

    type: Literal["TextMessageEnd"] = Field(default="TextMessageEnd")
    message_id: str = Field(..., alias="messageId", description="Message ID")


class RunFinished(BaseModel):
    """AG-UI event: Streaming session completed.

    Matches: zodRunFinishedSchema (Zod) in frontend
    """

    type: Literal["RunFinished"] = Field(default="RunFinished")
    final_state: Optional[dict] = Field(
        default=None, alias="finalState", description="Final state of the run"
    )


class RunError(BaseModel):
    """AG-UI event: Streaming session error.

    Matches: zodRunErrorSchema (Zod) in frontend
    """

    type: Literal["RunError"] = Field(default="RunError")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(default=None, description="Error code")


# Union type for all AG-UI events
AGUIEvent = Union[
    TextMessageStart,
    TextMessageContent,
    TextMessageEnd,
    RunFinished,
    RunError,
]


# ============================================
# SSE Event Format
# ============================================


class SSEEvent(BaseModel):
    """SSE (Server-Sent Event) wrapper for AG-UI events.

    Format: EVENT: {event_type}\ndata: {json_data}
    """

    event_type: str = Field(..., alias="eventType", description="Event type")
    data: AGUIEvent = Field(..., description="Event data")


# ============================================
# Legacy Schemas (Backward Compatibility)
# ============================================


class StockAdvice(BaseModel):
    """Legacy stock advice schema.

    Kept for backward compatibility.
    Consider using more specific schemas in new code.
    """

    ticker: str = Field(..., description="Mã chứng khoán (ví dụ: AAPL, BTC)")
    price: float = Field(
        ..., gt=0, description="Giá cổ phiếu hiện tại (phải lớn hơn 0)"
    )
    advice_messages: list[str] = Field(
        default_factory=list,
        alias="adviceMessages",
        description="Danh sách tin nhắn tư vấn",
    )

    @field_validator("ticker", mode="before")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        """Normalize ticker symbol."""
        v = v.strip().upper()
        if not (3 <= len(v) <= 5):
            raise ValueError("Mã chứng khoán (ticker) phải có từ 3 đến 5 ký tự.")
        return v
