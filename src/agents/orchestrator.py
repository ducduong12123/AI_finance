"""
Orchestrator Agent - Multi-Agent System.

The Orchestrator is responsible for:
1. Understanding user requests
2. Planning tool execution strategy
3. Coordinating with Critic for validation
4. Managing the agent loop until satisfactory result
"""

import json
import asyncio
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from pydantic import BaseModel, Field
import google.generativeai as genai

from core.config import settings
from agents.tools.tavily_search import tavily_web_search
from agents.tools.vnstock_tool import vnstock_get_quote, vnstock_get_company_info


class ToolPlan(BaseModel):
    """Execution plan for a single tool."""

    tool_name: str = Field(..., description="Name of the tool to execute")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Tool parameters"
    )
    reason: str = Field(..., description="Why this tool is needed")
    priority: int = Field(default=1, description="Execution priority (1-10)")


class OrchestratorPlan(BaseModel):
    """Complete execution plan from orchestrator."""

    original_query: str = Field(..., description="Original user query")
    interpreted_intent: str = Field(
        ..., description="AI's understanding of what user wants"
    )
    tools: List[ToolPlan] = Field(default_factory=list, description="Tools to execute")
    can_parallel: bool = Field(
        default=True, description="Whether tools can run in parallel"
    )
    expected_outcome: str = Field(..., description="What result should look like")


class ToolResult(BaseModel):
    """Result from executing a tool."""

    tool_name: str = Field(...)
    success: bool = Field(...)
    result: str = Field(...)
    execution_time: float = Field(...)
    error: Optional[str] = Field(default=None)


class OrchestratorResponse(BaseModel):
    """Final response from orchestrator after tool execution."""

    success: bool = Field(...)
    query: str = Field(...)
    plan: OrchestratorPlan = Field(...)
    tool_results: List[ToolResult] = Field(default_factory=list)
    synthesized_answer: str = Field(...)
    needs_iteration: bool = Field(
        default=False, description="Whether another iteration is needed"
    )
    iteration_reason: Optional[str] = Field(default=None)


