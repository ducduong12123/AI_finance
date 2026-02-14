"""
Tavily Web Search Tool.

Integration with Tavily API for AI-optimized web search.
Tavily provides search results specifically formatted for LLM consumption.

API Reference: https://docs.tavily.com/documentation/api-reference/endpoint/search
"""

import asyncio
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from core.config import settings


class TavilySearchResult(BaseModel):
    """Single search result from Tavily."""

    title: str = Field(..., description="Result title")
    url: str = Field(..., description="Source URL")
    content: str = Field(..., description="Content snippet")
    score: float = Field(..., description="Relevance score")
    raw_content: Optional[str] = Field(
        default=None, description="Full raw content if available"
    )


class TavilySearchResponse(BaseModel):
    """Tavily search response."""

    query: str = Field(..., description="Original search query")
    results: List[TavilySearchResult] = Field(default_factory=list)
    answer: Optional[str] = Field(
        default=None, description="AI-generated answer if include_answer is set"
    )
    total_results: int = Field(default=0)
    search_time: float = Field(default=0.0, description="Search time in seconds")


# Valid search_depth values per Tavily API docs
VALID_SEARCH_DEPTHS = ("basic", "advanced", "fast", "ultra-fast")
# Valid topic values
VALID_TOPICS = ("general", "news", "finance")
# Valid time_range values
VALID_TIME_RANGES = ("day", "week", "month", "year", "d", "w", "m", "y")


