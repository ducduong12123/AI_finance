"""
Agent Loop - Multi-Agent Orchestration Workflow.

Coordinates the full workflow:
User Query -> Orchestrator (Plan) -> Critic (Review) -> Tool Execution ->
Critic (Review Results) -> [Iterate if needed] -> Final Response
"""

import asyncio
import time
from typing import Optional, Callable
from datetime import datetime
from pydantic import BaseModel, Field

from agents.orchestrator import (
    OrchestratorAgent,
    OrchestratorResponse,
    OrchestratorPlan,
    QueryType,
)
from agents.critic import CriticAgent, CriticReview
from agents.state.manager import StateManager, AgentState, AgentStage
from core.config import settings


class AgentLoopConfig(BaseModel):
    """Configuration for agent loop."""

    max_iterations: int = Field(default=3, ge=1, le=10)
    require_critic_approval: bool = Field(default=True)
    parallel_tool_execution: bool = Field(default=True)
    timeout_seconds: float = Field(default=60.0)


class AgentLoopResult(BaseModel):
    """Result from agent loop execution."""

    model_config = {"populate_by_name": True}

    success: bool = Field(...)
    query: str = Field(...)
    final_answer: str = Field(...)
    iterations: int = Field(...)
    execution_time: float = Field(...)
    plan: OrchestratorPlan = Field(...)
    tool_results: list = Field(default_factory=list)
    critic_reviews: list = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)
    error: Optional[str] = Field(default=None)


