import uuid

import pytest
from sqlalchemy import func, select

from api import auth
from api.auth import get_current_user
from api.main import app
from api.models import ChatLog, Seminar, User, UserRole

pytestmark = pytest.mark.asyncio


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _make_student(db_session) -> User:
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name=_unique("name"),
        role=UserRole.student,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_seminar(db_session, *, description: str | None = "紹介") -> Seminar:
    seminar = Seminar(name=_unique("seminar"), description=description)
    db_session.add(seminar)
    await db_session.flush()
    return seminar


def _authenticate_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


async def _chat_log_count(db_session, user_id) -> int:
    result = await db_session.execute(
        select(func.count()).select_from(ChatLog).where(ChatLog.user_id == user_id)
    )
    count: int = result.scalar_one()
    return count


async def test_consult_returns_reply_and_logs(
    client, db_session, fake_consult_client
) -> None:
    user = await _make_student(db_session)
    await _make_seminar(db_session, description="機械学習のゼミ")
    _authenticate_as(user)

    resp = await client.post("/consult", json={"message": "AIに興味があります"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "テスト用の相談返答です。"
    assert body["recommendations"] == [
        {"seminar_name": "テストゼミ", "reason": "理由A"}
    ]
    # 会話が chat_logs に残る
    assert await _chat_log_count(db_session, user.id) == 1


async def test_consult_passes_message_history_and_context(
    client, db_session, fake_consult_client
) -> None:
    user = await _make_student(db_session)
    seminar = await _make_seminar(db_session, description="推薦システムのゼミ")
    _authenticate_as(user)

    resp = await client.post(
        "/consult",
        json={
            "message": "続きです",
            "history": [{"role": "user", "content": "前の質問"}],
        },
    )

    assert resp.status_code == 200
    call = fake_consult_client.calls[0]
    assert call["message"] == "続きです"
    assert [t.role for t in call["history"]] == ["user"]
    # 文脈に全ゼミ情報(名前・紹介)が含まれる
    assert seminar.name in call["seminars_context"]
    assert "推薦システムのゼミ" in call["seminars_context"]


async def test_consult_without_seminars_returns_guidance(
    client, db_session, fake_consult_client
) -> None:
    user = await _make_student(db_session)  # ゼミを作らない
    _authenticate_as(user)

    resp = await client.post("/consult", json={"message": "相談です"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["recommendations"] == []
    assert "ゼミ情報" in body["reply"]
    # ゼミが無いときはLLMを呼ばず、ログも残さない
    assert fake_consult_client.calls == []
    assert await _chat_log_count(db_session, user.id) == 0


async def test_consult_graceful_when_llm_fails(
    client, db_session, fake_consult_client, monkeypatch
) -> None:
    user = await _make_student(db_session)
    await _make_seminar(db_session)
    _authenticate_as(user)

    async def _boom(*, message, history, seminars_context):
        raise RuntimeError("OpenAI down (429)")

    monkeypatch.setattr(fake_consult_client, "consult", _boom)

    resp = await client.post("/consult", json={"message": "相談です"})

    # LLM失敗でも500にせず、フォールバック文言を返す
    assert resp.status_code == 200
    assert resp.json()["recommendations"] == []
    # 失敗時はログを残さない
    assert await _chat_log_count(db_session, user.id) == 0


async def test_consult_requires_authentication(client, monkeypatch) -> None:
    monkeypatch.setattr(auth.settings, "auth_dev_mode", False)
    resp = await client.post("/consult", json={"message": "相談です"})
    assert resp.status_code == 401
