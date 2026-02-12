"""
Multi-Agent API Routes.

Provides endpoints for the multi-agent orchestration system with:
- Orchestrator Agent (planning & distribution)
- Critic Agent (reflection & validation)
- Tool Execution (Tavily web search + VNStock)
"""

import json
import asyncio
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from agents.agent_loop import AgentLoop, AgentLoopResult
from api.schemas.shared import (
    ApiResponse,
    create_success_response,
    create_error_response,
)

router = APIRouter(prefix="/agent", tags=["multi-agent"])


# ============================================
# Request/Response Models
# ============================================


class AgentQueryRequest(BaseModel):
    """Request for multi-agent query."""

    query: str = Field(..., min_length=1, description="User's natural language query")
    session_id: Optional[str] = Field(
        default=None, description="Session ID for state persistence"
    )
    max_iterations: int = Field(
        default=3, ge=1, le=5, description="Maximum agent iterations"
    )
    stream_progress: bool = Field(
        default=False, description="Whether to stream progress updates"
    )


class AgentProgressUpdate(BaseModel):
    """Progress update during agent execution."""

    stage: str = Field(..., description="Current stage")
    message: str = Field(..., description="Status message")
    iteration: Optional[int] = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentQueryResponse(BaseModel):
    """Response from multi-agent query."""

    success: bool = Field(...)
    query: str = Field(...)
    answer: str = Field(..., description="Final synthesized answer")
    iterations: int = Field(..., description="Number of iterations executed")
    execution_time: float = Field(..., description="Total execution time in seconds")
    plan_summary: dict = Field(
        default_factory=dict, description="Summary of execution plan"
    )
    tool_executions: list = Field(
        default_factory=list, description="Tools that were executed"
    )
    critic_reviews: list = Field(default_factory=list, description="Critic reviews")


# ============================================
# Agent Loop Instance
# ============================================

agent_loop = AgentLoop()


# ============================================
# API Endpoints
# ============================================


@router.post("/query", response_model=AgentQueryResponse)
async def agent_query(request: AgentQueryRequest):
    """
    Execute multi-agent query with full orchestration.

    Workflow:
    1. Orchestrator analyzes query and creates plan
    2. Critic reviews and approves/rejects plan
    3. Tools are executed (Tavily, VNStock)
    4. Critic reviews results
    5. Final answer synthesized
    6. If needed, loop back to step 1 (max 3 iterations)

    Example queries:
    - "Cổ phiếu VCB hôm nay thế nào?"
    - "Tin tức mới nhất về thị trường chứng khoán VN"
    - "So sánh VNM và VCB"
    """
    try:
        # Configure agent loop
        agent_loop.config.max_iterations = request.max_iterations

        # Execute agent loop
        result = await agent_loop.execute(
            user_query=request.query,
            session_id=request.session_id,
        )

        # Format response
        return AgentQueryResponse(
            success=result.success,
            query=result.query,
            answer=result.final_answer,
            iterations=result.iterations,
            execution_time=result.execution_time,
            plan_summary={
                "intent": result.plan.interpreted_intent,
                "tools_planned": [t.tool_name for t in result.plan.tools],
                "can_parallel": result.plan.can_parallel,
            },
            tool_executions=[
                {
                    "tool": r.tool_name,
                    "success": r.success,
                    "execution_time": r.execution_time,
                }
                for r in result.tool_results
            ],
            critic_reviews=result.critic_reviews,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")


@router.post("/query/stream")
async def agent_query_stream(request: AgentQueryRequest):
    """
    Stream agent execution progress.

    Returns Server-Sent Events (SSE) with progress updates:
    - iteration_start
    - planning
    - critic_review
    - executing
    - response_ready
    - completed
    """
    from fastapi.responses import StreamingResponse

    async def event_stream():
        progress_queue = asyncio.Queue()

        def progress_callback(stage: str, data: dict):
            asyncio.create_task(
                progress_queue.put(
                    {
                        "stage": stage,
                        "data": data,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            )

        # Run agent loop in background
        async def run_agent():
            result = await agent_loop.execute(
                user_query=request.query,
                session_id=request.session_id,
                progress_callback=progress_callback,
            )
            await progress_queue.put(
                {"stage": "final_result", "data": result.model_dump()}
            )

        # Start agent execution
        agent_task = asyncio.create_task(run_agent())

        # Stream progress
        while True:
            try:
                # Wait for progress update with timeout
                update = await asyncio.wait_for(progress_queue.get(), timeout=60.0)

                # Format as SSE
                event_data = json.dumps(update, default=str)
                yield f"data: {event_data}\n\n"

                # Check if final result
                if update["stage"] == "final_result":
                    break

            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'stage': 'timeout', 'error': 'Execution timeout'})}\n\n"
                break

        # Ensure agent task completes
        if not agent_task.done():
            agent_task.cancel()
            try:
                await agent_task
            except asyncio.CancelledError:
                pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/tools")
async def list_available_tools():
    """
    List all available tools for the multi-agent system.

    Returns information about:
    - tavily_web_search
    - vnstock_get_quote
    - vnstock_get_company_info
    - vnstock_get_historical
    """
    return {
        "success": True,
        "tools": [
            {
                "name": "tavily_web_search",
                "description": "Tìm kiếm thông tin trên web với Tavily AI search",
                "parameters": {
                    "query": "str - Câu truy vấn tìm kiếm",
                    "search_depth": "str - 'basic' hoặc 'comprehensive'",
                    "max_results": "int - Số kết quả (1-20)",
                    "recency_days": "int - Lọc theo số ngày gần đây",
                },
                "use_cases": [
                    "Tìm tin tức mới nhất",
                    "Phân tích thị trường",
                    "Thông tin công ty",
                ],
            },
            {
                "name": "vnstock_get_quote",
                "description": "Lấy giá cổ phiếu VN hiện tại",
                "parameters": {
                    "symbol": "str - Mã cổ phiếu (VD: VCB, VNM)",
                },
                "use_cases": [
                    "Giá real-time",
                    "Khối lượng giao dịch",
                    "Thay đổi giá",
                ],
            },
            {
                "name": "vnstock_get_company_info",
                "description": "Lấy thông tin công ty và chỉ số tài chính",
                "parameters": {
                    "symbol": "str - Mã cổ phiếu",
                },
                "use_cases": [
                    "Thông tin cơ bản",
                    "P/E, P/B ratios",
                    "Vốn hóa thị trường",
                ],
            },
            {
                "name": "vnstock_get_historical",
                "description": "Lấy dữ liệu lịch sử giá",
                "parameters": {
                    "symbol": "str - Mã cổ phiếu",
                    "days": "int - Số ngày (default: 30)",
                },
                "use_cases": [
                    "Phân tích xu hướng",
                    "Tính toán returns",
                    "Biểu đồ giá",
                ],
            },
        ],
    }


# ============================================
# Debug/Testing Endpoints
# ============================================


@router.post("/test/orchestrator")
async def test_orchestrator(query: str):
    """
    Test orchestrator plan generation only.

    Returns the execution plan without actually executing tools.
    """
    from agents.orchestrator import orchestrator

    try:
        plan = await orchestrator.create_plan(query)
        return {
            "success": True,
            "plan": plan.model_dump(),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@router.post("/test/critic")
async def test_critic(query: str):
    """
    Test critic review.

    Creates a plan and has critic review it.
    """
    from agents.orchestrator import orchestrator
    from agents.critic import critic

    try:
        plan = await orchestrator.create_plan(query)
        review = await critic.review_plan(plan)

        return {
            "success": True,
            "plan": plan.model_dump(),
            "critic_review": review.model_dump(),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
