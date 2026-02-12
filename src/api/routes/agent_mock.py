"""
Mock Agent API Routes - For FE Development & Integration Testing.

Agent 3 (Integration) sử dụng endpoints này để:
1. Test mà không cần BE chạy thật
2. Verify data format
3. Test error scenarios
"""

import json
import asyncio
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/mock/agent", tags=["mock"])


# ============================================
# Mock Data
# ============================================

MOCK_AGENT_RESPONSE = {
    "success": True,
    "query": "Giá cổ phiếu VCB hôm nay",
    "answer": """## 📈 Thông tin cổ phiếu VCB (Vietcombank)

**Giá hiện tại:** 95,500 VND (+1.2%)
**Thay đổi:** +1,100 VND
**Khối lượng giao dịch:** 2.5M cổ phiếu

**Thông số kỹ thuật:**
- P/E: 12.5
- P/B: 1.8  
- Vốn hóa: 180,000 tỷ VND

**Nhận định:**
VCB đang trong xu hướng tăng ngắn hạn, được hỗ trợ bởi kết quả kinh doanh quý 4 khả quan.
""",
    "iterations": 1,
    "executionTime": 3.45,
    "planSummary": {
        "intent": "User wants current price and analysis of VCB stock",
        "toolsPlanned": ["vnstock_get_quote", "tavily_web_search"],
        "canParallel": True,
    },
    "toolExecutions": [
        {"tool": "vnstock_get_quote", "success": True, "executionTime": 0.82},
        {"tool": "tavily_web_search", "success": True, "executionTime": 1.23},
    ],
    "criticReviews": [
        {
            "approved": True,
            "score": 8.5,
            "reasoning": "Plan covers both real-time data and market analysis",
            "concerns": [],
            "suggestions": ["Could add historical comparison"],
            "requiresChanges": False,
            "iterationFeedback": None,
        }
    ],
    "meta": {
        "requestId": "mock-req-001",
        "timestamp": datetime.utcnow().isoformat(),
        "duration": 3450,
        "version": "v1",
    },
}

