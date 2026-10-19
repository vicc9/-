from qdrant_client import AsyncQdrantClient, models

from app.core.config import settings


class VectorStore:
    """Qdrant 向量資料庫連接管理類別"""

    def __init__(self):

        print("========================================")
        print("正在建立 Qdrant Client")
        print("QDRANT URL:", settings.VECTOR_DATABASE_URL)
        print(
            "QDRANT API KEY:",
            "SET" if settings.QDRANT_API_KEY else "NOT SET"
        )
        print(
            "COLLECTION:",
            settings.COLLECTION_NAME_USER_HISTORY
        )
        print("========================================")

        self.client = AsyncQdrantClient(
            url=settings.VECTOR_DATABASE_URL,
            api_key=settings.QDRANT_API_KEY,
        )

    async def ensure_user_history_index(self):

        collection_name = settings.COLLECTION_NAME_USER_HISTORY

        print("========================================")
        print("正在檢查 Qdrant Collection")
        print("Collection:", collection_name)
        print("========================================")

        try:

            exists = await self.client.collection_exists(
                collection_name=collection_name
            )

            print("✅ Qdrant API 連線成功")
            print("Collection exists:", exists)

        except Exception as e:

            print("========================================")
            print("❌ Qdrant 連線失敗")
            print("Exception Type:", type(e).__name__)
            print("Exception:", repr(e))
            print("QDRANT URL:", settings.VECTOR_DATABASE_URL)
            print(
                "QDRANT API KEY:",
                "SET" if settings.QDRANT_API_KEY else "NOT SET"
            )
            print("========================================")

            raise

        if not exists:
            raise RuntimeError(
                f"Qdrant Collection 不存在: {collection_name}"
            )

        print(
            f"✅ Qdrant Collection 已存在: {collection_name}"
        )

        try:

            await self.client.create_payload_index(
                collection_name=collection_name,
                field_name="original_id",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )

            print(
                "✅ Qdrant Payload Index 已確認: "
                f"{collection_name}.original_id (KEYWORD)"
            )

        except Exception as e:

            print("❌ Payload Index 建立失敗")
            print("Exception Type:", type(e).__name__)
            print("Exception:", repr(e))
            raise

    async def close(self):

        if self.client:

            print("正在關閉 Qdrant 連線...")

            await self.client.close()

            print("✅ Qdrant 連線已關閉")