"""
File upload and RAG-related Pydantic schemas.

This module defines schemas for file upload and document processing.
These schemas support the RAG (Retrieval-Augmented Generation) functionality.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# ============================================
# Enums
# ============================================


class FileType(str, Enum):
    """Supported file types for upload."""

    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    CSV = "csv"


class DocumentStatus(str, Enum):
    """Document processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================
# Document Schemas
# ============================================


class DocumentChunk(BaseModel):
    """Document chunk schema (for vector storage).

    Represents a single chunk of text extracted from a document.
    """

    model_config = {"populate_by_name": True}

    chunk_id: str = Field(..., alias="chunkId", description="Unique chunk ID")
    document_id: str = Field(..., alias="documentId", description="Parent document ID")
    content: str = Field(..., description="Chunk text content")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")
    chunk_index: int = Field(
        ..., alias="chunkIndex", description="Index within document"
    )
    embedding: Optional[list[float]] = Field(
        default=None, description="Vector embedding"
    )


class Document(BaseModel):
    """Document schema for uploaded files.

    Matches frontend expectations for file upload responses.
    """

    model_config = {"populate_by_name": True}

    id: str = Field(..., description="Unique document ID (UUID)")
    user_id: Optional[str] = Field(
        default=None, alias="userId", description="Owner user ID"
    )
    file_name: str = Field(..., alias="fileName", description="Original file name")
    file_type: FileType = Field(..., alias="fileType", description="File type")
    file_size: int = Field(..., alias="fileSize", description="File size in bytes")
    mime_type: str = Field(..., alias="mimeType", description="MIME type")
    status: DocumentStatus = Field(
        default=DocumentStatus.PENDING, description="Processing status"
    )
    chunk_count: int = Field(
        default=0, alias="chunkCount", description="Number of chunks created"
    )
    collection_name: Optional[str] = Field(
        default=None, alias="collectionName", description="Qdrant collection name"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Document metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        alias="createdAt",
        description="Upload timestamp",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        alias="updatedAt",
        description="Last update timestamp",
    )
    processed_at: Optional[datetime] = Field(
        default=None, alias="processedAt", description="Processing completion timestamp"
    )
    error_message: Optional[str] = Field(
        default=None,
        alias="errorMessage",
        description="Error message if processing failed",
    )


# ============================================
# Request/Response Schemas
# ============================================


class FileUploadRequest(BaseModel):
    """File upload request metadata.

    Used when uploading files via multipart/form-data.
    The actual file is sent as binary data.
    """

    model_config = {"populate_by_name": True}

    collection_name: Optional[str] = Field(
        default=None, alias="collectionName", description="Target Qdrant collection"
    )
    description: Optional[str] = Field(default=None, description="Document description")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class FileUploadResponse(BaseModel):
    """File upload response schema.

    Matches frontend expectations.
    """

    success: bool = Field(..., description="Whether upload was successful")
    file_id: str = Field(..., alias="fileId", description="Uploaded file ID (UUID)")
    document: Optional[Document] = Field(default=None, description="Document details")
    chunks: int = Field(default=0, description="Number of chunks created")
    message: Optional[str] = Field(default=None, description="Status message")


class DocumentListRequest(BaseModel):
    """Request schema for listing documents."""

    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")
    status: Optional[DocumentStatus] = Field(
        default=None, description="Filter by status"
    )
    file_type: Optional[FileType] = Field(
        default=None, alias="fileType", description="Filter by file type"
    )


class DocumentListResponse(BaseModel):
    """Response schema for document list."""

    success: bool = Field(..., description="Whether request was successful")
    documents: list[Document] = Field(
        default_factory=list, description="List of documents"
    )
    total: int = Field(..., description="Total number of documents")
    page: int = Field(..., description="Current page")
    limit: int = Field(..., description="Items per page")


# ============================================
# RAG Query Schemas
# ============================================


class RAGQueryRequest(BaseModel):
    """RAG query request schema.

    For semantic search across uploaded documents.
    """

    model_config = {"populate_by_name": True}

    query: str = Field(..., min_length=1, description="Search query")
    collection_name: str = Field(
        ..., alias="collectionName", description="Qdrant collection to search"
    )
    top_k: int = Field(
        default=5, ge=1, le=20, alias="topK", description="Number of results to return"
    )
    score_threshold: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        alias="scoreThreshold",
        description="Minimum similarity score",
    )
    filters: Optional[dict[str, Any]] = Field(
        default=None, description="Additional filters"
    )


class RAGQueryResult(BaseModel):
    """Single RAG query result."""

    chunk: DocumentChunk = Field(..., description="Matching document chunk")
    score: float = Field(..., description="Similarity score (0-1)")
    rank: int = Field(..., description="Result rank")


class RAGQueryResponse(BaseModel):
    """RAG query response schema."""

    success: bool = Field(..., description="Whether query was successful")
    query: str = Field(..., description="Original query")
    results: list[RAGQueryResult] = Field(
        default_factory=list, description="Search results"
    )
    total_found: int = Field(..., alias="totalFound", description="Total results found")


# ============================================
# Processing Status
# ============================================


class ProcessingStatus(BaseModel):
    """Document processing status response."""

    document_id: str = Field(..., alias="documentId", description="Document ID")
    status: DocumentStatus = Field(..., description="Current processing status")
    progress: float = Field(
        ..., ge=0, le=100, description="Processing progress percentage"
    )
    chunks_processed: int = Field(
        ..., alias="chunksProcessed", description="Number of chunks processed"
    )
    total_chunks: int = Field(
        ..., alias="totalChunks", description="Total chunks to process"
    )
    message: Optional[str] = Field(default=None, description="Status message")
