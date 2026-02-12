"""
User and Authentication Pydantic schemas.

This module defines schemas for user management and authentication.
Integrates with Supabase Auth.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, EmailStr, Field


# ============================================
# Enums
# ============================================


class UserRole(str, Enum):
    """User role enum."""

    USER = "user"
    ADMIN = "admin"
    PREMIUM = "premium"


class AuthProvider(str, Enum):
    """Authentication provider."""

    EMAIL = "email"
    GOOGLE = "google"
    GITHUB = "github"


# ============================================
# User Profile Schemas
# ============================================


class UserProfile(BaseModel):
    """User profile schema.

    Matches: ZodUserProfile in frontend (to be created)
    """

    model_config = {"populate_by_name": True}

    id: str = Field(..., description="User ID (UUID from Supabase)")
    email: EmailStr = Field(..., description="User email")
    full_name: Optional[str] = Field(
        default=None, alias="fullName", description="Full name"
    )
    avatar_url: Optional[str] = Field(
        default=None, alias="avatarUrl", description="Avatar URL"
    )
    role: UserRole = Field(default=UserRole.USER, description="User role")
    provider: AuthProvider = Field(
        default=AuthProvider.EMAIL, description="Auth provider"
    )
    preferences: dict[str, Any] = Field(
        default_factory=dict, description="User preferences"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        alias="createdAt",
        description="Account creation time",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        alias="updatedAt",
        description="Last update time",
    )
    last_login: Optional[datetime] = Field(
        default=None, alias="lastLogin", description="Last login time"
    )
    is_active: bool = Field(
        default=True, alias="isActive", description="Whether account is active"
    )


class UserProfileUpdate(BaseModel):
    """User profile update schema.

    Only includes fields that can be updated by the user.
    """

    model_config = {"populate_by_name": True}

    full_name: Optional[str] = Field(
        default=None, alias="fullName", description="Full name"
    )
    avatar_url: Optional[str] = Field(
        default=None, alias="avatarUrl", description="Avatar URL"
    )
    preferences: Optional[dict[str, Any]] = Field(
        default=None, description="User preferences"
    )


# ============================================
# Authentication Schemas
# ============================================


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    full_name: Optional[str] = Field(
        default=None, alias="fullName", description="Full name"
    )


class RegisterResponse(BaseModel):
    """User registration response."""

    success: bool = Field(..., description="Whether registration was successful")
    user_id: Optional[str] = Field(
        default=None, alias="userId", description="Created user ID"
    )
    message: Optional[str] = Field(default=None, description="Status message")
    requires_email_confirmation: bool = Field(
        default=False,
        alias="requiresEmailConfirmation",
        description="Whether email confirmation is required",
    )


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="Password")


class LoginResponse(BaseModel):
    """User login response."""

    success: bool = Field(..., description="Whether login was successful")
    access_token: Optional[str] = Field(
        default=None, alias="accessToken", description="JWT access token"
    )
    refresh_token: Optional[str] = Field(
        default=None, alias="refreshToken", description="JWT refresh token"
    )
    expires_in: Optional[int] = Field(
        default=None, alias="expiresIn", description="Token expiry in seconds"
    )
    user: Optional[UserProfile] = Field(default=None, description="User profile")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class RefreshTokenRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str = Field(..., alias="refreshToken", description="Refresh token")


class RefreshTokenResponse(BaseModel):
    """Token refresh response."""

    success: bool = Field(..., description="Whether refresh was successful")
    access_token: Optional[str] = Field(
        default=None, alias="accessToken", description="New access token"
    )
    expires_in: Optional[int] = Field(
        default=None, alias="expiresIn", description="Token expiry in seconds"
    )


class LogoutRequest(BaseModel):
    """Logout request."""

    refresh_token: Optional[str] = Field(
        default=None, alias="refreshToken", description="Refresh token to revoke"
    )


class LogoutResponse(BaseModel):
    """Logout response."""

    success: bool = Field(..., description="Whether logout was successful")
    message: Optional[str] = Field(default=None, description="Status message")


class PasswordResetRequest(BaseModel):
    """Password reset request."""

    email: EmailStr = Field(..., description="User email")


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""

    token: str = Field(..., description="Reset token")
    new_password: str = Field(
        ..., min_length=8, alias="newPassword", description="New password"
    )


# ============================================
# OAuth Schemas
# ============================================


class OAuthLoginRequest(BaseModel):
    """OAuth login request."""

    provider: AuthProvider = Field(..., description="OAuth provider")
    redirect_url: str = Field(
        ..., alias="redirectUrl", description="Redirect URL after OAuth"
    )


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request."""

    provider: AuthProvider = Field(..., description="OAuth provider")
    code: str = Field(..., description="Authorization code")
    state: Optional[str] = Field(
        default=None, description="State parameter for CSRF protection"
    )


# ============================================
# Session Schemas
# ============================================


class SessionInfo(BaseModel):
    """User session information."""

    model_config = {"populate_by_name": True}

    session_id: str = Field(..., alias="sessionId", description="Session ID")
    user_id: str = Field(..., alias="userId", description="User ID")
    created_at: datetime = Field(
        ..., alias="createdAt", description="Session creation time"
    )
    expires_at: datetime = Field(
        ..., alias="expiresAt", description="Session expiry time"
    )
    ip_address: Optional[str] = Field(
        default=None, alias="ipAddress", description="IP address"
    )
    user_agent: Optional[str] = Field(
        default=None, alias="userAgent", description="User agent"
    )


class SessionListResponse(BaseModel):
    """User sessions list response."""

    success: bool = Field(..., description="Whether request was successful")
    sessions: list[SessionInfo] = Field(
        default_factory=list, description="List of sessions"
    )
    current_session_id: str = Field(
        ..., alias="currentSessionId", description="Current session ID"
    )
