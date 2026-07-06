from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_db
from api.models import ResearchTag
from api.schemas import ResearchTagOut

router = APIRouter(prefix="/research-tags", tags=["research-tags"])


@router.get("", response_model=list[ResearchTagOut])
async def list_research_tags(
    db: AsyncSession = Depends(get_db),
) -> list[ResearchTag]:
    """興味分野タグのマスタ一覧(選択肢)を返す。"""
    result = await db.execute(select(ResearchTag).order_by(ResearchTag.sort_order))
    return list(result.scalars().all())
