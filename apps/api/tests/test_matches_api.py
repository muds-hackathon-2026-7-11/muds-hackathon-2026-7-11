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


async def _make_seminar(
    db_session, *, description: str | None, knowledge: str | None = None
) -> Seminar:
    seminar = Seminar(
        name=_unique("seminar"), description=description, knowledge=knowledge
    )
    db_session.add(seminar)
    await db_session.flush()
    return seminar


def _authenticate_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


async def test_matches_returns_ranked_results(
    client, db_session, fake_match_client
) -> None:
    user = await _make_user(db_session, research_theme="画像認識と深層学習")
    s1 = await _make_seminar(db_session, description="機械学習のゼミ")
    s2 = await _make_seminar(db_session, description="データベースのゼミ")
    _authenticate_as(user)

    resp = await client.get("/seminars/matches")

    assert resp.status_code == 200  # /{seminar_id} に横取りされていない
    body = resp.json()
    ids = {r["seminar_id"] for r in body["results"]}
    assert {str(s1.id), str(s2.id)} <= ids
    first = body["results"][0]
    assert first["score"] == 75  # 全観点75 → 加重総合も75
    assert first["rubric"] == {
        "field": 75,
        "method": 75,
        "interest": 75,
        "style": 75,
    }
    assert first["summary"] == "テスト用の評価"
    # 全ゼミを1コールで採点する
    assert len(fake_match_client.bulk_calls) == 1


async def test_matches_excludes_seminars_without_text(
    client, db_session, fake_match_client
) -> None:
    user = await _make_user(db_session, research_theme="推薦システム")
    with_text = await _make_seminar(db_session, description="AIのゼミ")
    without_text = await _make_seminar(db_session, description=None, knowledge=None)
    _authenticate_as(user)

    resp = await client.get("/seminars/matches")

    ids = {r["seminar_id"] for r in resp.json()["results"]}
    assert str(with_text.id) in ids
    assert str(without_text.id) not in ids  # 判断材料が無いゼミは対象外


async def test_matches_uses_research_theme_not_interest_tags(
    client, db_session, fake_match_client
) -> None:
    user = await _make_user(db_session, research_theme="推薦システム")
    tag = ResearchTag(name="自然言語処理", category="AI", sort_order=1)
    db_session.add(tag)
    await db_session.flush()
    db_session.add(UserInterestTag(user_id=user.id, tag_id=tag.id))
    await _make_seminar(db_session, description="AIのゼミ")
    _authenticate_as(user)

    resp = await client.get("/seminars/matches")

    assert resp.status_code == 200
    student_text, _names = fake_match_client.bulk_calls[0]
    assert "推薦システム" in student_text
    assert "自然言語処理" not in student_text  # 興味タグはマッチ度判定に使わない


async def test_matches_is_cached(client, db_session, fake_match_client) -> None:
    user = await _make_user(db_session, research_theme="分散システム")
    await _make_seminar(db_session, description="DBのゼミ")
    _authenticate_as(user)

    first = await client.get("/seminars/matches")
    second = await client.get("/seminars/matches")

    assert first.status_code == second.status_code == 200
    assert first.json()["results"] == second.json()["results"]
    # 2回目はキャッシュから返り、LLMは1回しか呼ばれない
    assert len(fake_match_client.bulk_calls) == 1


async def test_matches_message_when_no_profile(
    client, db_session, fake_match_client
) -> None:
    user = await _make_user(db_session, research_theme=None)
    await _make_seminar(db_session, description="ゼミ紹介あり")
    _authenticate_as(user)

    resp = await client.get("/seminars/matches")

    assert resp.status_code == 200
    body = resp.json()
    assert body["results"] == []
    assert body["message"]
    assert fake_match_client.bulk_calls == []  # 算出不可のときは呼ばない


async def test_matches_graceful_on_llm_failure(
    client, db_session, fake_match_client, monkeypatch
) -> None:
    user = await _make_user(db_session, research_theme="分散システム")
    await _make_seminar(db_session, description="DBのゼミ")
    _authenticate_as(user)

    async def _boom(*, student_text, seminars):
        raise RuntimeError("OpenAI down (429)")

    monkeypatch.setattr(fake_match_client, "evaluate_all", _boom)

    resp = await client.get("/seminars/matches")

    # LLM失敗でも500にせず、算出不可メッセージを返す
    assert resp.status_code == 200
    body = resp.json()
    assert body["results"] == []
    assert body["message"]


async def test_matches_requires_authentication(client, monkeypatch) -> None:
    monkeypatch.setattr(auth.settings, "auth_dev_mode", False)
    resp = await client.get("/seminars/matches")
    assert resp.status_code == 401
