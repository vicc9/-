from typing import List, Dict, Any, Optional
from sqlmodel import Session
from app.crud.crud_vector import VectorRepository
from app.crud.crud_user import get_user_history, get_users as crud_get_users
from app.services.song_service import SongService
from app.model import Song

class UserVectorService:
    """處理用戶向量相關的業務邏輯，包括推薦歌曲"""

    def __init__(self, db: Session):
        self.vector_repository = VectorRepository()
        self.db = db

    async def get_recommended_songs(self, user_id: str, limit: int) -> List[Dict[str, Any]]:
        try:
            # 1. 查詢用戶向量
            user_vector = await self.vector_repository.search_vector_by_user_id(user_id)
            if not user_vector:
                raise ValueError(f"No vector found for user ID: {user_id}. Cannot generate recommendations.")

            # 2. 搜尋相似用戶 (多找一個，排除自己)
            similar_users_qdrant_points = await self._find_similar_users(user_vector, limit + 1)
            similar_users = [
                point.payload['original_id'] for point in similar_users_qdrant_points
                if point.payload and 'original_id' in point.payload and point.payload['original_id'] != user_id
            ]

            if not similar_users:
                return []

            # 3. 從相似用戶的聽歌紀錄中，排除用戶已聽過的，作為推薦清單
            recommended_song_ids = await self._get_recommendations_from_similar_users(user_id, similar_users)

            # 根據 limit 參數截取推薦歌曲 ID
            recommended_song_ids = list(recommended_song_ids)[:limit]

            # 獲取推薦歌曲的詳細資訊
            # 【修正】SongService.get_song() 回傳的本來就是 dict（裡面已經對
            # song 呼叫過 model_dump() 了），不是 SQLModel 物件，所以這裡不需要
            # 再呼叫一次 .model_dump()，直接把 dict 加進清單即可。
            recommended_songs_details = []
            for song_id in recommended_song_ids:
                song_details = await self._fetch_song_details(song_id)
                if song_details:  # 確保歌曲詳情存在
                    recommended_songs_details.append(song_details)

            return recommended_songs_details

        except Exception as e:
            print(f"Error generating recommendations: {e}")
            raise

    async def _find_similar_users(self, user_vector: List[float], limit: int) -> List[Any]:
        """內部方法：在 Qdrant 中搜尋與給定向量相似的用戶"""
        search_result = await self.vector_repository.search_similar_users(user_vector, limit)
        return search_result

    async def _get_recommendations_from_similar_users(self, user_id: str, similar_user_ids: List[str]) -> List[str]:
        """內部方法：從相似用戶的歷史紀錄中篩選推薦歌曲"""
        recommended_songs = set()
        user_history_songs = set(get_user_history(self.db, user_id))

        for similar_user_id in similar_user_ids:
            similar_user_history_songs = set(get_user_history(self.db, similar_user_id))
            new_recommendations = similar_user_history_songs - user_history_songs
            recommended_songs.update(new_recommendations)

        return list(recommended_songs)

    async def _fetch_song_details(self, song_id: str) -> Optional[Dict[str, Any]]:
        """內部方法：從 PostgreSQL 獲取歌曲的詳細資訊。

        【修正】回傳型別改成 Optional[Dict[str, Any]]，因為
        SongService.get_song() 實際回傳的就是 dict，而不是 Song 這個
        SQLModel 物件，原本標成 Optional[Song] 會造成誤導。
        """
        song_service = SongService(self.db)
        song_details = song_service.get_song(song_id)
        if not song_details:
            # 這裡可以選擇不拋出異常，而是返回 None，讓上層處理
            print(f"Warning: Song with ID {song_id} not found in DB.")
            return None
        return song_details

    async def get_users(self, skip: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
        """
        獲取所有用戶的列表。
        :param limit: 返回的用戶數量限制。
        :return: 用戶列表，每個用戶包含 ID 和向量。
        """
        if limit <= 0:
            raise ValueError("Limit must be a positive integer.")
        try:
            return crud_get_users(self.db, skip=skip, limit=limit)
        except Exception as e:
            raise RuntimeError(f"An error occurred while fetching users: {e}")