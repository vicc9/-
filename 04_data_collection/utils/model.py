import os
from typing import List, Optional

import pandas as pd
from dotenv import load_dotenv
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select
from pathlib import Path

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("找不到 DATABASE_URL，請確認 .env 檔案是否存在且設定正確")


class Artist(SQLModel, table=True):
    __tablename__ = "artists"

    artist_id: str = Field(primary_key=True)
    artist_name: str
    artist_hotness: float

    songs: List["Song"] = Relationship(back_populates="artist")


class Song(SQLModel, table=True):
    __tablename__ = "songs"

    song_id: str = Field(primary_key=True)
    song_title: str = Field(index=True)
    artist_id: str = Field(foreign_key="artists.artist_id")
    song_hotness: Optional[float] = Field(default=None)
    year: Optional[int] = Field(default=None)

    artist: Optional["Artist"] = Relationship(back_populates="songs")
    audio_features: Optional["AudioFeatures"] = Relationship(
        back_populates="song",
        sa_relationship_kwargs={"uselist": False},
    )


class AudioFeatures(SQLModel, table=True):
    __tablename__ = "audio_features"

    song_id: str = Field(foreign_key="songs.song_id", primary_key=True)
    danceability: float
    energy: float
    key: int
    loudness: float
    tempo: float

    song: Optional["Song"] = Relationship(back_populates="audio_features")


class UserSongPlay(SQLModel, table=True):
    __tablename__ = "user_song_plays"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(max_length=40, nullable=False)
    song_id: str = Field(max_length=18, nullable=False)
    play_count: int = Field(nullable=False)


engine = create_engine(DATABASE_URL)


def create_session(engine):
    return Session(engine)


def insert_listening_history(engine, df: pd.DataFrame):
    """使用 pandas to_sql 進行高效批量寫入"""
    df.to_sql(
        name="user_song_plays",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=10000,
    )


if __name__ == "__main__":
    # ---------- 路徑（以本檔案位置為基準，與執行時的工作目錄無關） ----------
    BASE_DIR = Path(__file__).resolve().parent.parent  # 04_data_collection
    DATASET_DIR = BASE_DIR / "dataset"
    TRIPLETS_PATH = DATASET_DIR / "train_triplets.txt"
    SUBSET_CSV_PATH = DATASET_DIR / "listening_history_subset.csv"
    COLUMNS = ["user_id", "song_id", "play_count"]
    # 建立資料表
    SQLModel.metadata.create_all(engine)

    # 假設從 CSV 載入資料
    listening_history_subset = pd.read_csv(SUBSET_CSV_PATH)

    # 寫入資料
    if "listening_history_subset" in locals():
        insert_listening_history(engine, listening_history_subset)
        print("Listening history inserted into the database.")

    # 查詢並列印前 10 筆紀錄
    with create_session(engine) as session:
        results = session.exec(select(UserSongPlay).limit(10)).all()
        for record in results:
            print(record)