from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routers import songs, users
from app.core.vector_store import VectorStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 啟動與關閉生命週期管理。

    啟動時：
    1. 連線 Qdrant
    2. 確認 user_song_vectors Collection 存在
    3. 確保 original_id 有 KEYWORD Payload Index

    關閉時：
    1. 關閉 Qdrant 連線
    """

    vector_store = VectorStore()

    try:
        print("========================================")
        print("正在初始化 Qdrant...")
        print("========================================")

        await vector_store.ensure_user_history_index()

        print("✅ Qdrant 初始化完成")

        yield

    finally:
        print("正在關閉 Qdrant 連線...")
        await vector_store.close()
        print("✅ Qdrant 連線已關閉")


app = FastAPI(
    title="Music Recommendation System",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(songs.router)
app.include_router(users.router)


@app.get("/")
async def root():
    return {
        "message": "Hello Music Recommendation System!"
    }