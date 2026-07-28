"""LLM入出力のログ保存(#228)。

今後の機能改善(プロンプト調整・ゼミ資料の過不足の発見・診断精度の検証)の
根拠にするため、相談チャットとマッチ度診断の入出力を残す。

**ログ保存の失敗で相談・診断そのものを落とさない。** 分析用の副産物であり、
学生から見える機能を止める理由にはならない。

そのためINSERTはSAVEPOINT(begin_nested)で囲む。単に例外を握るだけでは不十分で、
flushが失敗したセッションは「要ロールバック」状態になり、get_db が最後に行う
commit がそこで失敗して結局500になってしまう。SAVEPOINTならログの挿入だけを
巻き戻し、同じリクエストの他の変更(採点結果のキャッシュ等)は生かせる。
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.consult_client import LlmCallMeta
from api.models import ChatLog, MatchFeature, MatchLog

logger = logging.getLogger(__name__)

# 直近の発話から この時間内 なら同じ会話の続きとみなす。クライアントは
# session_id を送ってこないため、サーバ側でこの窓を使って束ねる。
_SESSION_GAP = timedelta(hours=6)


async def resolve_session(
    db: AsyncSession, *, user_id: uuid.UUID, has_history: bool
) -> tuple[uuid.UUID, int]:
    """この発話が属する (session_id, turn_index) を決める。

    クライアントから会話IDが送られてこないため、次の2段で判定する:

    1. リクエストの history が空なら「新しい会話の1通目」なので新規セッション。
       画面のリセットボタンを押した直後もこれに該当する。
    2. history があれば直近の発話と同じ会話とみなす。ただし前回から
       _SESSION_GAP 以上空いていれば別の会話として扱う(ブラウザを閉じて
       翌日に開いた場合など、history が残っていても別セッションにする)。

    既知の限界: 同じ学生が複数タブで同時に相談すると1つのセッションに
    混ざる。分析用途では許容する。
    """
    if not has_history:
        return uuid.uuid4(), 0

    row = (
        await db.execute(
            select(ChatLog.session_id, ChatLog.turn_index, ChatLog.created_at)
            .where(ChatLog.user_id == user_id)
            .order_by(ChatLog.created_at.desc())
            .limit(1)
        )
    ).first()
    if row is None:
        # history はあるがログが無い = ログ機能を入れる前から続いている会話。
        return uuid.uuid4(), 0

    session_id, turn_index, created_at = row
    if datetime.now(UTC) - created_at >= _SESSION_GAP:
        return uuid.uuid4(), 0
    return session_id, turn_index + 1


async def log_consult(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    has_history: bool,
    message: str,
    response: str,
    recommendations: list[dict] | None,
    meta: LlmCallMeta | None,
    error: str | None = None,
) -> None:
    """相談チャットの1発話を保存する。失敗しても例外は投げない。"""
    try:
        session_id, turn_index = await resolve_session(
            db, user_id=user_id, has_history=has_history
        )
        async with db.begin_nested():
            db.add(
                ChatLog(
                    user_id=user_id,
                    session_id=session_id,
                    turn_index=turn_index,
                    message=message,
                    response=response,
                    recommendations=recommendations,
                    model=meta.model if meta else None,
                    prompt_tokens=meta.prompt_tokens if meta else None,
                    completion_tokens=meta.completion_tokens if meta else None,
                    cached_tokens=meta.cached_tokens if meta else None,
                    latency_ms=meta.latency_ms if meta else None,
                    error=error,
                )
            )
    except Exception:
        logger.exception("failed to save chat log (consult continues)")


async def log_match(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    feature: MatchFeature,
    query_text: str,
    bundle_hash: str | None,
    prompt_version: str | None,
    meta: LlmCallMeta | None,
    response_json: dict | list | None,
    error: str | None = None,
) -> None:
    """マッチ度診断のLLM 1コール分を保存する。失敗しても例外は投げない。"""
    try:
        async with db.begin_nested():
            db.add(
                MatchLog(
                    user_id=user_id,
                    feature=feature,
                    query_text=query_text,
                    bundle_hash=bundle_hash,
                    prompt_version=prompt_version,
                    model=meta.model if meta else None,
                    response_json=response_json,
                    prompt_tokens=meta.prompt_tokens if meta else None,
                    completion_tokens=meta.completion_tokens if meta else None,
                    cached_tokens=meta.cached_tokens if meta else None,
                    latency_ms=meta.latency_ms if meta else None,
                    error=error,
                )
            )
    except Exception:
        logger.exception("failed to save match log (diagnosis continues)")


async def count_chat_logs(db: AsyncSession, user_id: uuid.UUID) -> int:
    """テスト・確認用。指定ユーザーの相談ログ件数。"""
    result = await db.execute(
        select(func.count()).select_from(ChatLog).where(ChatLog.user_id == user_id)
    )
    count: int = result.scalar_one()
    return count
