import hashlib
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.config import settings
from api.db import get_db
from api.match_client import MatchClient, get_match_client
from api.models import MatchEvaluation, Seminar, User
from api.schemas import MatchOut

router = APIRouter(prefix="/seminars", tags=["match"])


def _input_hash(student_text: str, seminar_text: str, model: str) -> str:
    payload = "\x00".join([model, student_text, seminar_text])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@router.get("/{seminar_id}/match", response_model=MatchOut)
async def get_seminar_match(
    seminar_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    client: MatchClient = Depends(get_match_client),
) -> MatchOut:
    """ログイン中ユーザーの興味とゼミ内容のマッチ度(0-100)+理由を返す。

    結果は match_evaluations に (user, seminar, input_hash) でキャッシュし、
    同一入力なら再計算しない。
    """
    seminar = await db.get(Seminar, seminar_id)
    if seminar is None:
        raise HTTPException(status_code=404, detail="指定されたゼミが見つかりません。")

    student_text = (user.research_theme or "").strip()
    seminar_text = (seminar.description or "").strip()
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
        result = await client.evaluate(
            student_text=student_text, seminar_text=seminar_text
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
