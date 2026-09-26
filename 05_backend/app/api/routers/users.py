from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from app.core.database import get_session
from app.services.user_vector_service import UserVectorService
from typing import List, Dict, Any

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

@router.get("/{user_id}/recommendations", response_model=List[Dict[str, Any]])
async def get_recommendations(
    user_id: str,
    limit: int = 10,
    db: Session = Depends(get_session)
):
    """
    根據用戶 ID 獲取推薦歌曲列表。
    - **user_id**: 要獲取推薦的用戶 ID (e.g., 'b64cdd1a0bd907e5e00b39e345194768e330d652').
    - **limit**: 推薦歌曲的數量限制 (預設 10).
    """
    service = UserVectorService(db)
    try:
        # 調用服務層的異步方法來獲取推薦歌曲
        recommendations = await service.get_recommended_songs(user_id, limit)
        return recommendations
    except ValueError as e:
        # 捕獲業務邏輯錯誤 (如查無向量、查無歌曲)，回傳 404 Not Found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        # 捕獲任何其他未預期的錯誤，回傳 500 Internal Server Error
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")


@router.get("/", response_model=List[str])
async def get_users(
    db: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 10,
):
    """
    獲取所有用戶的列表。
    """
    service = UserVectorService(db)
    try:
        users = await service.get_users(skip, limit)
        return users
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error fetching users: {e}")