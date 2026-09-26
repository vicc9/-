from sqlmodel import Session, create_engine
from app.core.config import settings

# 根據 settings.DATABASE_URL 建立 SQLModel 的資料庫引擎
engine = create_engine(settings.DATABASE_URL)

def get_session():
    """
    提供一個資料庫會話 (Session) 的依賴注入函式。
    確保資源釋放和安全。
    """
    with Session(engine) as session:
        yield session