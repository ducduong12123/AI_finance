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


# ============================================
# SSE Event Formatter (OpenAPI Spec Compliant)
# ============================================

# Map internal stage names to OpenAPI event types
STAGE_TO_EVENT_TYPE = {
    "start": "START",
    "iteration_start": "START",
    "planning": "PLANNING",
    "plan_created": "PLAN_CREATED",
    "critic_review": "CRITIC_REVIEWED",
    "plan_reviewed": "CRITIC_REVIEWED",
    "executing": "TOOL_EXECUTING",
    "tools_completed": "TOOL_COMPLETED",
    "synthesizing": "SYNTHESIZING",
    "response_ready": "SYNTHESIZING",
    "result_review": "CRITIC_REVIEWED",
    "result_reviewed": "CRITIC_REVIEWED",
    "completed": "FINAL_RESULT",
    "final_result": "FINAL_RESULT",
    "error": "ERROR",
    "timeout": "ERROR",
    "plan_rejected": "CRITIC_REVIEWED",
    "iterating": "PLANNING",
}

# Total steps in the workflow
TOTAL_WORKFLOW_STEPS = 6


def format_sse_event(
    stage: str, data: dict, iteration: int, execution_start: float
) -> dict:
    """
    Format event to match OpenAPI spec:
    {
        "eventType": "START",
        "payload": {...},
        "metadata": {
            "iteration": 1,
            "timestamp": "2026-02-12T07:20:36.104Z",
            "executionTime": 0
        },
        "progress": {
            "currentStep": 1,
            "totalSteps": 6,
            "percentComplete": 0
        }
    }
    """
    event_type = STAGE_TO_EVENT_TYPE.get(stage, stage.upper())
    execution_time = (time.time() - execution_start) * 1000  # Convert to ms

    # Calculate progress
    progress_map = {
        "START": {
            "currentStep": 1,
            "totalSteps": TOTAL_WORKFLOW_STEPS,
            "percentComplete": 0,
        },
        "PLANNING": {
            "currentStep": 2,
            "totalSteps": TOTAL_WORKFLOW_STEPS,
            "percentComplete": 16,
        },
        "PLAN_CREATED": {
            "currentStep": 2,
            "totalSteps": TOTAL_WORKFLOW_STEPS,
            "percentComplete": 33,
        },
        "CRITIC_REVIEWED": {
            "currentStep": 3,
            "totalSteps": TOTAL_WORKFLOW_STEPS,
            "percentComplete": 50,
        },
        "TOOL_EXECUTING": {
            "currentStep": 4,
            "totalSteps": TOTAL_WORKFLOW_STEPS,
            "percentComplete": 66,
        },
        "TOOL_COMPLETED": {
            "currentStep": 4,
            "totalSteps": TOTAL_WORKFLOW_STEPS,
            "percentComplete": 66,
        },
        "SYNTHESIZING": {
            "currentStep": 5,
            "totalSteps": TOTAL_WORKFLOW_STEPS,
            "percentComplete": 83,
        },
        "FINAL_RESULT": {
            "currentStep": 6,
            "totalSteps": TOTAL_WORKFLOW_STEPS,
            "percentComplete": 100,
        },
        "ERROR": {
            "currentStep": 6,
            "totalSteps": TOTAL_WORKFLOW_STEPS,
            "percentComplete": 100,
        },
    }

    progress = progress_map.get(
        event_type,
        {"currentStep": 1, "totalSteps": TOTAL_WORKFLOW_STEPS, "percentComplete": 0},
    )

    # Format payload based on event type
    payload = _format_payload(stage, data, event_type)

    return {
        "eventType": event_type,
        "payload": payload,
        "metadata": {
            "iteration": iteration,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "executionTime": round(execution_time, 2),
        },
        "progress": progress,
    }


def _format_payload(stage: str, data: dict, event_type: str) -> dict:
    """Format payload based on stage and event type."""

    if event_type == "START":
        return {"query": data.get("query", "")}

    elif event_type == "PLANNING":
        return {"message": data.get("message", "Đang lập kế hoạch...")}

    elif event_type == "PLAN_CREATED":
        return {"plan": data.get("plan", {})}

    elif event_type == "CRITIC_REVIEWED":
        # Can be either plan review or result review
        if "review" in data:
            return data["review"]
        elif "message" in data:
            return {
                "approved": True,
                "score": 0,
                "reasoning": data["message"],
                "concerns": [],
                "suggestions": [],
                "requiresChanges": False,
                "iterationFeedback": None,
            }
        return data

    elif event_type == "TOOL_EXECUTING":
        if "tool_name" in data:
            return {
                "toolName": data["tool_name"],
                "parameters": data.get("parameters", {}),
            }
        return {
            "message": data.get("message", "Đang thực thi các công cụ..."),
        }

    elif event_type == "TOOL_COMPLETED":
        if "tool_name" in data:
            return {
                "toolName": data["tool_name"],
                "success": data.get("success", True),
                "executionTime": data.get("execution_time", 0),
                "result": data.get("result", ""),
            }
        # Batch tool completion
        success_count = (
            data.get("successCount")
            if data.get("successCount") is not None
            else data.get("results", 0)
        )
        total_count = data.get("total", success_count)
        return {
            "message": data.get("message", "Hoàn thành thực thi công cụ"),
            "count": success_count,
            "total": total_count,
            "success": True,
        }

    elif event_type == "SYNTHESIZING":
        return {"message": data.get("message", "Đang tổng hợp kết quả...")}

    elif event_type == "FINAL_RESULT":
        return data  # Full result data

    elif event_type == "ERROR":
        return {
            "code": data.get("code", "UNKNOWN_ERROR"),
            "message": data.get("error", data.get("message", "Đã xảy ra lỗi")),
            "details": data.get("details", {}),
        }

    return data


