from typing import List, Optional
from sqlmodel import SQLModel, Field, Relationship

# 定義 Artist 資料表模型
class Artist(SQLModel, table=True):
    __tablename__ = "artists"
    artist_id: str = Field(primary_key=True)
    artist_name: str
    artist_hotness: float

    songs: List["Song"] = Relationship(back_populates="artist")

# 定義 Song 資料表模型
class Song(SQLModel, table=True):
    __tablename__ = 'songs'
    song_id: str = Field(primary_key=True)
    song_title: str = Field(index=True)
    artist_id: str = Field(foreign_key="artists.artist_id")
    song_hotness: Optional[float] = Field(default=None)
    year: Optional[int] = Field(default=None)

    artist: Optional["Artist"] = Relationship(back_populates="songs")
    audio_features: Optional["AudioFeatures"] = Relationship(
        back_populates="song",
        sa_relationship_kwargs={"uselist": False}
    )

# 定義 AudioFeatures 資料表模型
class AudioFeatures(SQLModel, table=True):
    __tablename__ = "audio_features"
    song_id: str = Field(foreign_key="songs.song_id", primary_key=True)
    danceability: float
    energy: float
    key: int
    loudness: float
    tempo: float

    song: Optional["Song"] = Relationship(back_populates="audio_features")


# ==========================================
# 新增：定義 UserSongPlay 資料表模型 (用戶播放紀錄)
# ==========================================
class UserSongPlay(SQLModel, table=True):
    __tablename__ = "user_song_plays"

    # 獨立的流水號主鍵
    id: Optional[int] = Field(default=None, primary_key=True)

    # 建立 index=True 可加快根據 user_id 搜尋歷史紀錄的速度
    user_id: str = Field(index=True)

    # 關聯到 songs 表的 song_id
    song_id: str = Field(foreign_key="songs.song_id", index=True)