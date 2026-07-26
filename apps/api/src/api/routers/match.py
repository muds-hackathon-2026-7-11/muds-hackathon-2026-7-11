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
    BulkMatchItem,
    MatchClient,
    RubricScores,
    SeminarInput,
    get_match_client,
)
from api.models import (
    MatchEvaluation,
    Seminar,
    User,
)
from api.schemas import (
    MatchOut,
    ReasonMatchesIn,
    ReasonMatchesOut,
    ReasonMatchRecommendation,
    ReasonMatchResult,
    SeminarMatchesOut,
    SeminarMatchOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/seminars", tags=["match"])

# LLM呼び出し失敗時(quota/timeout/不正JSON等)に返す説明。
_ERROR_MESSAGE = "現在マッチ度を算出できません。しばらくして再度お試しください。"
_NO_PROFILE_MESSAGE = "研究テーマ・興味分野が未設定のため、マッチ度を算出できません。"
_NO_SEMINARS_MESSAGE = "評価できるゼミ情報がありません。"
_NO_REASON_MESSAGE = "ゼミと志望理由を入力してから診断してください。"


def _input_hash(student_text: str, seminar_text: str, model: str) -> str:
    payload = "\x00".join([model, student_text, seminar_text])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def _student_text(db: AsyncSession, user: User) -> str:
    """学生側の入力テキスト = 研究概要のみ。

    興味分野タグはマッチ度判定では参照しない(研究概要の自由記述だけを根拠にする)。
    db は呼び出し側の互換のため受け取るが、タグ参照をやめたため現在は未使用。
    """
    return (user.research_theme or "").strip()


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
    query_text: str, named_texts: list[tuple[str, str]], model: str
) -> str:
    """一括採点のキャッシュキー。プロンプト版・モデル・問い合わせ文・全ゼミ内容から生成。"""
    parts = [MATCHES_PROMPT_VERSION, model, query_text]
    for name, text in named_texts:
        parts.append(name)
        parts.append(text)
    return hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()


def _feedback(item: BulkMatchItem) -> dict:
    return {
        "rubric": {
            "field": item.rubric.field,
            "method": item.rubric.method,
            "interest": item.rubric.interest,
            "style": item.rubric.style,
        },
        "summary": item.summary,
        "reasons": item.reasons,
    }


async def _load_scorable(db: AsyncSession) -> list[tuple[Seminar, str]]:
    """採点対象のゼミ(紹介文/資料要約があるもの)を id 昇順で返す。"""
    seminars = (await db.execute(select(Seminar).order_by(Seminar.id))).scalars().all()
    return [(s, text) for s in seminars if (text := _seminar_text(s))]


async def _score_all(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    client: MatchClient,
    query_text: str,
    scorable: list[tuple[Seminar, str]],
    model: str,
) -> dict[uuid.UUID, MatchEvaluation] | None:
    """query_text で scorable 全ゼミを1コール採点し、seminar_id -> 行 を返す。

    同一入力(bundle)のキャッシュがあれば再計算しない。LLM失敗時は None。
    """
    bundle = _bundle_hash(query_text, [(s.name, t) for (s, t) in scorable], model)
    cached = (
        (
            await db.execute(
                select(MatchEvaluation).where(
                    MatchEvaluation.user_id == user_id,
                    MatchEvaluation.input_hash == bundle,
                )
            )
        )
        .scalars()
        .all()
    )
    rows = {row.seminar_id: row for row in cached}
    if len(rows) >= len(scorable):
        return rows

    inputs = [
        SeminarInput(index=i, name=s.name, text=text)
        for i, (s, text) in enumerate(scorable)
    ]
    items = None
    for attempt in range(2):  # 不正JSON/失敗時は1回だけリトライ
        try:
            items = await client.evaluate_all(student_text=query_text, seminars=inputs)
            break
        except Exception:
            logger.exception("bulk match LLM call failed (attempt %d)", attempt + 1)
    if items is None:
        return None

    rows = {}
    for i, (seminar, _text) in enumerate(scorable):
        item = items.get(i)
        if item is None:  # モデルが一部ゼミを返さなかった場合はスキップ
            continue
        row = MatchEvaluation(
            user_id=user_id,
            seminar_id=seminar.id,
            input_hash=bundle,
            score=_weighted_total(item.rubric),
            feedback=_feedback(item),
        )
        db.add(row)
        rows[seminar.id] = row
    await db.flush()
    return rows