class OrchestratorAgent:
    """
    Orchestrator Agent - Phân phối và điều phối.

    Quy trình:
    1. Nhận user query
    2. Tạo kế hoạch (plan) - xác định cần dùng tools nào
    3. Gửi plan cho Critic đánh giá
    4. Nếu approved → thực thi tools
    5. Tổng hợp kết quả
    6. Nếu chưa đạt → lặp lại từ bước 2
    """

    SYSTEM_PROMPT = """Bạn là Orchestrator Agent trong hệ thống AI Finance Assistant.

NHIỆM VỤ:
Phân tích yêu cầu của ngưởi dùng và lập kế hoạch sử dụng các công cụ (tools) để thu thập thông tin.

CÁC TOOLS CÓ SẴN:
1. **tavily_web_search** - Tìm kiếm thông tin trên web
   - Dùng khi cần: Tin tức mới nhất, thông tin thị trường, phân tích chuyên sâu
   - Parameters: query (str), search_depth ("basic"/"comprehensive"), max_results (int), recency_days (int)

2. **vnstock_get_quote** - Lấy giá cổ phiếu VN hiện tại
   - Dùng khi cần: Giá real-time của cổ phiếu VN
   - Parameters: symbol (str) - ví dụ: "VCB", "VNM"

3. **vnstock_get_company_info** - Lấy thông tin công ty VN
   - Dùng khi cần: Thông tin cơ bản, P/E, P/B, vốn hóa
   - Parameters: symbol (str)

QUY TẮC LẬP KẾ HOẠCH:
1. Phân tích intent: Ngưởi dùng muốn gì? (giá, tin tức, phân tích...)
2. Xác định tools cần thiết
3. Nếu cần thông tin real-time + tin tức → dùng CẢ HAI song song
4. Ưu tiên vnstock cho dữ liệu chính xác, tavily cho tin tức/phân tích

OUTPUT FORMAT (JSON):
{
    "original_query": "...",
    "interpreted_intent": "...",
    "tools": [
        {
            "tool_name": "tavily_web_search|vnstock_get_quote|vnstock_get_company_info",
            "parameters": {...},
            "reason": "...",
            "priority": 1
        }
    ],
    "can_parallel": true|false,
    "expected_outcome": "..."
}

VÍ DỤ:
Query: "Cổ phiếu VCB hôm nay thế nào?"
→ interpreted_intent: "Ngưởi dùng muốn biết giá VCB hiện tại và tin tức liên quan"
→ tools: [
    {tool_name: "vnstock_get_quote", parameters: {symbol: "VCB"}, reason: "Lấy giá real-time", priority: 1},
    {tool_name: "tavily_web_search", parameters: {query: "VCB Vietcombank cổ phiếu tin tức hôm nay", search_depth: "basic", max_results: 5}, reason: "Tìm tin tức mới nhất", priority: 2}
]
→ can_parallel: true
"""

    def __init__(self):
        self.model = genai.GenerativeModel(
            model_name=settings.PRIMARY_MODEL,
            system_instruction=self.SYSTEM_PROMPT,
        )

        # Tool registry
        self.tools: Dict[str, Callable] = {
            "tavily_web_search": tavily_web_search,
            "vnstock_get_quote": vnstock_get_quote,
            "vnstock_get_company_info": vnstock_get_company_info,
        }

    async def create_plan(self, user_query: str) -> OrchestratorPlan:
        """
        Create execution plan for user query.

        Args:
            user_query: User's natural language query

        Returns:
            OrchestratorPlan with tool execution strategy
        """
        prompt = f"""
Ngưởi dùng hỏi: "{user_query}"

Hãy phân tích và tạo kế hoạch thực thi (plan) dưới dạng JSON theo format đã chỉ định.
Chỉ trả về JSON, không thêm text khác.
"""

        try:
            response = await self.model.generate_content_async(prompt)
            content = response.text

            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            plan_data = json.loads(content.strip())
            return OrchestratorPlan(**plan_data)

        except Exception as e:
            # Fallback plan if parsing fails
            return OrchestratorPlan(
                original_query=user_query,
                interpreted_intent="Cần tìm kiếm thông tin",
                tools=[
                    ToolPlan(
                        tool_name="tavily_web_search",
                        parameters={"query": user_query, "max_results": 5},
                        reason="Tìm kiếm thông tin liên quan",
                        priority=1,
                    )
                ],
                can_parallel=False,
                expected_outcome="Thông tin về yêu cầu của ngưởi dùng",
            )

    async def execute_tools(self, plan: OrchestratorPlan) -> List[ToolResult]:
        """
        Execute tools according to plan.

        Args:
            plan: OrchestratorPlan with tool execution strategy

        Returns:
            List of ToolResult
        """
        results = []

        if plan.can_parallel:
            # Execute all tools in parallel
            tasks = []
            for tool_plan in plan.tools:
                task = self._execute_single_tool(tool_plan)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Convert exceptions to failed results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append(
                        ToolResult(
                            tool_name=plan.tools[i].tool_name,
                            success=False,
                            result="",
                            execution_time=0.0,
                            error=str(result),
                        )
                    )
                else:
                    processed_results.append(result)
            results = processed_results
        else:
            # Execute sequentially
            for tool_plan in plan.tools:
                result = await self._execute_single_tool(tool_plan)
                results.append(result)

        return results

    async def _execute_single_tool(self, tool_plan: ToolPlan) -> ToolResult:
        """Execute a single tool."""
        import time

        start_time = time.time()

        try:
            if tool_plan.tool_name not in self.tools:
                return ToolResult(
                    tool_name=tool_plan.tool_name,
                    success=False,
                    result="",
                    execution_time=time.time() - start_time,
                    error=f"Tool '{tool_plan.tool_name}' not found",
                )

            tool_func = self.tools[tool_plan.tool_name]
            result = await tool_func(**tool_plan.parameters)

            return ToolResult(
                tool_name=tool_plan.tool_name,
                success=True,
                result=result,
                execution_time=time.time() - start_time,
            )

        except Exception as e:
            return ToolResult(
                tool_name=tool_plan.tool_name,
                success=False,
                result="",
                execution_time=time.time() - start_time,
                error=str(e),
            )

    async def synthesize_response(
        self,
        plan: OrchestratorPlan,
        tool_results: List[ToolResult],
    ) -> OrchestratorResponse:
        """
        Synthesize final response from tool results.

        Args:
            plan: Original execution plan
            tool_results: Results from tool execution

        Returns:
            OrchestratorResponse with synthesized answer
        """
        # Format tool results for synthesis
        results_text = []
        for result in tool_results:
            status = "✅" if result.success else "❌"
            results_text.append(f"\n{status} {result.tool_name}:")
            if result.success:
                results_text.append(result.result)
            else:
                results_text.append(f"Error: {result.error}")

        synthesis_prompt = f"""
Dựa trên kế hoạch và kết quả thu thập được, hãy tổng hợp câu trả lời hoàn chỉnh bằng tiếng Việt.

Yêu cầu gốc: {plan.original_query}
Intent: {plan.interpreted_intent}

Kết quả từ các tools:
{chr(10).join(results_text)}

Yêu cầu:
1. Trả lời trực tiếp câu hỏi của ngưởi dùng
2. Tổng hợp thông tin từ tất cả sources
3. Nếu có dữ liệu số (giá, %), làm nổi bật
4. Thêm nhận xét/phân tích ngắn gọn nếu phù hợp
5. Format rõ ràng, dễ đọc

Chỉ trả về câu trả lời, không cần giải thích quá trình.
"""

        try:
            response = await self.model.generate_content_async(synthesis_prompt)
            synthesized_answer = response.text
        except Exception as e:
            synthesized_answer = f"Lỗi khi tổng hợp: {str(e)}"

        # Determine if needs another iteration
        needs_iteration = any(not r.success for r in tool_results)
        iteration_reason = None
        if needs_iteration:
            iteration_reason = "Một số tools thất bại, cần thử lại hoặc dùng cách khác"

        return OrchestratorResponse(
            success=not needs_iteration,
            query=plan.original_query,
            plan=plan,
            tool_results=tool_results,
            synthesized_answer=synthesized_answer,
            needs_iteration=needs_iteration,
            iteration_reason=iteration_reason,
        )


# Singleton instance
orchestrator = OrchestratorAgent()
