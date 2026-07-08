import hashlib
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.config import settings
from api.db import get_db
from api.match_client import (
    MATCHES_PROMPT_VERSION,
    MatchClient,
    RubricScores,
    SeminarInput,
    get_match_client,
)
from api.models import (
    MatchEvaluation,
    ResearchTag,
    Seminar,
    User,
    UserInterestTag,
)
from api.schemas import MatchOut, SeminarMatchesOut, SeminarMatchOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/seminars", tags=["match"])

# LLM呼び出し失敗時(quota/timeout/不正JSON等)に返す説明。
_ERROR_MESSAGE = "現在マッチ度を算出できません。しばらくして再度お試しください。"
_NO_PROFILE_MESSAGE = "研究テーマ・興味分野が未設定のため、マッチ度を算出できません。"
_NO_SEMINARS_MESSAGE = "評価できるゼミ情報がありません。"


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


def _normalized_weights() -> tuple[float, float, float, float]:
    """(field, method, interest, style) の重みを合計1へ正規化して返す。"""
    field = settings.match_weight_field
    method = settings.match_weight_method
    interest = settings.match_weight_interest
    style = settings.match_weight_style
    total = field + method + interest + style or 1.0
    return (field / total, method / total, interest / total, style / total)


def _weighted_total(rubric: RubricScores) -> int:
    wf, wm, wi, ws = _normalized_weights()
    total = (
        wf * rubric.field
        + wm * rubric.method
        + wi * rubric.interest
        + ws * rubric.style
    )
    return max(0, min(100, round(total)))


def _bundle_hash(
    student_text: str, named_texts: list[tuple[str, str]], model: str
) -> str:
    """一括採点のキャッシュキー。プロンプト版・モデル・学生・全ゼミ内容から生成。"""
    parts = [MATCHES_PROMPT_VERSION, model, student_text]
    for name, text in named_texts:
        parts.append(name)
        parts.append(text)
    return hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()


@router.get("/matches", response_model=SeminarMatchesOut)
async def get_seminar_matches(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    client: MatchClient = Depends(get_match_client),
) -> SeminarMatchesOut:
    """ログイン中ユーザーと全ゼミの適合度を、1回のLLMコールでルーブリック採点し
    score降順で返す。

    観点別(field/method/interest/style)を採点させ、総合スコアはサーバ側で
    重み付け(設定値)して算出する。結果は match_evaluations に、全ゼミ内容から
    導いた input_hash(bundle) で保存し、同一入力なら再計算しない。
    """
    student_text = await _student_text(db, user)
    if not student_text:
        return SeminarMatchesOut(results=[], message=_NO_PROFILE_MESSAGE)

    seminars = (await db.execute(select(Seminar).order_by(Seminar.id))).scalars().all()
    # 紹介文・資料要約が無いゼミは採点対象から外す(判断材料が無いため)。
    scorable = [(s, _seminar_text(s)) for s in seminars]
    scorable = [(s, text) for (s, text) in scorable if text]
    if not scorable:
        return SeminarMatchesOut(results=[], message=_NO_SEMINARS_MESSAGE)

    bundle = _bundle_hash(
        student_text, [(s.name, text) for (s, text) in scorable], settings.match_model
    )

    cached_rows = (
        (
            await db.execute(
                select(MatchEvaluation).where(
                    MatchEvaluation.user_id == user.id,
                    MatchEvaluation.input_hash == bundle,
                )
            )
        )
        .scalars()
        .all()
    )
    rows_by_seminar = {row.seminar_id: row for row in cached_rows}

    # 全採点対象ぶんのキャッシュが揃っていれば再計算しない。
    # (1リクエスト内でまとめてcommitするため、部分的な行が残ることはない)
    if len(rows_by_seminar) < len(scorable):
        inputs = [
            SeminarInput(index=i, name=s.name, text=text)
            for i, (s, text) in enumerate(scorable)
        ]
        items = None
        for attempt in range(2):  # 不正JSON/失敗時は1回だけリトライ
            try:
                items = await client.evaluate_all(
                    student_text=student_text, seminars=inputs
                )
                break
            except Exception:
                logger.exception("bulk match LLM call failed (attempt %d)", attempt + 1)
        if items is None:
            return SeminarMatchesOut(results=[], message=_ERROR_MESSAGE)

        rows_by_seminar = {}
        for i, (seminar, _text) in enumerate(scorable):
            item = items.get(i)
            if item is None:  # モデルが一部ゼミを返さなかった場合はスキップ
                continue
            row = MatchEvaluation(
                user_id=user.id,
                seminar_id=seminar.id,
                input_hash=bundle,
                score=_weighted_total(item.rubric),
                feedback={
                    "rubric": {
                        "field": item.rubric.field,
                        "method": item.rubric.method,
                        "interest": item.rubric.interest,
                        "style": item.rubric.style,
                    },
                    "summary": item.summary,
                    "reasons": item.reasons,
                },
            )
            db.add(row)
            rows_by_seminar[seminar.id] = row
        await db.flush()

    name_by_id = {s.id: s.name for (s, _text) in scorable}
    results = [
        SeminarMatchOut(
            seminar_id=seminar_id,
            seminar_name=name_by_id.get(seminar_id, ""),
            score=row.score,
            rubric=(row.feedback or {}).get("rubric", {}),
            summary=(row.feedback or {}).get("summary", ""),
            reasons=(row.feedback or {}).get("reasons", []),
        )
        for seminar_id, row in rows_by_seminar.items()
        if seminar_id in name_by_id
    ]
    results.sort(key=lambda r: r.score, reverse=True)
    return SeminarMatchesOut(results=results, message=None)


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
