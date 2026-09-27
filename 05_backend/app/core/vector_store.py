from qdrant_client import AsyncQdrantClient, models

from app.core.config import settings


class VectorStore:
    """Qdrant 向量資料庫連接管理類別"""

    def __init__(self):
        self.client = AsyncQdrantClient(
            url=settings.VECTOR_DATABASE_URL,
            api_key=settings.QDRANT_API_KEY,
        )

    async def ensure_user_history_index(self):
        """
        確保 user_song_vectors 的 original_id
        存在 KEYWORD Payload Index。
        """

        collection_name = settings.COLLECTION_NAME_USER_HISTORY

        # 確認 Collection 是否存在
        exists = await self.client.collection_exists(
            collection_name=collection_name
        )

        if not exists:
            raise RuntimeError(
                f"Qdrant Collection 不存在: {collection_name}"
            )

        print(
            f"✅ Qdrant Collection 已存在: {collection_name}"
        )

        # 建立 original_id KEYWORD index
        await self.client.create_payload_index(
            collection_name=collection_name,
            field_name="original_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )

        print(
            "✅ Qdrant Payload Index 已確認: "
            f"{collection_name}.original_id (KEYWORD)"
        )

    async def close(self):
        """關閉 Qdrant 非同步連線。"""

        if self.client:
            await self.client.close()