"""
Tavily Web Search Tool.

Integration with Tavily API for AI-optimized web search.
Tavily provides search results specifically formatted for LLM consumption.
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
        default=None, description="AI-generated answer if include_answer=True"
    )
    total_results: int = Field(default=0)
    search_time: float = Field(default=0.0, description="Search time in seconds")


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
        search_depth: str = "basic",  # "basic" or "comprehensive"
        max_results: int = 5,
        include_answer: bool = True,
        include_raw_content: bool = False,
        days: Optional[int] = None,  # Filter by recency (e.g., 7 for last week)
    ) -> TavilySearchResponse:
        """
        Execute web search using Tavily API.

        Args:
            query: Search query
            search_depth: "basic" (fast) or "comprehensive" (thorough)
            max_results: Number of results (1-20)
            include_answer: Include AI-generated answer
            include_raw_content: Include full page content
            days: Filter results by days (e.g., 7 for last week)

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
                "max_results": max_results,
                "include_answer": include_answer,
                "include_raw_content": include_raw_content,
            }

            if days:
                payload["days"] = days

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


# Function interface for Gemini tool calling
async def tavily_web_search(
    query: str,
    search_depth: str = "basic",
    max_results: int = 5,
    recency_days: Optional[int] = None,
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
        search_depth: "basic" for quick results, "comprehensive" for detailed analysis
        max_results: Number of results (1-10 recommended)
        recency_days: Filter by recent days (e.g., 7 for last week, 30 for last month)

    Returns:
        Formatted search results with summaries and sources
    """
    try:
        response = await tavily_tool.search(
            query=query,
            search_depth=search_depth,
            max_results=max_results,
            include_answer=True,
            days=recency_days,
        )
        return tavily_tool.format_results_for_llm(response)
    except Exception as e:
        return f"Lỗi khi tìm kiếm web: {str(e)}"
