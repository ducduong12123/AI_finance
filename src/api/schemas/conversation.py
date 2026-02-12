"""
Conversation/Chat Session Pydantic schemas.

This module defines schemas for managing chat conversations/sessions.
Allows users to organize chats with custom titles and metadata.

Matches: frontend/types/schemas/conversation.ts (Zod)
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# ============================================
# Enums
# ============================================


class ConversationStatus(str, Enum):
    """Conversation status."""

    ACTIVE = "active"  # Đang hoạt động
    ARCHIVED = "archived"  # Đã lưu trữ
    DELETED = "deleted"  # Đã xóa (soft delete)


# ============================================
# Conversation Schemas
# ============================================


class Conversation(BaseModel):
    """Chat conversation/session schema.

    Represents a conversation thread that can be named and organized.
    Matches: ZodConversation in frontend
    """

    model_config = {"populate_by_name": True}

    id: str = Field(..., description="Conversation ID (UUID)")
    user_id: str = Field(..., alias="userId", description="Owner user ID")

    # Display info
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Conversation title (user-defined or AI-generated)",
    )
    description: Optional[str] = Field(
        default=None, max_length=500, description="Optional description/summary"
    )

    # Categorization
    status: ConversationStatus = Field(
        default=ConversationStatus.ACTIVE, description="Conversation status"
    )
    folder_id: Optional[str] = Field(
        default=None, alias="folderId", description="Folder ID for organization"
    )
    tags: list[str] = Field(default_factory=list, description="Tags for filtering")
    color: Optional[str] = Field(
        default=None,
        pattern="^#[0-9A-Fa-f]{6}$",
        description="Custom color (hex format #RRGGBB)",
    )

    # Icon/Emoji
    icon: Optional[str] = Field(
        default=None, max_length=10, description="Emoji icon for the conversation"
    )

    # Stats
    message_count: int = Field(
        default=0,
        alias="messageCount",
        description="Number of messages in conversation",
    )
    total_tokens: Optional[int] = Field(
        default=None, alias="totalTokens", description="Total tokens used"
    )

    # RAG context
    document_ids: list[str] = Field(
        default_factory=list,
        alias="documentIds",
        description="Attached document IDs for RAG",
    )
    context_summary: Optional[str] = Field(
        default=None,
        alias="contextSummary",
        description="Summary of conversation context",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        alias="createdAt",
        description="Conversation creation time",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        alias="updatedAt",
        description="Last update time",
    )
    last_message_at: Optional[datetime] = Field(
        default=None, alias="lastMessageAt", description="Last message timestamp"
    )

    # Settings
    is_pinned: bool = Field(
        default=False, alias="isPinned", description="Whether conversation is pinned"
    )
    is_favorite: bool = Field(
        default=False,
        alias="isFavorite",
        description="Whether conversation is favorited",
    )
    model: str = Field(
        default="gemini-2.0-flash", description="Default model for this conversation"
    )
    temperature: float = Field(
        default=0.7, ge=0, le=2, description="Default temperature"
    )


class ConversationCreate(BaseModel):
    """Schema for creating a new conversation."""

    model_config = {"populate_by_name": True}

    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Conversation title (optional, auto-generated if not provided)",
    )
    description: Optional[str] = Field(default=None, max_length=500)
    folder_id: Optional[str] = Field(default=None, alias="folderId")
    tags: list[str] = Field(default_factory=list)
    color: Optional[str] = Field(default=None, pattern="^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(default=None, max_length=10)
    document_ids: list[str] = Field(default_factory=list, alias="documentIds")
    model: str = Field(default="gemini-2.0-flash")
    temperature: float = Field(default=0.7, ge=0, le=2)


class ConversationUpdate(BaseModel):
    """Schema for updating conversation metadata."""

    model_config = {"populate_by_name": True}

    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=500)
    folder_id: Optional[str] = Field(default=None, alias="folderId")
    tags: Optional[list[str]] = Field(default=None)
    color: Optional[str] = Field(default=None, pattern="^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(default=None, max_length=10)
    status: Optional[ConversationStatus] = Field(default=None)
    is_pinned: Optional[bool] = Field(default=None, alias="isPinned")
    is_favorite: Optional[bool] = Field(default=None, alias="isFavorite")
    model: Optional[str] = Field(default=None)
    temperature: Optional[float] = Field(default=None, ge=0, le=2)


class ConversationRenameRequest(BaseModel):
    """Simple rename request schema."""

    title: str = Field(
        ..., min_length=1, max_length=200, description="New conversation title"
    )


class ConversationQuickAction(BaseModel):
    """Quick action request (pin, favorite, archive)."""

    action: str = Field(
        ...,
        pattern="^(pin|unpin|favorite|unfavorite|archive|unarchive|delete)$",
        description="Action to perform",
    )


# ============================================
# Conversation List & Filter Schemas
# ============================================


class ConversationFilter(BaseModel):
    """Filter criteria for conversations."""

    model_config = {"populate_by_name": True}

    status: Optional[ConversationStatus] = Field(
        default=None, description="Filter by status"
    )
    folder_id: Optional[str] = Field(default=None, alias="folderId")
    tags: Optional[list[str]] = Field(default=None)
    is_pinned: Optional[bool] = Field(default=None, alias="isPinned")
    is_favorite: Optional[bool] = Field(default=None, alias="isFavorite")
    search_query: Optional[str] = Field(
        default=None, alias="searchQuery", description="Search in title/description"
    )
    date_from: Optional[datetime] = Field(default=None, alias="dateFrom")
    date_to: Optional[datetime] = Field(default=None, alias="dateTo")


class ConversationSort(str, Enum):
    """Sort options for conversation list."""

    NEWEST = "newest"  # created_at DESC
    OLDEST = "oldest"  # created_at ASC
    LAST_MESSAGE = "lastMessage"  # last_message_at DESC
    TITLE_ASC = "titleAsc"  # title ASC
    TITLE_DESC = "titleDesc"  # title DESC


class ConversationListRequest(BaseModel):
    """Request schema for listing conversations."""

    model_config = {"populate_by_name": True}

    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    filter: ConversationFilter = Field(default_factory=ConversationFilter)
    sort: ConversationSort = Field(default=ConversationSort.LAST_MESSAGE)


class ConversationListResponse(BaseModel):
    """Response schema for conversation list."""

    success: bool = Field(...)
    conversations: list[Conversation] = Field(default_factory=list)
    total: int = Field(...)
    page: int = Field(...)
    limit: int = Field(...)

    # Summary stats
    total_active: int = Field(default=0, alias="totalActive")
    total_archived: int = Field(default=0, alias="totalArchived")
    pinned_count: int = Field(default=0, alias="pinnedCount")
    favorite_count: int = Field(default=0, alias="favoriteCount")


# ============================================
# Conversation Detail (with messages)
# ============================================


class ConversationDetailResponse(BaseModel):
    """Detailed conversation response with messages."""

    success: bool = Field(...)
    conversation: Conversation = Field(...)
    messages: list[dict[str, Any]] = Field(
        default_factory=list, description="Chat messages in this conversation"
    )


# ============================================
# Folder Schemas (for organization)
# ============================================


class ConversationFolder(BaseModel):
    """Folder for organizing conversations."""

    model_config = {"populate_by_name": True}

    id: str = Field(..., description="Folder ID (UUID)")
    user_id: str = Field(..., alias="userId")

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    color: Optional[str] = Field(default=None, pattern="^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(default=None, max_length=10)

    parent_id: Optional[str] = Field(
        default=None,
        alias="parentId",
        description="Parent folder ID for nested folders",
    )

    sort_order: int = Field(default=0, alias="sortOrder")
    conversation_count: int = Field(default=0, alias="conversationCount")

    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt")


class ConversationFolderCreate(BaseModel):
    """Create folder request."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None)
    color: Optional[str] = Field(default=None, pattern="^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(default=None, max_length=10)
    parent_id: Optional[str] = Field(default=None, alias="parentId")


class ConversationFolderListResponse(BaseModel):
    """Folder list response."""

    success: bool = Field(...)
    folders: list[ConversationFolder] = Field(default_factory=list)


# ============================================
# AI-Generated Title
# ============================================


class GenerateTitleRequest(BaseModel):
    """Request AI to generate a title from messages."""

    messages: list[dict[str, Any]] = Field(
        ..., min_length=1, description="Chat messages to analyze"
    )
    max_length: int = Field(default=50, ge=10, le=200)


class GenerateTitleResponse(BaseModel):
    """AI-generated title response."""

    success: bool = Field(...)
    title: str = Field(...)
    suggested_tags: list[str] = Field(default_factory=list, alias="suggestedTags")
    suggested_icon: Optional[str] = Field(default=None, alias="suggestedIcon")


# ============================================
# Export/Import
# ============================================


class ExportConversationRequest(BaseModel):
    """Export conversation request."""

    format: str = Field(default="json", pattern="^(json|markdown|txt)$")
    include_metadata: bool = Field(default=True, alias="includeMetadata")


class ExportConversationResponse(BaseModel):
    """Export conversation response."""

    success: bool = Field(...)
    download_url: str = Field(..., alias="downloadUrl")
    expires_at: datetime = Field(..., alias="expiresAt")
    format: str = Field(...)