@router.get("/matches", response_model=SeminarMatchesOut)
async def get_seminar_matches(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    client: MatchClient = Depends(get_match_client),
) -> SeminarMatchesOut:
    """ログイン中ユーザーのプロフィールと全ゼミの適合度を、1コールでルーブリック
    採点し score降順で返す。"""
    student_text = await _student_text(db, user)
    if not student_text:
        return SeminarMatchesOut(results=[], message=_NO_PROFILE_MESSAGE)

    scorable = await _load_scorable(db)
    if not scorable:
        return SeminarMatchesOut(results=[], message=_NO_SEMINARS_MESSAGE)

    rows = await _score_all(
        db,
        user_id=user.id,
        client=client,
        query_text=student_text,
        scorable=scorable,
        model=settings.match_model,
    )
    if rows is None:
        return SeminarMatchesOut(results=[], message=_ERROR_MESSAGE)

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
        for seminar_id, row in rows.items()
        if seminar_id in name_by_id
    ]
    results.sort(key=lambda r: r.score, reverse=True)
    return SeminarMatchesOut(results=results, message=None)


@router.post("/reason-matches", response_model=ReasonMatchesOut)
async def post_reason_matches(
    payload: ReasonMatchesIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    client: MatchClient = Depends(get_match_client),
) -> ReasonMatchesOut:
    """各志望理由テキストで全ゼミを採点し、志望ごとに「選んだゼミのマッチ度」と
    「その理由に相性の良い他ゼミTop3(第1〜3志望を除外)」を返す(#119)。"""
    scorable = await _load_scorable(db)
    if not scorable:
        return ReasonMatchesOut(results=[], message=_NO_SEMINARS_MESSAGE)

    name_by_id = {s.id: s.name for (s, _text) in scorable}
    chosen_ids = {c.seminar_id for c in payload.choices}

    results: list[ReasonMatchResult] = []
    llm_failed = False
    had_reason = False
    for choice in payload.choices:
        reason = choice.reason.strip()
        if not reason:
            continue
        had_reason = True
        # 研究概要は使わず、その志望の理由だけを問い合わせ文にする(#196)。
        # ゼミ移動時は研究内容も変わることが多いため、志望理由のみを根拠にする。
        query = f"志望理由: {reason}"
        rows = await _score_all(
            db,
            user_id=user.id,
            client=client,
            query_text=query,
            scorable=scorable,
            model=settings.match_model,
        )
        if rows is None:
            llm_failed = True
            continue

        selected = rows.get(choice.seminar_id)
        others = sorted(
            (
                row
                for sid, row in rows.items()
                if sid not in chosen_ids and sid in name_by_id
            ),
            key=lambda r: r.score,
            reverse=True,
        )[:3]
        results.append(
            ReasonMatchResult(
                seminar_id=choice.seminar_id,
                seminar_name=name_by_id.get(choice.seminar_id, ""),
                selected_score=selected.score if selected else None,
                rubric=(selected.feedback or {}).get("rubric", {}) if selected else {},
                summary=(selected.feedback or {}).get("summary", "")
                if selected
                else "",
                recommendations=[
                    ReasonMatchRecommendation(
                        seminar_id=row.seminar_id,
                        seminar_name=name_by_id[row.seminar_id],
                        score=row.score,
                    )
                    for row in others
                ],
            )
        )

    message: str | None = None
    if not results:
        if llm_failed:
            message = _ERROR_MESSAGE
        elif not had_reason:
            message = _NO_REASON_MESSAGE
        else:
            message = _NO_SEMINARS_MESSAGE
    return ReasonMatchesOut(results=results, message=message)


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