class AgentLoop:
    """
    Agent Loop - Dieu phoi multi-agent workflow.
    """

    def __init__(
        self,
        orchestrator: Optional[OrchestratorAgent] = None,
        critic: Optional[CriticAgent] = None,
        state_manager: Optional[StateManager] = None,
        config: Optional[AgentLoopConfig] = None,
    ):
        self.orchestrator = orchestrator or OrchestratorAgent()
        self.critic = critic or CriticAgent()
        self.state_manager = state_manager or StateManager()
        self.config = config or AgentLoopConfig()

    async def execute(
        self,
        user_query: str,
        session_id: Optional[str] = None,
        progress_callback: Optional[Callable[[str, dict], None]] = None,
    ) -> AgentLoopResult:
        """Execute with smart routing - simple queries bypass Critic."""
        start_time = time.time()

        def notify(stage: str, data: dict):
            if progress_callback:
                progress_callback(stage, data)

        notify("start", {"query": user_query})

        # Step 0: Classify query
        query_type = self.orchestrator.classify_query(user_query)
        notify(
            "query_classified",
            {"type": query_type.value, "needs_critic": query_type == QueryType.COMPLEX},
        )

        # Route to appropriate handler
        if query_type == QueryType.SIMPLE:
            notify("simple_mode", {"message": "Query đơn giản - thực thi trực tiếp"})
            return await self._execute_simple(
                user_query, session_id, notify, start_time
            )
        else:
            notify("complex_mode", {"message": "Query phức tạp - dùng full pipeline"})
            return await self._execute_complex(
                user_query, session_id, notify, start_time
            )

    async def _execute_simple(
        self,
        user_query: str,
        session_id: Optional[str],
        notify: Callable,
        start_time: float,
    ) -> AgentLoopResult:
        """Execute simple query without Critic - FAST PATH."""
        if session_id:
            await self.state_manager.update_state(
                session_id,
                stage=AgentStage.EXECUTING,
                context={"query": user_query, "mode": "simple"},
            )

        try:
            # Create plan directly (no LLM)
            notify("planning", {"message": "Tạo kế hoạch nhanh..."})
            plan = self.orchestrator.create_simple_plan(user_query)
            notify("plan_created", {"plan": plan.model_dump(), "mode": "simple"})

            # Execute tools
            # Execute tools
            notify("executing", {"message": f"Thực thi {len(plan.tools)} công cụ..."})
            tool_results = await self.orchestrator.execute_tools(plan)
            success_count = sum(1 for r in tool_results if r.success)
            failed_count = len(tool_results) - success_count
            notify(
                "tools_completed",
                {
                    "results": success_count,
                    "total": len(tool_results),
                    "successCount": success_count,
                    "failed": failed_count,
                },
            )

            if session_id:
                await self.state_manager.update_state(
                    session_id, stage=AgentStage.ANALYZING
                )

            # Synthesize
            notify("synthesizing", {"message": "Tổng hợp kết quả..."})
            response = await self.orchestrator.synthesize_response(plan, tool_results)

            execution_time = time.time() - start_time
            orch_tokens = self.orchestrator.get_token_usage()

            if session_id:
                await self.state_manager.update_state(
                    session_id,
                    stage=AgentStage.FINALIZING,
                    context={
                        "iterations": 1,
                        "final_answer": response.synthesized_answer,
                    },
                )

            notify(
                "completed",
                {
                    "message": "Hoàn thành!",
                    "metrics": {
                        "latency_ms": round(execution_time * 1000, 2),
                        "tokens": orch_tokens["total"],
                        "mode": "simple",
                        "iterations": 1,
                    },
                },
            )

            return AgentLoopResult(
                success=response.success,
                query=user_query,
                final_answer=response.synthesized_answer,
                iterations=1,
                execution_time=execution_time,
                plan=plan,
                tool_results=tool_results,
                critic_reviews=[],  # No critic for simple queries
                metrics={
                    "latency_ms": round(execution_time * 1000, 2),
                    "tokens": orch_tokens["total"],
                    "mode": "simple",
                    "iterations": 1,
                },
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return AgentLoopResult(
                success=False,
                query=user_query,
                final_answer=f"Lỗi: {str(e)}",
                iterations=1,
                execution_time=execution_time,
                plan=OrchestratorPlan(
                    original_query=user_query,
                    interpreted_intent="Lỗi",
                    tools=[],
                    expected_outcome="Không có",
                    query_type=QueryType.SIMPLE,
                ),
                tool_results=[],
                critic_reviews=[],
                error=str(e),
            )

    async def _execute_complex(
        self,
        user_query: str,
        session_id: Optional[str],
        notify: Callable,
        start_time: float,
    ) -> AgentLoopResult:
        """Execute complex query with full Critic pipeline."""
        if session_id:
            await self.state_manager.update_state(
                session_id,
                stage=AgentStage.PLANNING,
                context={"query": user_query, "iterations": [], "mode": "complex"},
            )

        current_iteration = 0
        final_response: Optional[OrchestratorResponse] = None
        response: Optional[OrchestratorResponse] = None
        plan: Optional[OrchestratorPlan] = None
        all_critic_reviews: list[CriticReview] = []

        try:
            while current_iteration < self.config.max_iterations:
                current_iteration += 1
                notify("iteration_start", {"iteration": current_iteration})

                # Step 1: Orchestrator creates plan
                notify(
                    "planning",
                    {"message": "Orchestrator đang phân tích và lập kế hoạch..."},
                )
                plan = await self.orchestrator.create_plan(user_query)
                plan.query_type = QueryType.COMPLEX  # Mark as complex
                notify("plan_created", {"plan": plan.model_dump(), "mode": "complex"})

                if session_id:
                    await self.state_manager.update_state(
                        session_id, stage=AgentStage.EXECUTING
                    )

                tool_results = await self.orchestrator.execute_tools(plan)
                success_count = sum(1 for r in tool_results if r.success)
                notify(
                    "tools_completed",
                    {
                        "results": success_count,  # For backward compatibility with frontend
                        "total": len(tool_results),
                        "success": success_count,
                        "failed": len(tool_results) - success_count,
                        "message": f"✓ {success_count}/{len(tool_results)} tool(s) completed successfully",
                    },
                )

                # Step 3: Synthesize response
                notify("synthesizing", {"message": "Tổng hợp kết quả..."})

                if session_id:
                    await self.state_manager.update_state(
                        session_id, stage=AgentStage.ANALYZING
                    )

                response = await self.orchestrator.synthesize_response(
                    plan, tool_results
                )
                notify("response_ready", {"needs_iteration": response.needs_iteration})

                # Step 4: Critic reviews results (chỉ review kết quả, không review plan)
                notify("result_review", {"message": "Critic đang đánh giá kết quả..."})
                result_review = await self.critic.review_results(plan, tool_results)
                all_critic_reviews.append(result_review)
                notify(
                    "result_reviewed",
                    {
                        "review": result_review.model_dump(),
                        "score": result_review.score,
                        "approved": result_review.approved,
                    },
                )

                # Check result based on Critic scoring (0-5)
                if result_review.approved:
                    final_response = response

                    # Handle needs_clarification (score 3-5)
                    if (
                        result_review.needs_clarification
                        and result_review.clarification_questions
                    ):
                        notify(
                            "needs_clarification",
                            {
                                "message": "Kết quả đạt, nhưng có thể hỏi thêm ngưởi dùng",
                                "questions": result_review.clarification_questions,
                            },
                        )

                    # Compute final metrics
                    orch_tokens = self.orchestrator.get_token_usage()
                    critic_tokens = self.critic.get_token_usage()
                    avg_score = (
                        sum(r.score for r in all_critic_reviews)
                        / len(all_critic_reviews)
                        if all_critic_reviews
                        else 0.0
                    )

                    notify(
                        "completed",
                        {
                            "message": "Hoàn thành!",
                            "metrics": {
                                "latency_ms": round(
                                    (time.time() - start_time) * 1000, 2
                                ),
                                "tokens": orch_tokens["total"] + critic_tokens["total"],
                                "accuracy": round(
                                    avg_score * 2, 1
                                ),  # Convert 0-5 to 0-10
                                "critic_score": result_review.score,
                                "needs_clarification": result_review.needs_clarification,
                            },
                        },
                    )
                    break

                # Score 0-2: Not approved, need iteration
                if current_iteration < self.config.max_iterations:
                    notify(
                        "iterating",
                        {
                            "reason": result_review.iteration_feedback
                            or response.iteration_reason,
                            "score": result_review.score,
                            "feedback": "Orchestrator cần lập lại plan",
                        },
                    )
                    user_query = f"Yêu cầu gốc: {user_query}\n\nIntent hiện tại: {plan.interpreted_intent}\n\nCritic phản hồi: {result_review.iteration_feedback}\n\nHãy điều chỉnh plan cho phù hợp."

            # If we exited loop without final_response, use last response
            if final_response is None and response is not None:
                final_response = response

            if final_response is None:
                default_plan = (
                    plan
                    if plan is not None
                    else OrchestratorPlan(
                        original_query=user_query,
                        interpreted_intent="Loi",
                        tools=[],
                        expected_outcome="Khong co",
                    )
                )
                return AgentLoopResult(
                    success=False,
                    query=user_query,
                    final_answer="Loi: Khong the tao phan hoi",
                    iterations=current_iteration,
                    execution_time=0.0,
                    plan=default_plan,
                    tool_results=[],
                    critic_reviews=[r.model_dump() for r in all_critic_reviews],
                )

            final_resp = final_response
            execution_time = time.time() - start_time

            if session_id:
                await self.state_manager.update_state(
                    session_id,
                    stage=AgentStage.FINALIZING,
                    context={
                        "iterations": current_iteration,
                        "final_answer": final_resp.synthesized_answer,
                    },
                )

            # Collect metrics
            orch_tokens = self.orchestrator.get_token_usage()
            critic_tokens = self.critic.get_token_usage()
            total_tokens = orch_tokens["total"] + critic_tokens["total"]

            # Calculate average accuracy if critic reviews exist
            avg_score = 0.0
            if all_critic_reviews:
                avg_score = sum(r.score for r in all_critic_reviews) / len(
                    all_critic_reviews
                )

            metrics = {
                "latency_ms": round(execution_time * 1000, 2),
                "tokens": total_tokens,
                "accuracy": round(avg_score * 10, 1),  # Scale to 0-100
            }

            return AgentLoopResult(
                success=final_resp.success,
                query=user_query,
                final_answer=final_resp.synthesized_answer,
                iterations=current_iteration,
                execution_time=execution_time,
                plan=final_resp.plan,
                tool_results=final_resp.tool_results,
                critic_reviews=[r.model_dump() for r in all_critic_reviews],
                metrics=metrics,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            default_plan = (
                plan
                if plan is not None
                else OrchestratorPlan(
                    original_query=user_query,
                    interpreted_intent="Lỗi",
                    tools=[],
                    expected_outcome="Không có",
                )
            )
            return AgentLoopResult(
                success=False,
                query=user_query,
                final_answer=f"Lỗi: {str(e)}",
                iterations=current_iteration,
                execution_time=execution_time,
                plan=default_plan,
                tool_results=[],
                critic_reviews=[r.model_dump() for r in all_critic_reviews]
                if all_critic_reviews
                else [],
                error=str(e),
            )
