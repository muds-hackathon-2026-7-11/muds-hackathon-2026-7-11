from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_db
from api.models import User
from api.schemas import UserExistsOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/exists", response_model=UserExistsOut)
async def check_user_exists(
    email: str, db: AsyncSession = Depends(get_db)
) -> UserExistsOut:
    """メールアドレスがusersに事前登録済みか返す(ログイン許可判定用・認証不要)。

    事前登録済みのメールアドレスのみログインを許可するために、
    NextAuthのsignInコールバック(認証成立前=セッション無し)から呼ばれる。
    """
    result = await db.execute(select(User).where(User.email == email.strip().lower()))
    return UserExistsOut(exists=result.scalar_one_or_none() is not None)
