"""
API Schemas (Legacy Entry Point).

This module is kept for backward compatibility.
New code should import from the schemas package directly:
    from api.schemas import ChatRequest, Message

This file re-exports all schemas from the new modular structure.
"""

# Re-export everything from the new schemas package
from api.schemas.chat import (
    ChatRequest,
    ChatResponse,
    Message,
    MessageRole,
    MessageStatus,
    ModelOption,
    StockAdvice,
)

# Import shared utilities
from api.schemas.shared import ApiResponse

__all__ = [
    "Message",
    "MessageRole",
    "MessageStatus",
    "ChatRequest",
    "ChatResponse",
    "ModelOption",
    "StockAdvice",
    "ApiResponse",
]
