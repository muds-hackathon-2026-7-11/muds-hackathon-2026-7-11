import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.consult_client import ConsultClient, ConsultTurn, get_consult_client
from api.db import get_db
from api.llm_logging import log_consult
from api.models import Seminar, User
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

    会話内容は chat_logs に保存する(#228)。今後の機能改善の根拠にするためで、
    学生には保存する旨を画面に表示する前提。継続会話自体はクライアントが送る
    history で成立しており、保存は分析のための副産物。

    ゼミ情報が無くLLMを呼んでいない場合は記録しない(課金も発生していない)。
    """
    context = await _seminars_context(db)
    if not context:
        return ConsultOut(reply=_NO_SEMINARS_REPLY, recommendations=[])

    history = [ConsultTurn(role=t.role, content=t.content) for t in payload.history]
    try:
        result = await client.consult(
            message=payload.message, history=history, seminars_context=context
        )
    except Exception as exc:
        # OpenAI失敗(quota/timeout/不正JSON等)でもエンドポイントは落とさない。
        logger.exception("consult LLM call failed")
        # 失敗も品質分析の材料になるので、理由を添えて残す。
        await log_consult(
            db,
            user_id=user.id,
            has_history=bool(history),
            message=payload.message,
            response=_ERROR_REPLY,
            recommendations=None,
            meta=None,
            error=f"{type(exc).__name__}: {exc}",
        )
        return ConsultOut(reply=_ERROR_REPLY, recommendations=[])

    await log_consult(
        db,
        user_id=user.id,
        has_history=bool(history),
        message=payload.message,
        response=result.reply,
        recommendations=result.recommendations or None,
        meta=result.meta,
    )
    return ConsultOut(
        reply=result.reply,
        recommendations=[
            ConsultRecommendation(seminar_name=r["seminar_name"], reason=r["reason"])
            for r in result.recommendations
        ],
    )
