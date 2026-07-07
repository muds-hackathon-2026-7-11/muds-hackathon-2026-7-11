import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.consult_client import ConsultClient, ConsultTurn, get_consult_client
from api.db import get_db
from api.models import ChatLog, Seminar, User
from api.schemas import ConsultIn, ConsultOut, ConsultRecommendation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/consult", tags=["consult"])

# ゼミ情報が全く無いと推薦しようがないため、その旨を返す固定文言。
_NO_SEMINARS_REPLY = (
    "現在ご案内できるゼミ情報がありません。運営にお問い合わせください。"
)
# LLM呼び出し失敗時のフォールバック。
_ERROR_REPLY = "現在相談アシスタントを利用できません。しばらくして再度お試しください。"


async def _seminars_context(db: AsyncSession) -> str:
    """全ゼミの名前・紹介・(あれば)資料要約を1つの文脈テキストにまとめる。"""
    result = await db.execute(select(Seminar).order_by(Seminar.name))
    blocks: list[str] = []
    for s in result.scalars().all():
        parts = [f"## {s.name}"]
        if s.description:
            parts.append(s.description.strip())
        if s.knowledge:
            parts.append(f"[資料要約]\n{s.knowledge.strip()}")
        blocks.append("\n".join(parts))
    return "\n\n".join(blocks)


@router.post("", response_model=ConsultOut)
async def consult(
    payload: ConsultIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    client: ConsultClient = Depends(get_consult_client),
) -> ConsultOut:
    """学生の自由文相談に対し、ゼミ情報から適したゼミを理由付きで推薦する。

    やりとりは chat_logs に追記して残す(継続会話・振り返り用)。
    """
    context = await _seminars_context(db)
    if not context:
        return ConsultOut(reply=_NO_SEMINARS_REPLY, recommendations=[])

    history = [ConsultTurn(role=t.role, content=t.content) for t in payload.history]
    try:
        result = await client.consult(
            message=payload.message, history=history, seminars_context=context
        )
    except Exception:
        # OpenAI失敗(quota/timeout/不正JSON等)でもエンドポイントは落とさない。
        logger.exception("consult LLM call failed")
        return ConsultOut(reply=_ERROR_REPLY, recommendations=[])

    db.add(
        ChatLog(
            user_id=user.id,
            message=payload.message,
            response=result.reply,
            recommendations=result.recommendations,
        )
    )
    await db.flush()

    return ConsultOut(
        reply=result.reply,
        recommendations=[
            ConsultRecommendation(seminar_name=r["seminar_name"], reason=r["reason"])
            for r in result.recommendations
        ],
    )
