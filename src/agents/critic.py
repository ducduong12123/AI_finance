"""
Critic Agent - Reflection & Validation Layer.

The Critic is responsible for:
1. Reviewing Orchestrator's plan before execution
2. Evaluating tool results quality
3. Deciding if iteration is needed
4. Providing improvement suggestions
"""

import json
from typing import Optional
from pydantic import BaseModel, Field
import google.generativeai as genai

from core.config import settings
from agents.orchestrator import OrchestratorPlan, ToolResult


class CriticReview(BaseModel):
    """Review result from Critic agent."""

    approved: bool = Field(..., description="Whether the plan/result is approved")
    score: float = Field(..., ge=0, le=10, description="Quality score (0-10)")
    reasoning: str = Field(..., description="Detailed reasoning")
    concerns: list[str] = Field(default_factory=list, description="List of concerns")
    suggestions: list[str] = Field(
        default_factory=list, description="Improvement suggestions"
    )
    requires_changes: bool = Field(
        default=False, description="Whether changes are required"
    )
    iteration_feedback: Optional[str] = Field(
        default=None, description="Feedback for next iteration"
    )


class CriticAgent:
    """
    Critic Agent - Phản biện và đánh giá.

    Vai trò:
    1. Review plan từ Orchestrator trước khi thực thi
    2. Chấp nhận/Từ chối plan với lý do
    3. Đánh giá kết quả tools sau khi chạy
    4. Quyết định có cần iteration không
    """

    SYSTEM_PROMPT = """Bạn là Critic Agent trong hệ thống AI Finance Assistant.

NHIỆM VỤ:
Đánh giá và phản biện kế hoạch (plan) của Orchestrator và kết quả thực thi.

TIÊU CHÍ ĐÁNH GIÁ:
1. **Phù hợp**: Plan có đáp ứng đúng yêu cầu ngưởi dùng không?
2. **Đầy đủ**: Có thiếu tool nào cần thiết không?
3. **Hiệu quả**: Có tool nào dư thừa không?
4. **Chính xác**: Parameters có đúng không?
5. **Chất lượng kết quả**: Kết quả trả về có đáp ứng mong đợi?

QUY TẮC:
- Score >= 8: Chất lượng tốt, có thể chấp nhận
- Score 5-7: Cần cải thiện nhưng vẫn dùng được
- Score < 5: Cần iteration (chạy lại)

OUTPUT FORMAT (JSON):
{
    "approved": true|false,
    "score": 0-10,
    "reasoning": "Giải thích chi tiết...",
    "concerns": ["Vấn đề 1", "Vấn đề 2"],
    "suggestions": ["Gợi ý 1", "Gợi ý 2"],
    "requires_changes": true|false,
    "iteration_feedback": "Hướng dẫn cho iteration tiếp theo (nếu cần)"
}

VÍ DỤ:
Plan: Chỉ tìm kiếm web cho "giá VCB"
→ approved: false
→ score: 4
→ reasoning: "Nên dùng vnstock_get_quote để lấy giá real-time thay vì chỉ tìm kiếm web"
→ suggestions: ["Thêm tool vnstock_get_quote với symbol='VCB'"]
→ requires_changes: true
"""

    def __init__(self):
        self.model = genai.GenerativeModel(
            model_name=settings.PRIMARY_MODEL,
            system_instruction=self.SYSTEM_PROMPT,
        )

    async def review_plan(self, plan: OrchestratorPlan) -> CriticReview:
        """
        Review execution plan before execution.

        Args:
            plan: OrchestratorPlan to review

        Returns:
            CriticReview with approval decision
        """
        plan_text = f"""
Yêu cầu gốc: {plan.original_query}
Intent hiểu được: {plan.interpreted_intent}

Kế hoạch tools:
"""
        for i, tool in enumerate(plan.tools, 1):
            plan_text += f"\n{i}. {tool.tool_name}"
            plan_text += f"\n   Parameters: {tool.parameters}"
            plan_text += f"\n   Lý do: {tool.reason}"
            plan_text += f"\n   Priority: {tool.priority}"

        plan_text += f"\n\nCó thể chạy song song: {plan.can_parallel}"
        plan_text += f"\nKết quả mong đợi: {plan.expected_outcome}"

        prompt = f"""
Hãy đánh giá kế hoạch sau:

{plan_text}

Trả về đánh giá dưới dạng JSON theo format đã chỉ định.
Chỉ trả về JSON, không thêm text khác.
"""

        try:
            response = await self.model.generate_content_async(prompt)
            content = response.text

            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            review_data = json.loads(content.strip())
            return CriticReview(**review_data)

        except Exception as e:
            # Fallback - approve with warning
            return CriticReview(
                approved=True,
                score=5.0,
                reasoning=f"Lỗi khi đánh giá: {str(e)}. Chấp nhận plan mặc định.",
                concerns=["Không thể đánh giá chi tiết do lỗi"],
                requires_changes=False,
            )

    async def review_results(
        self,
        plan: OrchestratorPlan,
        tool_results: list[ToolResult],
    ) -> CriticReview:
        """
        Review execution results.

        Args:
            plan: Original plan
            tool_results: Results from tool execution

        Returns:
            CriticReview with quality assessment
        """
        results_text = []
        for result in tool_results:
            status = "✅ Thành công" if result.success else "❌ Thất bại"
            results_text.append(f"\n{result.tool_name}: {status}")
            if result.success:
                # Truncate long results
                preview = (
                    result.result[:500] + "..."
                    if len(result.result) > 500
                    else result.result
                )
                results_text.append(f"  Kết quả: {preview}")
            else:
                results_text.append(f"  Lỗi: {result.error}")

        prompt = f"""
Đánh giá kết quả thực thi:

Yêu cầu gốc: {plan.original_query}
Intent: {plan.interpreted_intent}

Kết quả từ các tools:
{chr(10).join(results_text)}

Câu hỏi:
1. Kết quả có đáp ứng yêu cầu không?
2. Có thiếu thông tin quan trọng không?
3. Có cần thêm iteration không?
4. Chất lượng tổng thể (0-10)?

Trả về đánh giá dưới dạng JSON theo format đã chỉ định.
"""

        try:
            response = await self.model.generate_content_async(prompt)
            content = response.text

            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            review_data = json.loads(content.strip())
            return CriticReview(**review_data)

        except Exception as e:
            # Check if all tools succeeded
            all_success = all(r.success for r in tool_results)

            return CriticReview(
                approved=all_success,
                score=7.0 if all_success else 3.0,
                reasoning=f"Đánh giá tự động: {'Tất cả tools thành công' if all_success else 'Có tools thất bại'}",
                concerns=["Không thể đánh giá chi tiết do lỗi"]
                if not all_success
                else [],
                requires_changes=not all_success,
                iteration_feedback="Thử lại các tools thất bại"
                if not all_success
                else None,
            )


# Singleton instance
critic = CriticAgent()