class TavilySearchTool:
    """
    Tavily Web Search Tool for multi-agent system.

    Usage:
        tool = TavilySearchTool()
        results = await tool.search("Giá cổ phiếu VCB hôm nay")
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.TAVILY_API_KEY
        self.base_url = "https://api.tavily.com"

    async def search(
        self,
        query: str,
        search_depth: str = "basic",  # "basic", "advanced", "fast", "ultra-fast"
        topic: str = "general",  # "general", "news", "finance"
        time_range: Optional[str] = None,  # "day", "week", "month", "year"
        max_results: int = 5,
        include_answer: bool = True,
        include_raw_content: bool = False,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
    ) -> TavilySearchResponse:
        """
        Execute web search using Tavily API.

        Args:
            query: Search query
            search_depth: "basic" (balanced), "advanced" (highest relevance),
                          "fast" (lower latency), "ultra-fast" (minimal latency)
            topic: "general", "news" (real-time updates), "finance" (financial data)
            time_range: Filter by recency - "day", "week", "month", "year"
            max_results: Number of results (1-20)
            include_answer: Include AI-generated answer
            include_raw_content: Include full page content
            include_domains: List of domains to include
            exclude_domains: List of domains to exclude

        Returns:
            TavilySearchResponse with results
        """
        if not self.api_key:
            raise ValueError(
                "Tavily API key not configured. Please set TAVILY_API_KEY in .env"
            )

        try:
            import aiohttp

            payload = {
                "api_key": self.api_key,
                "query": query,
                "search_depth": search_depth,
                "topic": topic,
                "max_results": max_results,
                "include_answer": include_answer,
                "include_raw_content": include_raw_content,
            }

            if time_range:
                payload["time_range"] = time_range
            if include_domains:
                payload["include_domains"] = include_domains
            if exclude_domains:
                payload["exclude_domains"] = exclude_domains

            start_time = asyncio.get_event_loop().time()

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/search",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(
                            f"Tavily API error: {response.status} - {error_text}"
                        )

                    data = await response.json()

            search_time = asyncio.get_event_loop().time() - start_time

            # Parse results
            results = []
            for result_data in data.get("results", []):
                results.append(
                    TavilySearchResult(
                        title=result_data.get("title", ""),
                        url=result_data.get("url", ""),
                        content=result_data.get("content", ""),
                        score=result_data.get("score", 0.0),
                        raw_content=result_data.get("raw_content"),
                    )
                )

            return TavilySearchResponse(
                query=query,
                results=results,
                answer=data.get("answer"),
                total_results=len(results),
                search_time=search_time,
            )

        except ImportError:
            raise ImportError("aiohttp required. Install: pip install aiohttp")
        except Exception as e:
            raise Exception(f"Tavily search failed: {str(e)}")

    async def search_multiple(
        self, queries: List[str], **kwargs
    ) -> List[TavilySearchResponse]:
        """
        Execute multiple searches in parallel.

        Args:
            queries: List of search queries
            **kwargs: Additional arguments for search()

        Returns:
            List of TavilySearchResponse
        """
        tasks = [self.search(query, **kwargs) for query in queries]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def format_results_for_llm(self, response: TavilySearchResponse) -> str:
        """
        Format search results for LLM consumption.

        Args:
            response: TavilySearchResponse

        Returns:
            Formatted string for LLM
        """
        lines = [
            f"## Web Search Results for: {response.query}",
            f"*Found {response.total_results} results in {response.search_time:.2f}s*",
            "",
        ]

        if response.answer:
            lines.extend(
                [
                    "### AI-Generated Summary:",
                    response.answer,
                    "",
                ]
            )

        lines.append("### Detailed Results:")
        for i, result in enumerate(response.results, 1):
            lines.extend(
                [
                    f"\n{i}. **{result.title}**",
                    f"   URL: {result.url}",
                    f"   Relevance: {result.score:.2f}",
                    f"   Content: {result.content}",
                ]
            )
            if result.raw_content:
                lines.append(f"   Full Content: {result.raw_content[:500]}...")

        return "\n".join(lines)


# Singleton instance
tavily_tool = TavilySearchTool()


def _normalize_search_depth(value: str) -> str:
    """Normalize search_depth to a valid Tavily API value."""
    if value in VALID_SEARCH_DEPTHS:
        return value
    # Map common aliases
    mapping = {
        "comprehensive": "advanced",
        "deep": "advanced",
        "quick": "fast",
        "fastest": "ultra-fast",
    }
    return mapping.get(value, "basic")


def _normalize_topic(value: str) -> str:
    """Normalize topic to a valid Tavily API value."""
    if value in VALID_TOPICS:
        return value
    mapping = {
        "financial": "finance",
        "stock": "finance",
        "market": "finance",
        "breaking": "news",
        "current": "news",
    }
    return mapping.get(value, "general")


def _normalize_time_range(value: Any) -> Optional[str]:
    """Normalize time_range — handle both string and legacy integer (days) format."""
    if value is None:
        return None
    if isinstance(value, str) and value in VALID_TIME_RANGES:
        return value
    # Handle legacy integer days format from Orchestrator
    if isinstance(value, (int, float)):
        days = int(value)
        if days <= 1:
            return "day"
        elif days <= 7:
            return "week"
        elif days <= 30:
            return "month"
        else:
            return "year"
    # Handle string integers
    if isinstance(value, str):
        try:
            return _normalize_time_range(int(value))
        except ValueError:
            pass
    return "day"


# Function interface for Orchestrator tool calling
async def tavily_web_search(
    query: str,
    search_depth: str = "basic",
    topic: str = "general",
    time_range: Optional[str] = None,
    max_results: int = 5,
    # Legacy parameter — kept for backward compatibility
    recency_days: Optional[int] = None,
    days: Optional[int] = None,
    **kwargs,  # Absorb any extra params from Orchestrator
) -> str:
    """
    Search the web using Tavily AI search engine.

    Use this tool to find:
    - Latest news and market information
    - Company announcements and financial reports
    - Stock analysis and recommendations
    - Economic indicators and trends

    Args:
        query: Search query (should be specific and in Vietnamese for VN stocks)
        search_depth: "basic" (balanced), "advanced" (detailed), "fast" (quick)
        topic: "general", "news" (real-time updates), "finance" (financial data)
        time_range: "day", "week", "month", "year" — filter by recency
        max_results: Number of results (1-10 recommended)
        recency_days: (Legacy) Filter by recent days — auto-converted to time_range

    Returns:
        Formatted search results with summaries and sources
    """
    # Normalize parameters to match Tavily API spec
    search_depth = _normalize_search_depth(search_depth)
    topic = _normalize_topic(topic)

    # Handle legacy days parameter → time_range
    if time_range is None and (recency_days or days):
        time_range = _normalize_time_range(recency_days or days)
    elif time_range is not None:
        time_range = _normalize_time_range(time_range)

    try:
        response = await tavily_tool.search(
            query=query,
            search_depth=search_depth,
            topic=topic,
            time_range=time_range,
            max_results=max_results,
            include_answer=True,
        )
        return tavily_tool.format_results_for_llm(response)
    except Exception as e:
        return f"Lỗi khi tìm kiếm web: {str(e)}"
