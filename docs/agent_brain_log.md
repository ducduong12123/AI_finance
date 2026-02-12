# AI Finance Assistant - Agent Brain Work Log

Tài liệu này ghi lại quá trình lập kế hoạch, thiết kế và triển khai bộ não AI (Models & Agent Flows) cho dự án.

---

## 📅 Nhật ký làm việc

### 2026-02-11: Khởi tạo và Lập kế hoạch
- **Trạng thái**: Đang thực hiện.
- **Nội dung**:
    - Phân tích cấu trúc hiện tại của Backend và Frontend.
    - Nhận diện các thành phần cốt lõi: Gemini 2.0 Flash, FastAPI, Supabase, Qdrant.
    - Đã yêu cầu Agent Metis lập kế hoạch chi tiết cho Agentic Workflow.
    - Xác định vai trò: Sisyphus tập trung vào "Brain" (Logic AI, Agent State, Tool Use), phối hợp với FE Agent và BE Agent.

---

## 🛠 MCP & Skills Evaluation (Sisyphus's Tools)

Dưới đây là đánh giá các công cụ (skills/subagents) có sẵn của Sisyphus để phục vụ dự án:

| Công cụ | Độ phù hợp | Cách sử dụng trong dự án này |
| :--- | :--- | :--- |
| **Metis (Plan)** | ⭐⭐⭐⭐⭐ | Lập kế hoạch kiến trúc Agent, phân tích requirement phức tạp. |
| **Oracle (Consult)** | ⭐⭐⭐⭐⭐ | Tham vấn về thiết kế State Machine, tối ưu hóa Prompt, xử lý lỗi logic AI. |
| **Explore (Search)** | ⭐⭐⭐⭐ | Tìm kiếm pattern trong codebase để đảm bảo Agent logic khớp với BE/FE. |
| **Librarian (Research)** | ⭐⭐⭐⭐ | Nghiên cứu các thư viện MCP, LangChain patterns, hoặc API documentation của các dịch vụ tài chính. |
| **Momus (Review)** | ⭐⭐⭐⭐ | Review lại các bản kế hoạch và code logic trước khi bàn giao. |

---

## 🏗 Kế hoạch Tổng quát (High-level Plan)

Sau khi nghiên cứu, tôi đề xuất kiến trúc Agent như sau:

1. **Kiến trúc Brain (Logic AI)**:
   - Sử dụng mô hình **ReAct (Reasoning + Acting)** tích hợp sẵn trong Gemini 2.0 Flash thông qua **Native Function Calling**.
   - Phân tách logic thành:
     - `BaseAgent`: Quản lý prompt hệ thống, lịch sử chat và gọi LLM.
     - `FinanceAgent`: Chứa logic nghiệp vụ tài chính, các tools cụ thể.

2. **Quản lý Trạng thái (State Management)**:
   - Mở rộng `AgentState` để lưu trữ `plan`, `steps_taken`, và `memory`.
   - `StateManager` sẽ chịu trách nhiệm đồng bộ hóa State này với Supabase để hỗ trợ multi-turn conversation dài hạn.

3. **Hệ thống Kỹ năng (Skills & MCP)**:
   - **Internal Skills**: Các function Python thuần túy được wrap làm Gemini Tools (ví dụ: `get_spending_summary`, `calculate_loan`).
   - **MCP Tools**: Sử dụng thư viện `mcp` của Python để kết nối với các MCP Server bên ngoài (ví dụ: Google Search, Brave Search, hoặc các DB connector).

4. **Luồng Streaming (Communication)**:
   - Tối ưu `ChatService` để bọc `FinanceAgent`.
   - Khi Agent "suy nghĩ" hoặc gọi Tool, hệ thống sẽ gửi các event trung gian về Frontend (có thể dùng `RunFinished` với metadata hoặc một custom event nếu cần) để người dùng biết AI đang làm việc.

---

## 🚀 Các bước triển khai tiếp theo

1. [ ] **Step 1**: Triển khai `src/agents/base.py` và `src/agents/finance_agent.py`.
2. [ ] **Step 2**: Cập nhật `src/agents/state/manager.py` để hỗ trợ Persistence.
3. [ ] **Step 3**: Xây dựng Skill đầu tiên: `search_finance_knowledge` (Kết nối với Qdrant RAG).
4. [ ] **Step 4**: Tích hợp luồng Agent vào `src/services/chat_service.py`.
5. [ ] **Step 5**: Thử nghiệm MCP Client cơ bản.

