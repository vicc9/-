from typing import List, Optional
from sqlmodel import Session, select
from app.model import Song, Artist

def get_songs(db: Session, skip: int = 0, limit: int = 100) -> List[tuple[Song, str]]:
    """
    從資料庫中獲取所有歌曲，支援分頁功能，並 join 藝人名稱。
    """
    statement = (
        select(Song, Artist.artist_name)
        .join(Artist, Song.artist_id == Artist.artist_id)
        .offset(skip)
        .limit(limit)
    )
    songs = db.exec(statement).all()
    return songs

def get_song(db: Session, song_id: str) -> Optional[tuple[Song, str]]:
    """
    根據歌曲 ID 獲取特定歌曲與藝人名稱。
    """
    statement = (
        select(Song, Artist.artist_name)
        .join(Artist, Song.artist_id == Artist.artist_id)
        .where(Song.song_id == song_id)
    )
    result = db.exec(statement).first()
    return result