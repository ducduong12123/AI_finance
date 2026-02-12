"""
Finance Core Pydantic schemas.

This module defines schemas for personal finance management:
- Transactions (thu chi)
- Portfolios (danh mục đầu tư)
- Categories (phân loại)
- Analysis results

Matches: frontend/types/schemas/finance.ts (Zod)
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


# ============================================
# Enums
# ============================================


class TransactionType(str, Enum):
    """Transaction type enum."""

    INCOME = "income"  # Thu nhập
    EXPENSE = "expense"  # Chi tiêu


class TransactionCategory(str, Enum):
    """Transaction categories."""

    # Income categories
    SALARY = "salary"
    INVESTMENT = "investment"
    BONUS = "bonus"
    GIFT = "gift"
    OTHER_INCOME = "other_income"

    # Expense categories
    FOOD = "food"
    TRANSPORT = "transport"
    SHOPPING = "shopping"
    ENTERTAINMENT = "entertainment"
    BILLS = "bills"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    HOUSING = "housing"
    OTHER_EXPENSE = "other_expense"


class AssetType(str, Enum):
    """Asset types for portfolio."""

    STOCK = "stock"  # Cổ phiếu
    BOND = "bond"  # Trái phiếu
    ETF = "etf"  # ETF
    CRYPTO = "crypto"  # Tiền điện tử
    REAL_ESTATE = "real_estate"  # Bất động sản
    COMMODITY = "commodity"  # Hàng hóa
    CASH = "cash"  # Tiền mặt
    OTHER = "other"  # Khác


class Currency(str, Enum):
    """Supported currencies."""

    VND = "VND"  # Vietnamese Dong
    USD = "USD"  # US Dollar
    EUR = "EUR"  # Euro
    CNY = "CNY"  # Chinese Yuan


# ============================================
# Transaction Schemas
# ============================================


class Transaction(BaseModel):
    """Transaction schema.

    Represents a single income or expense transaction.
    Matches: ZodTransaction in frontend
    """

    model_config = {"populate_by_name": True}

    id: str = Field(..., description="Transaction ID (UUID)")
    user_id: str = Field(..., alias="userId", description="Owner user ID")

    # Transaction details
    type: TransactionType = Field(
        ..., description="Transaction type: income or expense"
    )
    category: TransactionCategory = Field(..., description="Transaction category")
    amount: Decimal = Field(
        ..., gt=0, description="Transaction amount (must be positive)"
    )
    currency: Currency = Field(default=Currency.VND, description="Currency")

    # Description and metadata
    description: Optional[str] = Field(
        default=None, description="Transaction description"
    )
    notes: Optional[str] = Field(default=None, description="Additional notes")
    tags: list[str] = Field(default_factory=list, description="Tags for organization")

    # Date
    transaction_date: date = Field(
        ..., alias="transactionDate", description="Date of transaction"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        alias="createdAt",
        description="Record creation time",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        alias="updatedAt",
        description="Last update time",
    )

    # Attachments
    receipt_url: Optional[str] = Field(
        default=None, alias="receiptUrl", description="URL to receipt image"
    )
    document_ids: list[str] = Field(
        default_factory=list, alias="documentIds", description="Related document IDs"
    )

    # Recurring
    is_recurring: bool = Field(
        default=False,
        alias="isRecurring",
        description="Whether this is a recurring transaction",
    )
    recurring_id: Optional[str] = Field(
        default=None,
        alias="recurringId",
        description="ID of recurring pattern if applicable",
    )

    @field_validator("amount")
    @classmethod
    def validate_amount_precision(cls, v: Decimal) -> Decimal:
        """Ensure amount has at most 2 decimal places."""
        return round(v, 2)


class TransactionCreate(BaseModel):
    """Schema for creating a new transaction."""

    model_config = {"populate_by_name": True}

    type: TransactionType = Field(..., description="Transaction type")
    category: TransactionCategory = Field(..., description="Transaction category")
    amount: Decimal = Field(..., gt=0, description="Amount")
    currency: Currency = Field(default=Currency.VND, description="Currency")
    description: Optional[str] = Field(default=None, description="Description")
    notes: Optional[str] = Field(default=None, description="Notes")
    tags: list[str] = Field(default_factory=list, description="Tags")
    transaction_date: date = Field(
        ..., alias="transactionDate", description="Transaction date"
    )
    receipt_url: Optional[str] = Field(default=None, alias="receiptUrl")
    is_recurring: bool = Field(default=False, alias="isRecurring")


class TransactionUpdate(BaseModel):
    """Schema for updating a transaction."""

    model_config = {"populate_by_name": True}

    category: Optional[TransactionCategory] = Field(default=None)
    amount: Optional[Decimal] = Field(default=None, gt=0)
    currency: Optional[Currency] = Field(default=None)
    description: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    tags: Optional[list[str]] = Field(default=None)
    transaction_date: Optional[date] = Field(default=None, alias="transactionDate")
    receipt_url: Optional[str] = Field(default=None, alias="receiptUrl")


class TransactionFilter(BaseModel):
    """Filter criteria for transactions."""

    model_config = {"populate_by_name": True}

    type: Optional[TransactionType] = Field(default=None, description="Filter by type")
    category: Optional[TransactionCategory] = Field(
        default=None, description="Filter by category"
    )
    start_date: Optional[date] = Field(
        default=None, alias="startDate", description="Start date"
    )
    end_date: Optional[date] = Field(
        default=None, alias="endDate", description="End date"
    )
    min_amount: Optional[Decimal] = Field(
        default=None, alias="minAmount", description="Minimum amount"
    )
    max_amount: Optional[Decimal] = Field(
        default=None, alias="maxAmount", description="Maximum amount"
    )
    tags: Optional[list[str]] = Field(default=None, description="Filter by tags")
    search_query: Optional[str] = Field(
        default=None, alias="searchQuery", description="Search in description"
    )


class TransactionListResponse(BaseModel):
    """Response schema for transaction list."""

    success: bool = Field(...)
    transactions: list[Transaction] = Field(default_factory=list)
    total: int = Field(...)
    page: int = Field(...)
    limit: int = Field(...)
    total_income: Decimal = Field(
        ..., alias="totalIncome", description="Total income in results"
    )
    total_expense: Decimal = Field(
        ..., alias="totalExpense", description="Total expense in results"
    )
    net_amount: Decimal = Field(
        ..., alias="netAmount", description="Net amount (income - expense)"
    )


# ============================================
# Portfolio Schemas
# ============================================


class PortfolioAsset(BaseModel):
    """Individual asset in a portfolio.

    Matches: ZodPortfolioAsset in frontend
    """

    model_config = {"populate_by_name": True}

    id: str = Field(..., description="Asset ID (UUID)")
    portfolio_id: str = Field(
        ..., alias="portfolioId", description="Parent portfolio ID"
    )

    # Asset details
    symbol: str = Field(..., description="Asset symbol/ticker (e.g., AAPL, BTC)")
    name: str = Field(..., description="Asset name")
    type: AssetType = Field(..., description="Asset type")
    exchange: Optional[str] = Field(
        default=None, description="Exchange (e.g., HOSE, NASDAQ)"
    )

    # Holdings
    quantity: Decimal = Field(..., gt=0, description="Number of units held")
    avg_buy_price: Decimal = Field(
        ..., alias="avgBuyPrice", description="Average buy price per unit"
    )
    current_price: Optional[Decimal] = Field(
        default=None, alias="currentPrice", description="Current market price"
    )
    currency: Currency = Field(default=Currency.VND, description="Currency")

    # Calculated fields
    total_invested: Decimal = Field(
        ..., alias="totalInvested", description="Total amount invested"
    )
    current_value: Optional[Decimal] = Field(
        default=None, alias="currentValue", description="Current market value"
    )
    unrealized_pnl: Optional[Decimal] = Field(
        default=None, alias="unrealizedPnl", description="Unrealized profit/loss"
    )
    unrealized_pnl_percent: Optional[float] = Field(
        default=None,
        alias="unrealizedPnlPercent",
        description="Unrealized P&L percentage",
    )

    # Metadata
    notes: Optional[str] = Field(default=None, description="Investment notes")
    tags: list[str] = Field(default_factory=list, description="Tags")
    purchase_date: Optional[date] = Field(default=None, alias="purchaseDate")
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt")


class Portfolio(BaseModel):
    """Portfolio schema.

    Represents a collection of investments.
    Matches: ZodPortfolio in frontend
    """

    model_config = {"populate_by_name": True}

    id: str = Field(..., description="Portfolio ID (UUID)")
    user_id: str = Field(..., alias="userId", description="Owner user ID")

    # Basic info
    name: str = Field(..., min_length=1, max_length=100, description="Portfolio name")
    description: Optional[str] = Field(
        default=None, description="Portfolio description"
    )
    currency: Currency = Field(default=Currency.VND, description="Base currency")

    # Settings
    is_public: bool = Field(
        default=False, alias="isPublic", description="Whether portfolio is public"
    )
    tags: list[str] = Field(default_factory=list, description="Tags")

    # Calculated fields (updated periodically)
    total_value: Optional[Decimal] = Field(
        default=None, alias="totalValue", description="Total current value"
    )
    total_invested: Optional[Decimal] = Field(
        default=None, alias="totalInvested", description="Total amount invested"
    )
    total_pnl: Optional[Decimal] = Field(
        default=None, alias="totalPnl", description="Total profit/loss"
    )
    total_pnl_percent: Optional[float] = Field(
        default=None, alias="totalPnlPercent", description="Total P&L percentage"
    )

    # Asset allocation
    asset_allocation: Optional[dict[str, Decimal]] = Field(
        default=None, alias="assetAllocation", description="Percentage by asset type"
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt")
    last_synced_at: Optional[datetime] = Field(
        default=None, alias="lastSyncedAt", description="Last time prices were updated"
    )


class PortfolioCreate(BaseModel):
    """Schema for creating a portfolio."""

    model_config = {"populate_by_name": True}

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None)
    currency: Currency = Field(default=Currency.VND)
    is_public: bool = Field(default=False, alias="isPublic")
    tags: list[str] = Field(default_factory=list)


class PortfolioUpdate(BaseModel):
    """Schema for updating a portfolio."""

    model_config = {"populate_by_name": True}

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None)
    is_public: Optional[bool] = Field(default=None, alias="isPublic")
    tags: Optional[list[str]] = Field(default=None)


class PortfolioDetailResponse(BaseModel):
    """Detailed portfolio response including assets."""

    success: bool = Field(...)
    portfolio: Portfolio = Field(...)
    assets: list[PortfolioAsset] = Field(default_factory=list)


class PortfolioListResponse(BaseModel):
    """Response schema for portfolio list."""

    success: bool = Field(...)
    portfolios: list[Portfolio] = Field(default_factory=list)
    total: int = Field(...)


# ============================================
# Asset Transaction Schemas
# ============================================


class AssetTransaction(BaseModel):
    """Transaction record for buying/selling assets.

    Similar to stock orders.
    """

    model_config = {"populate_by_name": True}

    id: str = Field(..., description="Transaction ID (UUID)")
    asset_id: str = Field(..., alias="assetId", description="Asset ID")
    portfolio_id: str = Field(..., alias="portfolioId", description="Portfolio ID")

    # Transaction details
    type: str = Field(..., pattern="^(BUY|SELL)$", description="Transaction type")
    quantity: Decimal = Field(..., gt=0, description="Quantity")
    price: Decimal = Field(..., gt=0, description="Price per unit")
    total_amount: Decimal = Field(
        ..., alias="totalAmount", description="Total transaction amount"
    )
    fees: Decimal = Field(default=Decimal("0"), description="Transaction fees")
    currency: Currency = Field(default=Currency.VND)

    # Metadata
    transaction_date: datetime = Field(..., alias="transactionDate")
    notes: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")


class AssetTransactionCreate(BaseModel):
    """Schema for creating an asset transaction."""

    model_config = {"populate_by_name": True}

    asset_id: str = Field(..., alias="assetId")
    type: str = Field(..., pattern="^(BUY|SELL)$")
    quantity: Decimal = Field(..., gt=0)
    price: Decimal = Field(..., gt=0)
    fees: Decimal = Field(default=Decimal("0"))
    currency: Currency = Field(default=Currency.VND)
    transaction_date: datetime = Field(
        default_factory=datetime.utcnow, alias="transactionDate"
    )
    notes: Optional[str] = Field(default=None)


# ============================================
# Analysis & Summary Schemas
# ============================================


class FinancialSummary(BaseModel):
    """Financial summary for a user."""

    model_config = {"populate_by_name": True}

    # Period
    period_start: date = Field(..., alias="periodStart")
    period_end: date = Field(..., alias="periodEnd")

    # Income/Expense
    total_income: Decimal = Field(..., alias="totalIncome")
    total_expense: Decimal = Field(..., alias="totalExpense")
    net_savings: Decimal = Field(..., alias="netSavings")
    savings_rate: float = Field(
        ..., alias="savingsRate", description="Savings rate as percentage"
    )

    # Breakdown
    income_by_category: dict[str, Decimal] = Field(..., alias="incomeByCategory")
    expense_by_category: dict[str, Decimal] = Field(..., alias="expenseByCategory")

    # Trends
    daily_average: Decimal = Field(
        ..., alias="dailyAverage", description="Daily average spending"
    )
    top_expenses: list[Transaction] = Field(..., alias="topExpenses")


class PortfolioAnalysis(BaseModel):
    """Portfolio analysis results."""

    model_config = {"populate_by_name": True}

    portfolio_id: str = Field(..., alias="portfolioId")

    # Performance
    total_return: Decimal = Field(..., alias="totalReturn")
    total_return_percent: float = Field(..., alias="totalReturnPercent")
    annualized_return: Optional[float] = Field(default=None, alias="annualizedReturn")

    # Risk metrics
    volatility: Optional[float] = Field(
        default=None, description="Portfolio volatility"
    )
    sharpe_ratio: Optional[float] = Field(default=None, alias="sharpeRatio")
    max_drawdown: Optional[float] = Field(default=None, alias="maxDrawdown")

    # Allocation
    sector_allocation: Optional[dict[str, Decimal]] = Field(
        default=None, alias="sectorAllocation"
    )
    geographic_allocation: Optional[dict[str, Decimal]] = Field(
        default=None, alias="geographicAllocation"
    )

    # Recommendations
    recommendations: list[str] = Field(default_factory=list)
    risk_level: str = Field(..., alias="riskLevel", description="Low/Medium/High")


class FinancialGoal(BaseModel):
    """Financial goal schema.

    For savings targets, investment goals, etc.
    """

    model_config = {"populate_by_name": True}

    id: str = Field(..., description="Goal ID (UUID)")
    user_id: str = Field(..., alias="userId")

    name: str = Field(..., description="Goal name")
    description: Optional[str] = Field(default=None)
    target_amount: Decimal = Field(..., alias="targetAmount", gt=0)
    current_amount: Decimal = Field(default=Decimal("0"), alias="currentAmount")
    currency: Currency = Field(default=Currency.VND)

    # Timeline
    target_date: Optional[date] = Field(default=None, alias="targetDate")
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")

    # Progress
    progress_percent: float = Field(default=0, alias="progressPercent")
    is_achieved: bool = Field(default=False, alias="isAchieved")

    # Monthly contribution needed
    monthly_contribution_needed: Optional[Decimal] = Field(
        default=None, alias="monthlyContributionNeeded"
    )
