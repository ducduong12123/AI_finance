from qdrant_client import QdrantClient
from qdrant_client.http import models
from core.config import settings


def get_qdrant_client():
    return QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        api_key=settings.QDRANT_API_KEY,
    )


def upsert_vectors(collection_name: str, points: list):
    client = get_qdrant_client()
    client.upsert(collection_name=collection_name, points=points)


def search_vectors(collection_name: str, vector: list, limit: int = 5):
    client = get_qdrant_client()
    # Kiểm tra collection tồn tại trước khi search
    # (Trong thực tế cần handle exception nếu collection chưa có)
    return client.search(
        collection_name=collection_name, query_vector=vector, limit=limit
    )
