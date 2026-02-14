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
from agents.base import BaseAgent
from agents.orchestrator import OrchestratorPlan, ToolResult


class CriticReview(BaseModel):
    """Review result from Critic agent."""

    approved: bool = Field(..., description="Whether the plan/result is approved")
    score: float = Field(..., ge=0, le=5, description="Quality score (0-5)")
    reasoning: str = Field(..., description="Detailed reasoning")
    concerns: list[str] = Field(default_factory=list, description="List of concerns")
    suggestions: list[str] = Field(
        default_factory=list, description="Improvement suggestions"
    )
    requires_changes: bool = Field(
        default=False, description="Whether changes are required (score 0-2)"
    )
    needs_clarification: bool = Field(
        default=False, description="Whether to ask user for clarification (score 3-5)"
    )
    iteration_feedback: Optional[str] = Field(
        default=None, description="Feedback for Orchestrator if needs iteration"
    )
    clarification_questions: Optional[list[str]] = Field(
        default=None, description="Questions to ask user if needs_clarification"
    )


class CriticAgent(BaseAgent):
    """
    Critic Agent - Phản biện và đánh giá.
    """

    SYSTEM_PROMPT = """Bạn là Critic Agent trong hệ thống AI Finance Assistant.

NHIỆM VỤ:
Đánh giá kết quả thực thi dựa trên "Intent đã diễn dịch" của Orchestrator (KHÔNG đánh giá dựa trên yêu cầu gốc của ngưởi dùng).

QUAN TRỌNG - TIÊU CHÍ ĐÁNH GIÁ (Thang điểm 0-5):
0-2 điểm: KHÔNG ĐẠT - Yêu cầu Orchestrator lập lại plan
  • Dùng kiến thức cũ thay vì tool
  • Tool thất bại hoàn toàn
  • Sai lệch nghiêm trọng so với intent
  → "approved": false, "requires_changes": true

3-5 điểm: ĐẠT - Có thể trả lởi, nhưng cần hỏi thêm ngưởi dùng
  • Thiếu thông tin chi tiết (ví dụ: thiếu P/E, ROE...)
  • Có thể làm tốt hơn nhưng không bắt buộc
  → "approved": true, "needs_clarification": true

HƯỚNG DẪN ĐÁNH GIÁ:
1. Luôn so sánh kết quả với "Intent đã diễn dịch" của Orchestrator
2. Nếu Orchestrator chỉ intent là "lấy giá", đừng yêu cầu thêm P/E, ROE...
3. Chỉ phản hồi lại Orchestrator khi score 0-2
4. Score 3-5: approved=true, có thể đề xuất câu hỏi bổ sung

OUTPUT FORMAT (JSON):
{
    "approved": true|false,
    "score": 0-5,
    "reasoning": "Giải thích ngắn gọn...",
    "concerns": ["Vấn đề 1"],
    "suggestions": ["Gợi ý 1"],
    "requires_changes": true|false,
    "needs_clarification": true|false,
    "iteration_feedback": "Phản hồi cho Orchestrator (nếu requires_changes=true)",
    "clarification_questions": ["Câu hỏi 1", "Câu hỏi 2"] (nếu needs_clarification=true)
}
"""

    def __init__(self):
        super().__init__(system_prompt=self.SYSTEM_PROMPT)

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
            response = await self.generate_content_async(prompt)
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

🎯 **CHỈ ĐÁNH GIÁ DỰA TRÊN INTENT ĐÃ DIỄN DỊCH - KHÔNG QUAN TÂM YÊU CẦU GỐC**

Intent đã diễn dịch (TIÊU CHUẨN DUY NHẤT): {plan.interpreted_intent}

Kết quả từ các tools:
{chr(10).join(results_text)}

📊 THANG ĐIỂM (0-5):
- 0-2: Không đạt → requires_changes=true, phản hồi lại Orchestrator
  • Dùng kiến thức cũ
  • Tool thất bại hoàn toàn  
  • Sai lệch nghiêm trọng so với intent

- 3-5: Đạt → approved=true
  • Score 3-4: needs_clarification=true (có thể hỏi thêm)
  • Score 5: needs_clarification=false (hoàn hảo)

⚠️ **VÍ DỤ QUAN TRỌNG:**
- Nếu intent là "Lấy giá VCB" → Chỉ cần có giá là đạt (Score 5), KHÔNG cần P/E, ROE
- Nếu intent là "So sánh toàn diện VCB và VNM với P/E, ROE" → Cần đầy đủ chỉ số
- Nếu intent là "Thông tin công ty VCB" → Chỉ cần info cơ bản, không cần giá

❓ CÂU HỎI:
1. Kết quả có đáp ứng đúng intent ở trên không? (KHÔNG quan tâm yêu cầu gốc)
2. Có cần thêm iteration không? (chỉ khi 0-2 điểm)
3. Có cần hỏi thêm ngưởi dùng không? (nếu 3-4 điểm)
4. Chấm điểm 0-5?

Trả về JSON theo format đã chỉ định.
"""

        try:
            response = await self.generate_content_async(prompt)
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