MOCK_EVENTS = [
    {
        "eventType": "START",
        "payload": {"query": "Giá cổ phiếu VCB hôm nay"},
        "metadata": {
            "iteration": 1,
            "timestamp": datetime.utcnow().isoformat(),
            "executionTime": 0,
        },
        "progress": {"currentStep": 1, "totalSteps": 6, "percentComplete": 0},
    },
    {
        "eventType": "PLANNING",
        "payload": {"message": "Orchestrator đang phân tích và lập kế hoạch..."},
        "metadata": {
            "iteration": 1,
            "timestamp": datetime.utcnow().isoformat(),
            "executionTime": 150,
        },
        "progress": {"currentStep": 2, "totalSteps": 6, "percentComplete": 16},
    },
    {
        "eventType": "PLAN_CREATED",
        "payload": {
            "plan": {
                "originalQuery": "Giá cổ phiếu VCB hôm nay",
                "interpretedIntent": "User wants current price and analysis of VCB stock",
                "tools": [
                    {
                        "toolName": "vnstock_get_quote",
                        "parameters": {"symbol": "VCB"},
                        "reason": "Get real-time stock price",
                        "priority": 1,
                    },
                    {
                        "toolName": "tavily_web_search",
                        "parameters": {
                            "query": "VCB Vietcombank phân tích",
                            "maxResults": 3,
                        },
                        "reason": "Get market analysis",
                        "priority": 2,
                    },
                ],
                "canParallel": True,
                "expectedOutcome": "Current price and market analysis of VCB",
            }
        },
        "metadata": {
            "iteration": 1,
            "timestamp": datetime.utcnow().isoformat(),
            "executionTime": 450,
        },
        "progress": {"currentStep": 2, "totalSteps": 6, "percentComplete": 33},
    },
    {
        "eventType": "CRITIC_REVIEWED",
        "payload": {
            "approved": True,
            "score": 8.5,
            "reasoning": "Plan covers both real-time data and market analysis",
            "concerns": [],
            "suggestions": ["Could add historical comparison"],
            "requiresChanges": False,
            "iterationFeedback": None,
        },
        "metadata": {
            "iteration": 1,
            "timestamp": datetime.utcnow().isoformat(),
            "executionTime": 650,
        },
        "progress": {"currentStep": 3, "totalSteps": 6, "percentComplete": 50},
    },
    {
        "eventType": "TOOL_EXECUTING",
        "payload": {"toolName": "vnstock_get_quote", "parameters": {"symbol": "VCB"}},
        "metadata": {
            "iteration": 1,
            "timestamp": datetime.utcnow().isoformat(),
            "executionTime": 800,
        },
        "progress": {"currentStep": 4, "totalSteps": 6, "percentComplete": 66},
    },
    {
        "eventType": "TOOL_COMPLETED",
        "payload": {
            "toolName": "vnstock_get_quote",
            "success": True,
            "executionTime": 0.82,
            "result": "VCB: 95,500 VND (+1.2%)",
        },
        "metadata": {
            "iteration": 1,
            "timestamp": datetime.utcnow().isoformat(),
            "executionTime": 1620,
        },
        "progress": {"currentStep": 4, "totalSteps": 6, "percentComplete": 66},
    },
    {
        "eventType": "TOOL_EXECUTING",
        "payload": {
            "toolName": "tavily_web_search",
            "parameters": {"query": "VCB Vietcombank phân tích", "maxResults": 3},
        },
        "metadata": {
            "iteration": 1,
            "timestamp": datetime.utcnow().isoformat(),
            "executionTime": 1700,
        },
        "progress": {"currentStep": 4, "totalSteps": 6, "percentComplete": 66},
    },
    {
        "eventType": "TOOL_COMPLETED",
        "payload": {
            "toolName": "tavily_web_search",
            "success": True,
            "executionTime": 1.23,
            "result": "Found 3 relevant articles about VCB",
        },
        "metadata": {
            "iteration": 1,
            "timestamp": datetime.utcnow().isoformat(),
            "executionTime": 2930,
        },
        "progress": {"currentStep": 4, "totalSteps": 6, "percentComplete": 66},
    },
    {
        "eventType": "SYNTHESIZING",
        "payload": {"message": "Tổng hợp kết quả..."},
        "metadata": {
            "iteration": 1,
            "timestamp": datetime.utcnow().isoformat(),
            "executionTime": 2950,
        },
        "progress": {"currentStep": 5, "totalSteps": 6, "percentComplete": 83},
    },
    {
        "eventType": "CRITIC_REVIEWED",
        "payload": {
            "approved": True,
            "score": 9.0,
            "reasoning": "Results are comprehensive and accurate",
            "concerns": [],
            "suggestions": [],
            "requiresChanges": False,
            "iterationFeedback": None,
        },
        "metadata": {
            "iteration": 1,
            "timestamp": datetime.utcnow().isoformat(),
            "executionTime": 3150,
        },
        "progress": {"currentStep": 5, "totalSteps": 6, "percentComplete": 83},
    },
    {
        "eventType": "FINAL_RESULT",
        "payload": MOCK_AGENT_RESPONSE,
        "metadata": {
            "iteration": 1,
            "timestamp": datetime.utcnow().isoformat(),
            "executionTime": 3450,
        },
        "progress": {"currentStep": 6, "totalSteps": 6, "percentComplete": 100},
    },
]


# ============================================
# Mock Endpoints
# ============================================


class MockQueryRequest(BaseModel):
    """Mock request - same as real."""

    query: str = Field(..., min_length=1)
    session_id: str | None = None
    max_iterations: int = Field(default=3, ge=1, le=5)


@router.post("/query")
async def mock_agent_query(request: MockQueryRequest):
    """
    Return mock response immediately (no LLM calls).

    Use this for:
    - FE development
    - Testing UI without consuming API quota
    - Agent 3 integration testing
    """
    return MOCK_AGENT_RESPONSE


