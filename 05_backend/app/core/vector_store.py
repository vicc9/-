from qdrant_client import AsyncQdrantClient
from app.core.config import settings

class VectorStore:
    """Qdrant 向量資料庫連接管理類別"""

    def __init__(self):
        # 初始化 Qdrant 客戶端，連接到指定 URL
        self.client = AsyncQdrantClient(
            url=settings.VECTOR_DATABASE_URL,
            api_key=settings.QDRANT_API_KEY,
        )

    async def close(self):
        """非同步關閉 Qdrant 客戶端連線，確保釋放資源"""
        if self.client:
            await self.client.close()