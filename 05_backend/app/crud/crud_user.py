from typing import List, Optional
from sqlmodel import Session, select, func
from app.model import UserSongPlay

# 【修正】與 build_user_vectors.py 的 MIN_PLAYS_PER_USER 保持一致。
# 因為向量庫只收錄「播放紀錄數 >= 此門檻」的用戶，/users/ 列表如果沒有
# 套用同樣的篩選條件，前端就有機會選到「SQL 裡存在、但 Qdrant 裡沒有
# 向量」的用戶，點下去要推薦時就會 404。
MIN_PLAYS_PER_USER = 5


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[str]:
    """取得播放紀錄數達到門檻的用戶清單（確保這些用戶在 Qdrant 裡也找得到向量）"""
    statement = (
        select(UserSongPlay.user_id)
        .group_by(UserSongPlay.user_id)
        .having(func.count(UserSongPlay.song_id) >= MIN_PLAYS_PER_USER)
        .offset(skip)
        .limit(limit)
    )
    users = db.exec(statement).all()
    return users


def get_user_history(db: Session, user_id: str) -> List[str]:
    """Get user listening history with pagination"""
    statement = select(UserSongPlay.song_id).where(UserSongPlay.user_id == user_id)
    songs = db.exec(statement).all()
    return songs