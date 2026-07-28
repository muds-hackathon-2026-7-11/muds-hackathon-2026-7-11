"""LLM入出力ログ(#228)。

「保存されること」だけでなく「保存に失敗しても学生向けの機能が落ちないこと」
「課金が発生していない経路では記録しないこと」を固定する。
"""

import uuid

import pytest
from sqlalchemy import select

from api.auth import get_current_user
from api.main import app
from api.models import ChatLog, MatchFeature, MatchLog, Seminar, User, UserRole

pytestmark = pytest.mark.asyncio


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _make_student(db_session) -> User:
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name=_unique("name"),
        role=UserRole.student,
        research_theme="推薦システムに興味",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_seminar(db_session) -> Seminar:
    seminar = Seminar(name=_unique("seminar"), description="ゼミ紹介文")
    db_session.add(seminar)
    await db_session.flush()
    return seminar


def _authenticate_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


async def _chat_logs(db_session, user_id) -> list[ChatLog]:
    result = await db_session.execute(
        select(ChatLog).where(ChatLog.user_id == user_id).order_by(ChatLog.turn_index)
    )
    return list(result.scalars().all())


async def _match_logs(db_session, user_id) -> list[MatchLog]:
    result = await db_session.execute(
        select(MatchLog).where(MatchLog.user_id == user_id)
    )
    return list(result.scalars().all())


# --- 相談チャット ---


async def test_consult_records_message_response_and_metrics(
    client, db_session, fake_consult_client
) -> None:
    user = await _make_student(db_session)
    await _make_seminar(db_session)
    _authenticate_as(user)

    await client.post("/consult", json={"message": "AIに興味があります"})

    logs = await _chat_logs(db_session, user.id)
    assert len(logs) == 1
    log = logs[0]
    assert log.message == "AIに興味があります"
    assert log.response == "テスト用の相談返答です。"
    assert log.recommendations == [{"seminar_name": "テストゼミ", "reason": "理由A"}]
    assert log.turn_index == 0
    assert log.error is None


async def test_consult_groups_turns_into_one_session(
    client, db_session, fake_consult_client
) -> None:
    """history が付いた2通目は、1通目と同じ session_id に束ねる。"""
    user = await _make_student(db_session)
    await _make_seminar(db_session)
    _authenticate_as(user)

    await client.post("/consult", json={"message": "1通目"})
    await client.post(
        "/consult",
        json={
            "message": "2通目",
            "history": [
                {"role": "user", "content": "1通目"},
                {"role": "assistant", "content": "テスト用の相談返答です。"},
            ],
        },
    )

    logs = await _chat_logs(db_session, user.id)
    assert len(logs) == 2
    assert logs[0].session_id == logs[1].session_id
    assert [log.turn_index for log in logs] == [0, 1]


async def test_consult_starts_new_session_when_history_is_empty(
    client, db_session, fake_consult_client
) -> None:
    """history が空＝画面のリセット後なので、別の会話として扱う。"""
    user = await _make_student(db_session)
    await _make_seminar(db_session)
    _authenticate_as(user)

    await client.post("/consult", json={"message": "1回目の相談"})
    await client.post("/consult", json={"message": "リセット後の相談"})

    logs = await _chat_logs(db_session, user.id)
    assert len(logs) == 2
    assert logs[0].session_id != logs[1].session_id
    assert all(log.turn_index == 0 for log in logs)


async def test_consult_records_error_when_llm_fails(
    client, db_session, fake_consult_client, monkeypatch
) -> None:
    user = await _make_student(db_session)
    await _make_seminar(db_session)
    _authenticate_as(user)

    async def _boom(*, message, history, seminars_context):
        raise RuntimeError("OpenAI down (429)")

    monkeypatch.setattr(fake_consult_client, "consult", _boom)

    resp = await client.post("/consult", json={"message": "相談です"})

    assert resp.status_code == 200
    logs = await _chat_logs(db_session, user.id)
    assert len(logs) == 1
    assert "OpenAI down" in (logs[0].error or "")


async def test_consult_survives_logging_failure(
    client, db_session, fake_consult_client, monkeypatch
) -> None:
    """ログ保存の途中で落ちても相談そのものは成功させる。"""
    user = await _make_student(db_session)
    await _make_seminar(db_session)
    _authenticate_as(user)

    async def _broken(*args, **kwargs):
        raise RuntimeError("session lookup failed")

    # log_consult 自体ではなく、その内部を壊す。関数ごと差し替えると
    # log_consult が持つ例外処理を迂回してしまい、防御機構を検証できない。
    monkeypatch.setattr("api.llm_logging.resolve_session", _broken)

    resp = await client.post("/consult", json={"message": "相談です"})

    assert resp.status_code == 200
    assert resp.json()["reply"] == "テスト用の相談返答です。"
    assert await _chat_logs(db_session, user.id) == []


async def test_logging_db_error_does_not_break_the_session(db_session) -> None:
    """INSERTがDBレベルで失敗しても、同じセッションの他の操作を巻き込まない。

    SAVEPOINTで囲んでいないと、flush失敗でセッションが要ロールバック状態になり、
    get_db の commit がそこで落ちて結局500になる。存在しないuser_idで外部キー
    違反を起こし、その後も同じセッションが使えることを確かめる。
    """
    from api.llm_logging import log_consult

    await log_consult(
        db_session,
        user_id=uuid.uuid4(),  # 存在しないユーザー = FK違反
        has_history=False,
        message="壊れる想定",
        response="返答",
        recommendations=None,
        meta=None,
    )

    # セッションが生きていれば、続けてクエリを投げられる。
    seminar = await _make_seminar(db_session)
    assert seminar.id is not None


# --- マッチ度診断 ---


async def test_reason_matches_records_query_and_response(
    client, db_session, fake_match_client
) -> None:
    user = await _make_student(db_session)
    seminar = await _make_seminar(db_session)
    _authenticate_as(user)

    await client.post(
        "/seminars/reason-matches",
        json={
            "choices": [{"seminar_id": str(seminar.id), "reason": "機械学習をやりたい"}]
        },
    )

    logs = await _match_logs(db_session, user.id)
    assert len(logs) == 1
    log = logs[0]
    assert log.feature == MatchFeature.reason_match
    assert "機械学習をやりたい" in log.query_text
    assert log.bundle_hash
    assert log.prompt_version
    assert log.error is None


async def test_match_cache_hit_is_not_recorded(
    client, db_session, fake_match_client
) -> None:
    """キャッシュヒット時はOpenAIを呼んでいないので記録しない。"""
    user = await _make_student(db_session)
    seminar = await _make_seminar(db_session)
    _authenticate_as(user)

    body = {"choices": [{"seminar_id": str(seminar.id), "reason": "同じ理由"}]}
    await client.post("/seminars/reason-matches", json=body)
    await client.post("/seminars/reason-matches", json=body)

    assert len(fake_match_client.bulk_calls) == 1
    assert len(await _match_logs(db_session, user.id)) == 1


async def test_single_match_is_recorded(client, db_session, fake_match_client) -> None:
    user = await _make_student(db_session)
    seminar = await _make_seminar(db_session)
    _authenticate_as(user)

    await client.get(f"/seminars/{seminar.id}/match")

    logs = await _match_logs(db_session, user.id)
    assert len(logs) == 1
    assert logs[0].feature == MatchFeature.single_match
