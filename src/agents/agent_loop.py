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
        """Execute full agent loop."""
        start_time = time.time()

        if session_id:
            await self.state_manager.update_state(
                session_id,
                stage=AgentStage.PLANNING,
                context={"query": user_query, "iterations": []},
            )

        def notify(stage: str, data: dict):
            if progress_callback:
                progress_callback(stage, data)

        notify("start", {"query": user_query})

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
                notify("planning", {"message": "Orchestrator dang phan tich va lap ke hoach..."})
                plan = await self.orchestrator.create_plan(user_query)
                notify("plan_created", {"plan": plan.model_dump()})

                # Step 2: Critic reviews plan
                if self.config.require_critic_approval:
                    notify("critic_review", {"message": "Critic dang danh gia ke hoach..."})
                    plan_review = await self.critic.review_plan(plan)
                    all_critic_reviews.append(plan_review)
                    notify("plan_reviewed", {"review": plan_review.model_dump()})

                    if not plan_review.approved and plan_review.requires_changes:
                        notify("plan_rejected", {
                            "reason": plan_review.reasoning,
                            "feedback": plan_review.iteration_feedback,
                        })
                        user_query = f"Yeu cau goc: {user_query}\n\nKe hoach truoc chua dat. Phan hoi: {plan_review.iteration_feedback}\n\nHay tao ke hoach moi tot hon."
                        continue

                # Step 3: Execute tools
                notify("executing", {"message": f"Thuc thi {len(plan.tools)} tools..."})

                if session_id:
                    await self.state_manager.update_state(session_id, stage=AgentStage.EXECUTING)

                tool_results = await self.orchestrator.execute_tools(plan)
                notify("tools_completed", {"results": len(tool_results)})

                # Step 4: Synthesize response
                notify("synthesizing", {"message": "Tong hop ket qua..."})

                if session_id:
                    await self.state_manager.update_state(session_id, stage=AgentStage.ANALYZING)

                response = await self.orchestrator.synthesize_response(plan, tool_results)
                notify("response_ready", {"needs_iteration": response.needs_iteration})

                # Step 5: Critic reviews results
                notify("result_review", {"message": "Critic dang danh gia ket qua..."})
                result_review = await self.critic.review_results(plan, tool_results)
                all_critic_reviews.append(result_review)
                notify("result_reviewed", {"review": result_review.model_dump()})

                # Check if we need another iteration
                if result_review.approved and not response.needs_iteration:
                    final_response = response
                    notify("completed", {"message": "Hoan thanh!"})
                    break

                if current_iteration < self.config.max_iterations:
                    notify("iterating", {
                        "reason": result_review.iteration_feedback or response.iteration_reason,
                    })
                    user_query = f"Yeu cau goc: {user_query}\n\nKet qua chua dat yeu cau. Phan hoi: {result_review.iteration_feedback or response.iteration_reason}\n\nHay thu cach tiep can khac."

            # If we exited loop without final_response, use last response
            if final_response is None and response is not None:
                final_response = response

            if final_response is None:
                default_plan = plan if plan is not None else OrchestratorPlan(
                    original_query=user_query,
                    interpreted_intent="Loi",
                    tools=[],
                    expected_outcome="Khong co"
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

            return AgentLoopResult(
                success=final_resp.success,
                query=user_query,
                final_answer=final_resp.synthesized_answer,
                iterations=current_iteration,
                execution_time=execution_time,
                plan=final_resp.plan,
                tool_results=final_resp.tool_results,
                critic_reviews=[r.model_dump() for r in all_critic_reviews],
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return AgentLoo
