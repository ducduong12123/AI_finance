from typing import List, Optional, Any
from .base import BaseAgent
from core.config import settings
from .skills.rag_skill import search_finance_knowledge


class FinanceAgent(BaseAgent):
    """
    Agent chuyên về tư vấn tài chính.
    Được trang bị các công cụ truy xuất dữ liệu và tính toán.
    """

    DEFAULT_SYSTEM_PROMPT = """
    Bạn là một Chuyên gia Tư vấn Tài chính Thông minh (AI Finance Advisor).
    Nhiệm vụ của bạn là giúp người dùng quản lý tài chính cá nhân, phân tích thu chi, và đưa ra lời khuyên đầu tư.
    
    Quy tắc ứng xử:
    1. Luôn lịch sự, chuyên nghiệp và khách quan.
    2. Nếu không chắc chắn, hãy yêu cầu thêm thông tin.
    3. Sử dụng các công cụ có sẵn (tools) để lấy dữ liệu chính xác trước khi trả lời.
    4. Trình bày dữ liệu dưới dạng bảng hoặc danh sách khi cần thiết.
    """

    def __init__(self, model_name: str = settings.PRIMARY_MODEL):
        # Đăng ký các tools cho Gemini
        tools = [
            search_finance_knowledge,
            self.get_user_balance,
            self.analyze_spending_trends,
        ]
        super().__init__(
            system_prompt=self.DEFAULT_SYSTEM_PROMPT, model_name=model_name, tools=tools
        )

    async def get_user_balance(self, account_type: str = "all") -> str:
        """
        Lấy số dư tài khoản của người dùng.
        """
        # Placeholder cho Supabase DB
        return "Số dư hiện tại của bạn là: 50,000,000 VND"

    async def analyze_spending_trends(self, month: int, year: int) -> str:
        """
        Phân tích xu hướng chi tiêu trong một khoảng thời gian.
        """
        # Placeholder cho Analytics logic
        return f"Xu hướng chi tiêu tháng {month}/{year}: Giảm 10% so với tháng trước."
