from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    PROJECT_NAME: str = "Music API"
    VERSION: str = "1.0.0"
    API_STR: str = "/api"

    DATABASE_USERNAME: str
    DATABASE_PASSWORD: str
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "music_database"

    # --- 以下為新增的 Qdrant 連線設定 ---
    VECTOR_DATABASE_URL: str = "http://localhost:6333"
    # 【新增】Qdrant Cloud 需要帶 API Key 才能連線，本機 Docker 版不需要，
    # 所以給預設值 None，本機開發時 .env 可以不填這個欄位。
    QDRANT_API_KEY: str | None = None
    COLLECTION_NAME_SONG: str = "song_features"
    COLLECTION_NAME_USER_HISTORY: str = "user_song_vectors"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.DATABASE_USERNAME}:{self.DATABASE_PASSWORD}@"
            f"{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()