@router.post("/query/stream")
async def mock_agent_stream(request: MockQueryRequest):
    """
    Stream mock events with realistic delays.

    Simulates the full agent workflow:
    - START -> PLANNING -> PLAN_CREATED -> ... -> FINAL_RESULT
    - Each event has proper timing
    - Total ~3-4 seconds
    """
    from fastapi.responses import StreamingResponse

    async def event_stream():
        for event in MOCK_EVENTS:
            # Simulate realistic delay between events
            if event["eventType"] == "PLANNING":
                await asyncio.sleep(0.2)
            elif event["eventType"] == "TOOL_EXECUTING":
                await asyncio.sleep(0.5)
            elif event["eventType"] == "SYNTHESIZING":
                await asyncio.sleep(0.3)

            data = json.dumps(event)
            yield f"data: {data}\n\n"

        # Small delay before closing
        await asyncio.sleep(0.1)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/tools")
async def mock_list_tools():
    """Return list of available tools."""
    return {
        "success": True,
        "tools": [
            {
                "name": "tavily_web_search",
                "description": "Tìm kiếm thông tin trên web với Tavily AI",
                "parameters": {
                    "query": {"type": "string", "required": True},
                    "max_results": {"type": "integer", "default": 5},
                    "search_depth": {
                        "type": "string",
                        "enum": ["basic", "comprehensive"],
                    },
                    "recency_days": {"type": "integer", "optional": True},
                },
                "useCases": [
                    "Tìm tin tức mới nhất",
                    "Phân tích thị trường",
                    "Thông tin công ty",
                ],
            },
            {
                "name": "vnstock_get_quote",
                "description": "Lấy giá cổ phiếu VN hiện tại",
                "parameters": {
                    "symbol": {"type": "string", "required": True, "example": "VCB"}
                },
                "useCases": ["Giá real-time", "Khối lượng giao dịch", "Thay đổi giá"],
            },
            {
                "name": "vnstock_get_company_info",
                "description": "Lấy thông tin công ty và chỉ số tài chính",
                "parameters": {"symbol": {"type": "string", "required": True}},
                "useCases": [
                    "Thông tin cơ bản",
                    "P/E, P/B ratios",
                    "Vốn hóa thị trường",
                ],
            },
        ],
    }


@router.post("/query/error")
async def mock_error_response():
    """
    Return error response for testing error handling.

    Use this to test:
    - Error UI display
    - Retry logic
    - User notifications
    """
    return {
        "success": False,
        "query": "Test query",
        "answer": "",
        "iterations": 0,
        "executionTime": 0.0,
        "planSummary": {},
        "toolExecutions": [],
        "criticReviews": [],
        "error": {
            "code": "AGENT_TIMEOUT",
            "message": "Agent execution exceeded 60 seconds",
            "details": {"timeout": 60, "elapsed": 60.5},
        },
        "meta": {
            "requestId": "mock-error-001",
            "timestamp": datetime.utcnow().isoformat(),
            "duration": 60500,
            "version": "v1",
        },
    }


@router.post("/query/stream/error")
async def mock_stream_error():
    """
    Stream that fails mid-way.

    Use this to test:
    - SSE error handling
    - Connection recovery
    - Partial data display
    """
    from fastapi.responses import StreamingResponse

    async def error_stream():
        # Send first few events normally
        for event in MOCK_EVENTS[:5]:
            data = json.dumps(event)
            yield f"data: {data}\n\n"
            await asyncio.sleep(0.2)

        # Then send error
        error_event = {
            "eventType": "ERROR",
            "payload": {
                "code": "TOOL_EXECUTION_FAILED",
                "message": "Failed to execute vnstock_get_quote",
                "details": {"tool": "vnstock_get_quote", "error": "Connection timeout"},
            },
            "metadata": {
                "iteration": 1,
                "timestamp": datetime.utcnow().isoformat(),
                "executionTime": 2500,
            },
            "progress": {"currentStep": 4, "totalSteps": 6, "percentComplete": 66},
        }
        yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        error_stream(),
        media_type="text/event-stream",
    )
