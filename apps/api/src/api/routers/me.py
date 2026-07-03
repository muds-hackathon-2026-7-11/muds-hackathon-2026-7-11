from fastapi import APIRouter, Depends

from api.auth import get_current_user
from api.models import User
from api.schemas import MeOut

router = APIRouter(tags=["auth"])


@router.get("/me", response_model=MeOut)
async def read_me(user: User = Depends(get_current_user)) -> User:
    """認証済みユーザー自身の情報を返す。"""
    return user
