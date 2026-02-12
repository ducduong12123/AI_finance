from typing import List
from services.rag_service import rag_service


async def search_finance_knowledge(query: str) -> str:
    """
    Tìm kiếm thông tin từ kho kiến thức tài chính và các tài liệu đã tải lên.

    Args:
        query: Câu hỏi hoặc từ khóa cần tìm kiếm.

    Returns:
        Một chuỗi chứa thông tin hữu ích được tìm thấy.
    """
    try:
        # Gọi RAG service để tìm kiếm từ Qdrant
        results = await rag_service.query(query)
        if not results:
            return "Không tìm thấy thông tin liên quan trong kho dữ liệu."

        # Format lại kết quả trả về cho LLM
        context = "\n---\n".join([r.content for r in results])
        return f"Dưới đây là thông tin tìm được từ tài liệu:\n\n{context}"
    except Exception as e:
        return f"Lỗi khi truy xuất kiến thức: {str(e)}"
