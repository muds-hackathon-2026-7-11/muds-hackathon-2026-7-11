from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_db
from api.models import Seminar
from api.schemas import SeminarOut

router = APIRouter(prefix="/seminars", tags=["seminars"])


@router.get("", response_model=list[SeminarOut])
async def list_seminars(db: AsyncSession = Depends(get_db)) -> list[Seminar]:
    result = await db.execute(select(Seminar).order_by(Seminar.name))
    return list(result.scalars().all())
