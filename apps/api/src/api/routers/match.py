import hashlib
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.config import settings
from api.db import get_db
from api.match_client import MatchClient, get_match_client
from api.models import (
    MatchEvaluation,
    ResearchTag,
    Seminar,
    User,
    UserInterestTag,
)
from api.schemas import MatchOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/seminars", tags=["match"])

# LLM呼び出し失敗時(quota/timeout/不正JSON等)に返す説明。
_ERROR_MESSAGE = "現在マッチ度を算出できません。しばらくして再度お試しください。"


def _input_hash(student_text: str, seminar_text: str, model: str) -> str:
    payload = "\x00".join([model, student_text, seminar_text])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def _student_text(db: AsyncSession, user: User) -> str:
    """学生側の入力テキスト = 研究概要 + 興味分野タグ。"""
    parts: list[str] = []
    if user.research_theme:
        parts.append(user.research_theme.strip())
    tag_rows = await db.execute(
        select(ResearchTag.name)
        .join(UserInterestTag, UserInterestTag.tag_id == ResearchTag.id)
        .where(UserInterestTag.user_id == user.id)
        .order_by(ResearchTag.sort_order)
    )
    tags = [name for (name,) in tag_rows.all()]
    if tags:
        parts.append("興味分野: " + "、".join(tags))
    return "\n".join(parts).strip()


def _seminar_text(seminar: Seminar) -> str:
    """ゼミ側の入力テキスト = 紹介文 + 資料要約(あれば)。"""
    parts: list[str] = []
    if seminar.description:
        parts.append(seminar.description.strip())
    if seminar.knowledge:
        parts.append(f"[資料要約]\n{seminar.knowledge.strip()}")
    return "\n".join(parts).strip()


@router.get("/{seminar_id}/match", response_model=MatchOut)
async def get_seminar_match(
    seminar_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    client: MatchClient = Depends(get_match_client),
) -> MatchOut:
    """ログイン中ユーザーの興味とゼミ内容のマッチ度(0-100)+理由を返す。

    学生側は研究概要+興味分野タグ、ゼミ側は紹介文+資料要約(PDF由来)を用いる。
    結果は match_evaluations に (user, seminar, input_hash) でキャッシュし、
    同一入力なら再計算しない。
    """
    seminar = await db.get(Seminar, seminar_id)
    if seminar is None:
        raise HTTPException(status_code=404, detail="指定されたゼミが見つかりません。")

    student_text = await _student_text(db, user)
    seminar_text = _seminar_text(seminar)
    if not student_text or not seminar_text:
        return MatchOut(
            seminar_id=seminar_id,
            score=None,
            feedback=None,
            message="研究テーマまたはゼミ紹介が未設定のため、マッチ度を算出できません。",
        )

    input_hash = _input_hash(student_text, seminar_text, settings.match_model)
    cached = await db.execute(
        select(MatchEvaluation).where(
            MatchEvaluation.user_id == user.id,
            MatchEvaluation.seminar_id == seminar_id,
            MatchEvaluation.input_hash == input_hash,
        )
    )
    evaluation = cached.scalar_one_or_none()
    if evaluation is None:
        try:
            result = await client.evaluate(
                student_text=student_text, seminar_text=seminar_text
            )
        except Exception:
            # OpenAI失敗でも500にせず、算出不可のメッセージを返す。
            logger.exception("match LLM call failed")
            return MatchOut(
                seminar_id=seminar_id, score=None, feedback=None, message=_ERROR_MESSAGE
            )
        evaluation = MatchEvaluation(
            user_id=user.id,
            seminar_id=seminar_id,
            input_hash=input_hash,
            score=result.score,
            feedback=result.feedback,
        )
        db.add(evaluation)
        await db.flush()

    return MatchOut(
        seminar_id=seminar_id,
        score=evaluation.score,
        feedback=evaluation.feedback,
        message=None,
    )