import time


@router.post("/query/stream")
async def agent_query_stream(request: AgentQueryRequest):
    """
    Stream agent execution progress.

    Returns Server-Sent Events (SSE) matching OpenAPI spec:
    - START - Workflow bắt đầu
    - PLANNING - Orchestrator đang phân tích
    - PLAN_CREATED - Plan được tạo
    - CRITIC_REVIEWED - Critic đánh giá plan
    - TOOL_EXECUTING - Đang chạy tools
    - TOOL_COMPLETED - Tools hoàn thành
    - SYNTHESIZING - Đang tổng hợp kết quả
    - FINAL_RESULT - Kết quả cuối cùng

    Format (per OpenAPI spec):
    {
        "eventType": "START",
        "payload": {...},
        "metadata": {...},
        "progress": {...}
    }
    """
    from fastapi.responses import StreamingResponse

    async def event_stream():
        progress_queue = asyncio.Queue()
        execution_start = time.time()
        current_iteration = 1

        def progress_callback(stage: str, data: dict):
            # Map to OpenAPI format
            asyncio.create_task(
                progress_queue.put(
                    {
                        "stage": stage,
                        "data": data,
                        "iteration": current_iteration,
                        "execution_start": execution_start,
                    }
                )
            )

        # Run agent loop in background
        async def run_agent():
            nonlocal current_iteration
            try:
                result = await agent_loop.execute(
                    user_query=request.query,
                    session_id=request.session_id,
                    progress_callback=progress_callback,
                )

                # Format final result to match OpenAPI AgentQueryResponse
                await progress_queue.put(
                    {
                        "stage": "final_result",
                        "data": {
                            "success": result.success,
                            "query": result.query,
                            "answer": result.final_answer,
                            "iterations": result.iterations,
                            "executionTime": result.execution_time,
                            "planSummary": {
                                "intent": result.plan.interpreted_intent,
                                "toolsPlanned": [
                                    t.tool_name for t in result.plan.tools
                                ],
                                "canParallel": result.plan.can_parallel,
                            },
                            "toolExecutions": [
                                {
                                    "tool": r.tool_name,
                                    "success": r.success,
                                    "executionTime": r.execution_time,
                                }
                                for r in result.tool_results
                            ],
                            "criticReviews": result.critic_reviews,
                            "metrics": result.metrics,
                        },
                        "iteration": result.iterations,
                        "execution_start": execution_start,
                    }
                )
            except Exception as e:
                await progress_queue.put(
                    {
                        "stage": "error",
                        "data": {
                            "code": "AGENT_ERROR",
                            "message": str(e),
                        },
                        "iteration": current_iteration,
                        "execution_start": execution_start,
                    }
                )

        # Start agent execution
        agent_task = asyncio.create_task(run_agent())

        # Stream progress in OpenAPI format
        while True:
            try:
                # Wait for progress update with timeout
                update = await asyncio.wait_for(progress_queue.get(), timeout=60.0)

                stage = update["stage"]
                data = update["data"]
                iteration = update.get("iteration", 1)
                exec_start = update.get("execution_start", execution_start)

                # Track iteration for loop
                if stage == "iteration_start":
                    current_iteration = data.get("iteration", 1)

                # Format to OpenAPI spec
                sse_event = format_sse_event(stage, data, iteration, exec_start)

                # Format as SSE
                event_data = json.dumps(sse_event, default=str, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

                # Check if final result or error
                if stage in ("final_result", "error", "timeout"):
                    break

            except asyncio.TimeoutError:
                # Send timeout event in OpenAPI format
                timeout_event = {
                    "eventType": "ERROR",
                    "payload": {
                        "code": "TIMEOUT",
                        "message": "Execution timeout after 60 seconds",
                    },
                    "metadata": {
                        "iteration": current_iteration,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "executionTime": (time.time() - execution_start) * 1000,
                    },
                    "progress": {
                        "currentStep": TOTAL_WORKFLOW_STEPS,
                        "totalSteps": TOTAL_WORKFLOW_STEPS,
                        "percentComplete": 100,
                    },
                }
                yield f"data: {json.dumps(timeout_event, default=str)}\n\n"
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
