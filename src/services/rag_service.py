import uuid
from typing import List
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from core.config import settings
from data.adapters.qdrant_client import upsert_vectors
from qdrant_client.http.models import PointStruct


class RAGService:
    def __init__(self, chunk_size: int = 1500, chunk_overlap: int = 200):
        # Khởi tạo Gemini Embeddings dùng Google SDK
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.EMBEDDING_MODEL, google_api_key=settings.GOOGLE_API_KEY
        )

        # Chiến lược RecursiveCharacterTextSplitter để giữ ngữ cảnh tài chính
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )

    def process_financial_pdf(self, file_path: str, collection_name: str):
        """
        Đọc file PDF, chia nhỏ (chunking), tạo embedding bằng Gemini và đẩy vào Qdrant.
        """
        # 1. Load PDF
        loader = PyPDFLoader(file_path)
        documents = loader.load()

        # 2. Chia nhỏ văn bản (Chunking)
        chunks = self.text_splitter.split_documents(documents)
        texts = [chunk.page_content for chunk in chunks]

        # 3. Tạo Embeddings hàng loạt bằng Google Gemini SDK (Tối ưu performance)
        embeddings = self.embeddings.embed_documents(texts)

        # 4. Chuẩn bị dữ liệu cho Qdrant
        points = []
        for i, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "text": chunk.page_content,
                    "metadata": chunk.metadata,
                    "chunk_index": i,
                },
            )
            points.append(point)

        # 5. Upsert vào Qdrant
        upsert_vectors(collection_name, points)

        return {
            "status": "success",
            "chunks_processed": len(points),
            "collection": collection_name,
        }

    async def query(
        self, text: str, collection_name: str = "finance_docs", top_k: int = 5
    ):
        """
        Truy vấn thông tin từ Qdrant dựa trên text đầu vào.
        """
        from data.adapters.qdrant_client import search_vectors
        from pydantic import BaseModel

        class SearchResult(BaseModel):
            content: str
            metadata: dict
            score: float

        # 1. Tạo embedding cho câu hỏi
        vector = self.embeddings.embed_query(text)

        # 2. Tìm kiếm vector tương đồng
        hits = search_vectors(collection_name, vector, top_k)

        # 3. Format kết quả
        results = [
            SearchResult(
                content=hit.payload.get("text", ""),
                metadata=hit.payload.get("metadata", {}),
                score=hit.score,
            )
            for hit in hits
        ]

        return results


rag_service = RAGService()
