from typing import List, Optional, Any

from qdrant_client import models

from app.core.config import settings
from app.core.vector_store import VectorStore


class VectorRepository:
    def __init__(self):
        vector_store = VectorStore()
        self.vector_client = vector_store.client

    async def search_vector_by_user_id(
        self,
        user_id: str
    ) -> Optional[List[float]]:
        """
        根據 user_id 搜尋對應的使用者向量。
        """

        try:
            records, _ = await self.vector_client.scroll(
                collection_name=settings.COLLECTION_NAME_USER_HISTORY,

                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="original_id",
                            match=models.MatchValue(
                                value=user_id
                            ),
                        ),
                    ]
                ),

                limit=1,
                with_vectors=True,
            )

            if not records:
                print(
                    f"找不到 user_id '{user_id}' 的向量。"
                )
                return None

            user_vector = records[0].vector

            if user_vector is None:
                print(
                    f"user_id '{user_id}' 找到資料，"
                    "但 vector 為 None。"
                )
                return None

            return user_vector

        except Exception as e:
            print(
                f"搜尋 user_id '{user_id}' "
                f"的向量時發生錯誤: {e}"
            )
            raise

    async def search_similar_users(
        self,
        query_vector: List[float],
        limit: int,
    ) -> List[Any]:
        """
        根據輸入的查詢向量搜尋相似使用者。
        """

        try:
            results = await self.vector_client.query_points(
                collection_name=settings.COLLECTION_NAME_USER_HISTORY,
                query=query_vector,
                limit=limit,
                with_payload=True,
            )

            return results.points

        except Exception as e:
            print(
                f"搜尋相似用戶的向量時發生錯誤: {e}"
            )
            raise

    async def cleanup(self):
        """清理 Qdrant 連線。"""

        if self.vector_client:
            await self.vector_client.close()