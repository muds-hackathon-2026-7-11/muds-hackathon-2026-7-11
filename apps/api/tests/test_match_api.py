import uuid

import pytest

from api import auth
from api.auth import get_current_user
from api.main import app
from api.models import ResearchTag, Seminar, User, UserInterestTag, UserRole

pytestmark = pytest.mark.asyncio


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _make_user(db_session, *, research_theme: str | None) -> User:
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name=_unique("name"),
        role=UserRole.student,
        research_theme=research_theme,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_seminar(db_session, *, description: str | None) -> Seminar:
    seminar = Seminar(name=_unique("seminar"), description=description)
    db_session.add(seminar)
    await db_session.flush()
    return seminar


def _authenticate_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


async def test_match_returns_score_and_feedback(
    client, db_session, fake_match_client
) -> None:
    user = await _make_user(db_session, research_theme="画像認識と深層学習")
    seminar = await _make_seminar(db_session, description="機械学習・深層学習のゼミ")
    _authenticate_as(user)

    resp = await client.get(f"/seminars/{seminar.id}/match")

    assert resp.status_code == 200
    body = resp.json()
    assert body["score"] == 75
    assert body["feedback"]["summary"] == "テスト用の評価"
    assert body["message"] is None
    # LLM(Fake)には研究テーマとゼミ紹介がそのまま渡る
    assert fake_match_client.calls == [
        ("画像認識と深層学習", "機械学習・深層学習のゼミ")
    ]


async def test_match_is_cached(client, db_session, fake_match_client) -> None:
    user = await _make_user(db_session, research_theme="分散システム")
    seminar = await _make_seminar(db_session, description="データベースのゼミ")
    _authenticate_as(user)

    first = await client.get(f"/seminars/{seminar.id}/match")
    second = await client.get(f"/seminars/{seminar.id}/match")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["score"] == second.json()["score"] == 75
    # 2回目はキャッシュから返り、LLMは1回しか呼ばれない
    assert len(fake_match_client.calls) == 1


async def test_match_null_when_no_research_theme(
    client, db_session, fake_match_client
) -> None:
    user = await _make_user(db_session, research_theme=None)
    seminar = await _make_seminar(db_session, description="ゼミ紹介あり")
    _authenticate_as(user)

    resp = await client.get(f"/seminars/{seminar.id}/match")

    assert resp.status_code == 200
    body = resp.json()
    assert body["score"] is None
    assert body["feedback"] is None
    assert body["message"]
    # 算出不可のときはLLMを呼ばない
    assert fake_match_client.calls == []


async def test_match_seminar_not_found(client, db_session) -> None:
    _authenticate_as(await _make_user(db_session, research_theme="x"))
    resp = await client.get(f"/seminars/{uuid.uuid4()}/match")
    assert resp.status_code == 404


async def test_match_requires_authentication(client, monkeypatch) -> None:
    monkeypatch.setattr(auth.settings, "auth_dev_mode", False)
    resp = await client.get(f"/seminars/{uuid.uuid4()}/match")
    assert resp.status_code == 401


async def test_match_enriches_with_interest_tags_and_knowledge(
    client, db_session, fake_match_client
) -> None:
    # 学生側は研究概要+興味タグ、ゼミ側は紹介文+資料要約(PDF由来)が渡る。
    user = await _make_user(db_session, research_theme="推薦システム")
    tag = ResearchTag(name="自然言語処理", category="AI", sort_order=1)
    db_session.add(tag)
    await db_session.flush()
    db_session.add(UserInterestTag(user_id=user.id, tag_id=tag.id))
    seminar = await _make_seminar(db_session, description="AIのゼミ")
    seminar.knowledge = "深層学習と推薦を扱う研究室"
    await db_session.flush()
    _authenticate_as(user)

    resp = await client.get(f"/seminars/{seminar.id}/match")

    assert resp.status_code == 200
    student_text, seminar_text = fake_match_client.calls[0]
    assert "推薦システム" in student_text
    assert "自然言語処理" in student_text  # 興味タグ
    assert "AIのゼミ" in seminar_text
    assert "深層学習と推薦を扱う研究室" in seminar_text  # 資料要約


async def test_match_returns_message_when_llm_fails(
    client, db_session, fake_match_client, monkeypatch
) -> None:
    user = await _make_user(db_session, research_theme="分散システム")
    seminar = await _make_seminar(db_session, description="DBのゼミ")
    _authenticate_as(user)

    async def _boom(*, student_text: str, seminar_text: str):
        raise RuntimeError("OpenAI down (429)")

    monkeypatch.setattr(fake_match_client, "evaluate", _boom)

    resp = await client.get(f"/seminars/{seminar.id}/match")

    # LLM失敗でも500にせず、算出不可メッセージを返す
    assert resp.status_code == 200
    body = resp.json()
    assert body["score"] is None
    assert body["message"]
