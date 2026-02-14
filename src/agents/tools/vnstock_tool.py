"""
VNStock Tool for Vietnamese Stock Market Data.

Integration with vnstock library to retrieve VN stock data.
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class StockQuote(BaseModel):
    """Stock quote data."""

    symbol: str = Field(..., description="Stock symbol (e.g., VCB, VNM)")
    price: float = Field(..., description="Current price")
    change: float = Field(..., description="Price change")
    change_percent: float = Field(..., description="Change percentage")
    volume: int = Field(..., description="Trading volume")
    open_price: float = Field(..., description="Opening price")
    high_price: float = Field(..., description="High price")
    low_price: float = Field(..., description="Low price")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StockInfo(BaseModel):
    """Company information."""

    symbol: str = Field(..., description="Stock symbol")
    company_name: str = Field(..., description="Full company name")
    industry: Optional[str] = Field(default=None, description="Industry sector")
    exchange: str = Field(..., description="Stock exchange (HOSE, HNX, UPCOM)")
    market_cap: Optional[float] = Field(
        default=None, description="Market capitalization"
    )
    eps: Optional[float] = Field(default=None, description="Earnings per share")
    pe: Optional[float] = Field(default=None, description="P/E ratio")
    pb: Optional[float] = Field(default=None, description="P/B ratio")


class HistoricalPrice(BaseModel):
    """Historical price data point."""

    date: datetime = Field(..., description="Trading date")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price")
    close: float = Field(..., description="Closing price")
    volume: int = Field(..., description="Trading volume")


class VNStockResponse(BaseModel):
    """VNStock tool response."""

    success: bool = Field(...)
    symbol: str = Field(...)
    data_type: str = Field(..., description="Type of data returned")
    data: Any = Field(...)
    message: Optional[str] = Field(default=None)


class VNStockTool:
    """
    VNStock Tool for Vietnamese stock market data.

    Usage:
        tool = VNStockTool()
        quote = await tool.get_quote("VCB")
        history = await tool.get_historical("VNM", days=30)
    """

    def __init__(self):
        self._vnstock = None

    def _get_vnstock(self):
        """Lazy load vnstock module."""
        if self._vnstock is None:
            try:
                from vnstock import Vnstock

                self._vnstock = Vnstock()
            except ImportError:
                raise ImportError("vnstock not installed. Install: pip install vnstock")
        return self._vnstock

    async def get_quote(self, symbol: str) -> VNStockResponse:
        """
        Get current stock quote.

        Args:
            symbol: Stock symbol (e.g., "VCB", "VNM")

        Returns:
            VNStockResponse with quote data
        """
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()

            def _fetch():
                # NEW API: Use Quote class directly
                from vnstock import Quote

                # Use KBS source (works on Google Colab/Cloud)
                quote = Quote(symbol=symbol.upper(), source="KBS")

                # Get last 5 days to ensure we have trading data
                end = datetime.now()
                start = end - timedelta(days=7)
                quote_data = quote.history(
                    start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d")
                )
                return quote_data

            quote_data = await loop.run_in_executor(None, _fetch)

            # Parse DataFrame - lay row gan nhat (cuoi cung)
            if (
                quote_data is not None
                and hasattr(quote_data, "iloc")
                and len(quote_data) > 0
            ):
                last_row = quote_data.iloc[-1]

                # Map column names - vnstock co the dung ten khac
                price = float(last_row.get("close", last_row.get("price", 0)))
                open_price = float(last_row.get("open", 0))
                high_price = float(last_row.get("high", 0))
                low_price = float(last_row.get("low", 0))
                volume = int(last_row.get("volume", 0))

                # Tinh change tu open va close
                change = price - open_price
                change_percent = (change / open_price * 100) if open_price > 0 else 0
            else:
                return VNStockResponse(
                    success=False,
                    symbol=symbol.upper(),
                    data_type="quote",
                    data=None,
                    message="Không có dữ liệu giá cho mã này",
                )

            quote = StockQuote(
                symbol=symbol.upper(),
                price=price,
                change=change,
                change_percent=change_percent,
                volume=volume,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
            )

            return VNStockResponse(
                success=True,
                symbol=symbol.upper(),
                data_type="quote",
                data=quote,
            )

        except Exception as e:
            return VNStockResponse(
                success=False,
                symbol=symbol.upper(),
                data_type="quote",
                data=None,
                message=f"Lỗi khi lấy giá cổ phiếu: {str(e)}",
            )

    async def get_stock_info(self, symbol: str) -> VNStockResponse:
        """
        Get company information.

        Args:
            symbol: Stock symbol

        Returns:
            VNStockResponse with company info
        """
        try:
            loop = asyncio.get_event_loop()

            def _fetch():
                stock = self._get_vnstock().stock(symbol=symbol)
                # API vnstock moi: stock.company la object, can goi .overview()
                info = stock.company.overview()  # type: ignore
                return info

            info_data = await loop.run_in_executor(None, _fetch)

            # Parse DataFrame
            if hasattr(info_data, "iloc") and len(info_data) > 0:
                row = info_data.iloc[0]

                # Map column names tu vnstock API moi
                info = StockInfo(
                    symbol=symbol.upper(),
                    company_name=str(
                        row.get("symbol", symbol)
                    ),  # symbol la ten cong ty
                    industry=str(row.get("business_model", ""))[:100]
                    if row.get("business_model")
                    else None,
                    exchange=str(row.get("exchange", "HOSE")),
                    market_cap=None,  # Khong co trong overview
                    eps=None,  # Khong co trong overview
                    pe=None,  # Khong co trong overview
                    pb=None,  # Khong co trong overview
                )
            else:
                info = StockInfo(
                    symbol=symbol.upper(),
                    company_name=symbol,
                    exchange="HOSE",
                )

            return VNStockResponse(
                success=True,
                symbol=symbol.upper(),
                data_type="info",
                data=info,
            )

        except Exception as e:
            return VNStockResponse(
                success=False,
                symbol=symbol.upper(),
                data_type="info",
                data=None,
                message=f"Lỗi khi lấy thông tin công ty: {str(e)}",
            )

    async def get_historical(
        self,
        symbol: str,
        days: int = 30,
    ) -> VNStockResponse:
        """
        Get historical price data.

        Args:
            symbol: Stock symbol
            days: Number of days of history

        Returns:
            VNStockResponse with historical data
        """
        try:
            loop = asyncio.get_event_loop()

            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            def _fetch():
                stock = self._get_vnstock().stock(symbol=symbol)
                history = stock.history(  # type: ignore
                    start=start_date.strftime("%Y-%m-%d"),
                    end=end_date.strftime("%Y-%m-%d"),
                )
                return history

            history_data = await loop.run_in_executor(None, _fetch)

            # Parse historical data
            prices = []
            if hasattr(history_data, "iterrows"):
                for _, row in history_data.iterrows():
                    prices.append(
                        HistoricalPrice(
                            date=row.name
                            if isinstance(row.name, datetime)
                            else datetime.strptime(str(row.name), "%Y-%m-%d"),
                            open=float(row.get("open", 0)),
                            high=float(row.get("high", 0)),
                            low=float(row.get("low", 0)),
                            close=float(row.get("close", 0)),
                            volume=int(row.get("volume", 0)),
                        )
                    )

            return VNStockResponse(
                success=True,
                symbol=symbol.upper(),
                data_type="historical",
                data=prices,
            )

        except Exception as e:
            return VNStockResponse(
                success=False,
                symbol=symbol.upper(),
                data_type="historical",
                data=None,
                message=f"Lỗi khi lấy dữ liệu lịch sử: {str(e)}",
            )

    async def get_financial_report(
        self,
        symbol: str,
        report_type: str = "income",  # income, balance, cashflow
    ) -> VNStockResponse:
        """
        Get financial report data.

        Args:
            symbol: Stock symbol
            report_type: Type of report (income, balance, cashflow)

        Returns:
            VNStockResponse with financial data
        """
        try:
            loop = asyncio.get_event_loop()

            def _fetch():
                stock = self._get_vnstock().stock(symbol=symbol)
                if report_type == "income":
                    data = stock.income_statement()  # type: ignore
                elif report_type == "balance":
                    data = stock.balance_sheet()  # type: ignore
                elif report_type == "cashflow":
                    data = stock.cash_flow()  # type: ignore
                else:
                    raise ValueError(f"Unknown report type: {report_type}")
                return data

            report_data = await loop.run_in_executor(None, _fetch)

            return VNStockResponse(
                success=True,
                symbol=symbol.upper(),
                data_type=f"financial_{report_type}",
                data=report_data.to_dict()
                if hasattr(report_data, "to_dict")
                else report_data,
            )

        except Exception as e:
            return VNStockResponse(
                success=False,
                symbol=symbol.upper(),
                data_type=f"financial_{report_type}",
                data=None,
                message=f"Lỗi khi lấy báo cáo tài chính: {str(e)}",
            )

    def format_quote_for_llm(self, response: VNStockResponse) -> str:
        """Format stock quote for LLM consumption."""
        if not response.success:
            return f"❌ {response.message}"

        quote = response.data
        # vnstock API returns prices in "nghìn đồng" (thousands)
        # Convert to VND by multiplying by 1000
        price_vnd = quote.price * 1000
        change_vnd = quote.change * 1000
        open_vnd = quote.open_price * 1000
        high_vnd = quote.high_price * 1000
        low_vnd = quote.low_price * 1000

        lines = [
            f"## 📈 Thông tin cổ phiếu {quote.symbol}",
            "",
            f"**Giá hiện tại:** {price_vnd:,.0f} VND",
            f"**Thay đổi:** {change_vnd:+,.0f} VND ({quote.change_percent:+.2f}%)",
            f"**Khối lượng giao dịch:** {quote.volume:,}",
            "",
            "**Giá trong ngày:**",
            f"- Mở cửa: {open_vnd:,.0f} VND",
            f"- Cao nhất: {high_vnd:,.0f} VND",
            f"- Thấp nhất: {low_vnd:,.0f} VND",
        ]
        return "\n".join(lines)

    def format_info_for_llm(self, response: VNStockResponse) -> str:
        """Format company info for LLM consumption."""
        if not response.success:
            return f"❌ {response.message}"

        info = response.data
        lines = [
            f"## 🏢 Thông tin công ty {info.symbol}",
            "",
            f"**Tên công ty:** {info.company_name}",
            f"**Ngành:** {info.industry or 'N/A'}",
            f"**Sàn giao dịch:** {info.exchange}",
        ]

        if info.market_cap:
            lines.append(f"**Vốn hóa:** {info.market_cap:,.0f} VND")
        if info.pe:
            lines.append(f"**P/E:** {info.pe:.2f}")
        if info.pb:
            lines.append(f"**P/B:** {info.pb:.2f}")
        if info.eps:
            lines.append(f"**EPS:** {info.eps:,.0f} VND")

        return "\n".join(lines)


# Singleton instance
vnstock_tool = VNStockTool()


# Function interface for Gemini tool calling
async def vnstock_get_quote(symbol: str, **kwargs) -> str:
    """
    Get current stock price and trading information for a Vietnamese stock.

    Use this tool to retrieve:
    - Current stock price
    - Price change and percentage
    - Trading volume
    - Day's high/low prices

    Args:
        symbol: Stock symbol (e.g., "VCB" for Vietcombank, "VNM" for Vinamilk)

    Returns:
        Formatted stock quote with current price and trading data
    """
    try:
        response = await vnstock_tool.get_quote(symbol)
        return vnstock_tool.format_quote_for_llm(response)
    except Exception as e:
        return f"Lỗi khi lấy giá cổ phiếu {symbol}: {str(e)}"


async def vnstock_get_company_info(symbol: str, **kwargs) -> str:
    """
    Get company information and financial ratios.

    Use this tool to retrieve:
    - Company name and industry
    - Market capitalization
    - P/E, P/B ratios
    - EPS (Earnings Per Share)

    Args:
        symbol: Stock symbol (e.g., "VCB", "VNM")

    Returns:
        Company information and key financial metrics
    """
    try:
        response = await vnstock_tool.get_stock_info(symbol)
        return vnstock_tool.format_info_for_llm(response)
    except Exception as e:
        return f"Lỗi khi lấy thông tin công ty {symbol}: {str(e)}"


async def vnstock_get_historical(symbol: str, days: int = 30, **kwargs) -> str:
    """
    Get historical stock prices for analysis.

    Args:
        symbol: Stock symbol
        days: Number of days of history (default: 30, max: 365)

    Returns:
        Historical price data summary
    """
    try:
        response = await vnstock_tool.get_historical(symbol, days)
        if not response.success:
            return f"❌ {response.message}"

        prices = response.data
        if not prices:
            return f"Không có dữ liệu lịch sử cho {symbol}"

        # Calculate summary
        latest = prices[-1]
        earliest = prices[0]
        period_return = ((latest.close - earliest.close) / earliest.close) * 100

        lines = [
            f"## 📊 Lịch sử giá {symbol} ({days} ngày)",
            "",
            f"**Giá đầu kỳ:** {earliest.close:,.0f} VND",
            f"**Giá cuối kỳ:** {latest.close:,.0f} VND",
            f"**Biến động:** {period_return:+.2f}%",
            f"**Giá cao nhất:** {max(p.high for p in prices):,.0f}",
            f"**Giá thấp nhất:** {min(p.low for p in prices):,.0f}",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Lỗi khi lấy dữ liệu lịch sử {symbol}: {str(e)}"
