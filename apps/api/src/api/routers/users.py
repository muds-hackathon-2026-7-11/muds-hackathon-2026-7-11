from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import require_internal_secret
from api.db import get_db
from api.models import User
from api.schemas import UserExistsOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/exists",
    response_model=UserExistsOut,
    dependencies=[Depends(require_internal_secret)],
)
async def check_user_exists(
    email: str, db: AsyncSession = Depends(get_db)
) -> UserExistsOut:
    """メールアドレスがusersに事前登録済みか返す(ログイン許可判定用)。

    事前登録済みのメールアドレスのみログインを許可するために、
    NextAuthのsignInコールバック(認証成立前=セッション無し)から呼ばれる。
    JWT認証は使えないため、web-api間の合言葉(require_internal_secret)で
    外部からの直接アクセス(学籍番号の総当たり等)を防ぐ。
    """
    result = await db.execute(select(User).where(User.email == email.strip().lower()))
    return UserExistsOut(exists=result.scalar_one_or_none() is not None)
