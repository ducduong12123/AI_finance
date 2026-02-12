"""
API Schemas Package.

This package contains all Pydantic schemas for request/response validation.
All schemas mirror the Zod schemas in frontend/types/schemas/ for FE-BE consistency.

Usage:
    from api.schemas import ChatRequest, UserProfile, Transaction
    from api.schemas.chat import Message, AGUIEvent
    from api.schemas.finance import Portfolio, AssetType
"""

# ============================================
# Shared/Base schemas
# ============================================
from .shared import (
    ApiErrorDetail,
    ApiMeta,
    ApiResponse,
    BaseSchema,
    PaginationMeta,
    PaginationParams,
    SortParams,
    create_error_response,
    create_success_response,
)

# ============================================
# Chat schemas
# ============================================
from .chat import (
    AGUIEvent,
    AGUIEventType,
    ChatRequest,
    ChatResponse,
    Message,
    MessageRole,
    MessageStatus,
    ModelOption,
    RunError,
    RunFinished,
    SSEEvent,
    TextMessageContent,
    TextMessageEnd,
    TextMessageStart,
)

# ============================================
# File/Document schemas
# ============================================
from .file import (
    Document,
    DocumentChunk,
    DocumentListRequest,
    DocumentListResponse,
    DocumentStatus,
    FileType,
    FileUploadRequest,
    FileUploadResponse,
    ProcessingStatus,
    RAGQueryRequest,
    RAGQueryResponse,
    RAGQueryResult,
)

# ============================================
# User/Auth schemas
# ============================================
from .user import (
    AuthProvider,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    OAuthCallbackRequest,
    OAuthLoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterRequest,
    RegisterResponse,
    SessionInfo,
    SessionListResponse,
    UserProfile,
    UserProfileUpdate,
    UserRole,
)

# ============================================
# Conversation schemas
# ============================================
from .conversation import (
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

# ============================================
# Finance schemas
# ============================================
from .finance import (
    AssetTransaction,
    AssetTransactionCreate,
    AssetType,
    Currency,
    FinancialGoal,
    FinancialSummary,
    Portfolio,
    PortfolioAnalysis,
    PortfolioAsset,
    PortfolioCreate,
    PortfolioDetailResponse,
    PortfolioListResponse,
    PortfolioUpdate,
    Transaction,
    TransactionCategory,
    TransactionCreate,
    TransactionFilter,
    TransactionListResponse,
    TransactionType,
    TransactionUpdate,
)

# ============================================
# Backward compatibility - re-export from old schemas.py
# These are kept for compatibility with existing code
# ============================================
from .chat import StockAdvice

__all__ = [
    # Shared
    "BaseSchema",
    "PaginationParams",
    "PaginationMeta",
    "SortParams",
    "ApiResponse",
    "ApiErrorDetail",
    "ApiMeta",
    "create_success_response",
    "create_error_response",
    # Chat
    "Message",
    "MessageRole",
    "MessageStatus",
    "ChatRequest",
    "ChatResponse",
    "ModelOption",
    "AGUIEventType",
    "AGUIEvent",
    "TextMessageStart",
    "TextMessageContent",
    "TextMessageEnd",
    "RunFinished",
    "RunError",
    "SSEEvent",
    "StockAdvice",
    # File
    "FileType",
    "DocumentStatus",
    "Document",
    "DocumentChunk",
    "FileUploadRequest",
    "FileUploadResponse",
    "DocumentListRequest",
    "DocumentListResponse",
    "RAGQueryRequest",
    "RAGQueryResponse",
    "RAGQueryResult",
    "ProcessingStatus",
    # User
    "UserRole",
    "AuthProvider",
    "UserProfile",
    "UserProfileUpdate",
    "RegisterRequest",
    "RegisterResponse",
    "LoginRequest",
    "LoginResponse",
    "RefreshTokenRequest",
    "RefreshTokenResponse",
    "LogoutRequest",
    "LogoutResponse",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "OAuthLoginRequest",
    "OAuthCallbackRequest",
    "SessionInfo",
    "SessionListResponse",
    # Conversation
    "ConversationStatus",
    "Conversation",
    "ConversationCreate",
    "ConversationUpdate",
    "ConversationRenameRequest",
    "ConversationQuickAction",
    "ConversationFilter",
    "ConversationSort",
    "ConversationListRequest",
    "ConversationListResponse",
    "ConversationDetailResponse",
    "ConversationFolder",
    "ConversationFolderCreate",
    "ConversationFolderListResponse",
    "GenerateTitleRequest",
    "GenerateTitleResponse",
    "ExportConversationRequest",
    "ExportConversationResponse",
    # Finance
    "TransactionType",
    "TransactionCategory",
    "AssetType",
    "Currency",
    "Transaction",
    "TransactionCreate",
    "TransactionUpdate",
    "TransactionFilter",
    "TransactionListResponse",
    "Portfolio",
    "PortfolioCreate",
    "PortfolioUpdate",
    "PortfolioAsset",
    "PortfolioDetailResponse",
    "PortfolioListResponse",
    "AssetTransaction",
    "AssetTransactionCreate",
    "FinancialSummary",
    "PortfolioAnalysis",
    "FinancialGoal",
]
