"""
Shared utilities and base schemas for API.

This module provides shared Pydantic models that mirror Zod schemas in frontend.
FE-BE Contract: All models should match corresponding Zod schemas.
"""

from datetime import datetime
from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, Field


T = TypeVar("T")


# ============================================
# Base Models
# ============================================


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = {"populate_by_name": True, "extra": "allow"}


# ============================================
# Pagination
# ============================================


class PaginationParams(BaseSchema):
    """Pagination parameters for list endpoints.

    Matches: ZodPaginationParams in frontend
    """

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")


class PaginationMeta(BaseSchema):
    """Pagination metadata in responses."""

    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


# ============================================
# Sorting
# ============================================


class SortParams(BaseSchema):
    """Sorting parameters.

    n    Matches: ZodSortParams in frontend
    """

    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$")


# ============================================
# API Response Wrappers
# ============================================


class ApiErrorDetail(BaseSchema):
    """Error detail in API responses."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[dict[str, Any]] = Field(
        default=None, description="Additional error details"
    )


class ApiMeta(BaseSchema):
    """Metadata in API responses."""

    request_id: Optional[str] = Field(default=None, description="Unique request ID")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )
    latency: Optional[float] = Field(default=None, description="Request latency in ms")


class ApiResponse(BaseSchema, Generic[T]):
    """Generic API response wrapper.

    Matches: zodApiResponse in frontend
    """

    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[T] = Field(default=None, description="Response data")
    error: Optional[ApiErrorDetail] = Field(
        default=None, description="Error details if failed"
    )
    meta: Optional[ApiMeta] = Field(default=None, description="Response metadata")


# ============================================
# Validation Utilities
# ============================================


def create_success_response(
    data: T, request_id: Optional[str] = None
) -> ApiResponse[T]:
    """Create a successful API response."""
    return ApiResponse(
        success=True,
        data=data,
        meta=ApiMeta(request_id=request_id),
    )


def create_error_response(
    code: str,
    message: str,
    details: Optional[dict] = None,
    request_id: Optional[str] = None,
) -> ApiResponse[Any]:
    """Create an error API response."""
    return ApiResponse(
        success=False,
        error=ApiErrorDetail(code=code, message=message, details=details),
        meta=ApiMeta(request_id=request_id),
    )
