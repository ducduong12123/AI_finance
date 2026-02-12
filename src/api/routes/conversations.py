"""
Conversation Management API Routes.

Provides endpoints for:
- Creating, reading, updating, deleting conversations
- Renaming conversations with custom titles
- Organizing conversations (folders, tags, pins, favorites)
- AI-generated titles
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.schemas.conversation import (
    Conversation,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationFilter,
    ConversationFolder,
    ConversationFolderCreate,
    ConversationFolderListResponse,
    ConversationListRequest,
    ConversationListResponse,
    ConversationQuickAction,
    ConversationRenameRequest,
    ConversationSort,
    ConversationStatus,
    ConversationUpdate,
    ExportConversationRequest,
    ExportConversationResponse,
    GenerateTitleRequest,
    GenerateTitleResponse,
)
from api.schemas.shared import create_error_response, create_success_response

router = APIRouter(prefix="/conversations", tags=["conversations"])


# ============================================
# Conversation CRUD
# ============================================


@router.post("", response_model=ConversationListResponse)
async def list_conversations(
    request: ConversationListRequest,
    user_id: str = "user_123",  # TODO: Get from auth
):
    """
    List user's conversations with filtering and pagination.

    Supports:
    - Pagination (page, limit)
    - Filtering (status, folder, tags, favorites, pinned)
    - Sorting (newest, oldest, last message, title)
    - Search (title/description)
    """
    # TODO: Implement with database
    # Placeholder response
    return ConversationListResponse(
        success=True,
        conversations=[],  # Fetch from DB
        total=0,
        page=request.page,
        limit=request.limit,
    )


@router.post("/create", response_model=Conversation)
async def create_conversation(
    request: ConversationCreate,
    user_id: str = "user_123",  # TODO: Get from auth
):
    """
    Create a new conversation.

    If title is not provided, it will be auto-generated from first message
    or set to "New Conversation".
    """
    # TODO: Implement with database
    conversation = Conversation(
        id="conv_" + datetime.utcnow().strftime("%Y%m%d%H%M%S"),
        user_id=user_id,
        title=request.title or "Cuộc trò chuyện mới",
        description=request.description,
        folder_id=request.folder_id,
        tags=request.tags,
        color=request.color,
        icon=request.icon,
        document_ids=request.document_ids,
        model=request.model,
        temperature=request.temperature,
    )
    return conversation


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    user_id: str = "user_123",  # TODO: Get from auth
):
    """Get conversation details including messages."""
    # TODO: Implement with database
    raise HTTPException(status_code=404, detail="Conversation not found")


@router.put("/{conversation_id}", response_model=Conversation)
async def update_conversation(
    conversation_id: str,
    request: ConversationUpdate,
    user_id: str = "user_123",  # TODO: Get from auth
):
    """Update conversation metadata."""
    # TODO: Implement with database
    raise HTTPException(status_code=404, detail="Conversation not found")


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    permanent: bool = Query(
        default=False, description="Permanently delete (hard delete)"
    ),
    user_id: str = "user_123",  # TODO: Get from auth
):
    """
    Delete a conversation.

    Default is soft delete (marks as deleted).
    Set permanent=true for hard delete.
    """
    # TODO: Implement with database
    return {"success": True, "message": "Conversation deleted"}


# ============================================
# Conversation Renaming
# ============================================


@router.post("/{conversation_id}/rename", response_model=Conversation)
async def rename_conversation(
    conversation_id: str,
    request: ConversationRenameRequest,
    user_id: str = "user_123",  # TODO: Get from auth
):
    """
        Quickly rename a conversation.

        Simple endpoint specifically for renaming without needing
    to send full update payload.
    """
    # TODO: Implement with database
    # Placeholder: return updated conversation
    return Conversation(
        id=conversation_id,
        user_id=user_id,
        title=request.title,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@router.post("/{conversation_id}/generate-title", response_model=GenerateTitleResponse)
async def generate_title(
    conversation_id: str,
    request: GenerateTitleRequest,
    user_id: str = "user_123",  # TODO: Get from auth
):
    """
        Use AI to generate a conversation title from messages.

        Analyzes the conversation content and suggests a concise,
    descriptive title.
    """
    # TODO: Integrate with LLM to generate title
    # Placeholder response
    return GenerateTitleResponse(
        success=True,
        title="Tư vấn đầu tư chứng khoán tháng 2",
        suggested_tags=["tài chính", "đầu tư", "chứng khoán"],
        suggested_icon="📈",
    )


# ============================================
# Quick Actions
# ============================================


@router.post("/{conversation_id}/action")
async def quick_action(
    conversation_id: str,
    request: ConversationQuickAction,
    user_id: str = "user_123",  # TODO: Get from auth
):
    """
    Perform quick actions on conversation.

    Actions:
    - pin/unpin: Pin/unpin conversation to top
    - favorite/unfavorite: Mark as favorite
    - archive/unarchive: Move to/from archive
    - delete: Soft delete
    """
    action_messages = {
        "pin": "Conversation pinned",
        "unpin": "Conversation unpinned",
        "favorite": "Added to favorites",
        "unfavorite": "Removed from favorites",
        "archive": "Conversation archived",
        "unarchive": "Conversation restored",
        "delete": "Conversation deleted",
    }

    # TODO: Implement with database
    return {
        "success": True,
        "action": request.action,
        "message": action_messages.get(request.action, "Action completed"),
    }


# ============================================
# Folder Management
# ============================================


@router.get("/folders", response_model=ConversationFolderListResponse)
async def list_folders(
    user_id: str = "user_123",  # TODO: Get from auth
):
    """List all conversation folders."""
    # TODO: Implement with database
    return ConversationFolderListResponse(success=True, folders=[])


@router.post("/folders/create", response_model=ConversationFolder)
async def create_folder(
    request: ConversationFolderCreate,
    user_id: str = "user_123",  # TODO: Get from auth
):
    """Create a new folder for organizing conversations."""
    # TODO: Implement with database
    return ConversationFolder(
        id="folder_" + datetime.utcnow().strftime("%Y%m%d%H%M%S"),
        user_id=user_id,
        name=request.name,
        description=request.description,
        color=request.color,
        icon=request.icon,
        parent_id=request.parent_id,
    )


@router.put("/folders/{folder_id}", response_model=ConversationFolder)
async def update_folder(
    folder_id: str,
    request: ConversationFolderCreate,
    user_id: str = "user_123",  # TODO: Get from auth
):
    """Update folder details."""
    # TODO: Implement with database
    raise HTTPException(status_code=404, detail="Folder not found")


@router.delete("/folders/{folder_id}")
async def delete_folder(
    folder_id: str,
    move_conversations_to: Optional[str] = Query(
        default=None,
        alias="moveTo",
        description="Move conversations to another folder before deleting",
    ),
    user_id: str = "user_123",  # TODO: Get from auth
):
    """
    Delete a folder.

    Optionally move conversations to another folder first.
    """
    # TODO: Implement with database
    return {"success": True, "message": "Folder deleted"}


# ============================================
# Bulk Operations
# ============================================


class BulkMoveRequest(BaseModel):
    conversation_ids: list[str]
    folder_id: Optional[str] = None


@router.post("/bulk/move")
async def bulk_move_conversations(
    request: BulkMoveRequest,
    user_id: str = "user_123",  # TODO: Get from auth
):
    """Move multiple conversations to a folder (or remove from folder)."""
    # TODO: Implement with database
    return {
        "success": True,
        "message": f"Moved {len(request.conversation_ids)} conversations",
        "folder_id": request.folder_id,
    }


class BulkDeleteRequest(BaseModel):
    conversation_ids: list[str]
    permanent: bool = False


@router.post("/bulk/delete")
async def bulk_delete_conversations(
    request: BulkDeleteRequest,
    user_id: str = "user_123",  # TODO: Get from auth
):
    """Delete multiple conversations at once."""
    # TODO: Implement with database
    return {
        "success": True,
        "message": f"Deleted {len(request.conversation_ids)} conversations",
        "permanent": request.permanent,
    }


# ============================================
# Export
# ============================================


@router.post("/{conversation_id}/export", response_model=ExportConversationResponse)
async def export_conversation(
    conversation_id: str,
    request: ExportConversationRequest,
    user_id: str = "user_123",  # TODO: Get from auth
):
    """
    Export conversation to file.

    Formats: json, markdown, txt
    """
    # TODO: Implement export logic
    return ExportConversationResponse(
        success=True,
        download_url=f"/api/conversations/{conversation_id}/download?format={request.format}",
        expires_at=datetime.utcnow(),
        format=request.format,
    )


# ============================================
# Stats & Analytics
# ============================================


@router.get("/stats/summary")
async def get_conversation_stats(
    user_id: str = "user_123",  # TODO: Get from auth
):
    """Get conversation statistics for the user."""
    # TODO: Implement with database
    return {
        "success": True,
        "total_conversations": 0,
        "active_conversations": 0,
        "archived_conversations": 0,
        "pinned_conversations": 0,
        "favorite_conversations": 0,
        "total_messages": 0,
        "conversations_this_week": 0,
        "conversations_this_month": 0,
    }
