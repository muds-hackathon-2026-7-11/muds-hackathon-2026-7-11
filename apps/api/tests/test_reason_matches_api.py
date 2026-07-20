import uuid

import pytest

from api import auth
from api.auth import get_current_user
from api.main import app
from api.models import Seminar, User, UserRole

pytestmark = pytest.mark.asyncio


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _make_user(db_session) -> User:
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


async def test_reason_matches_returns_selected_and_recommendations(
    client, db_session, fake_match_client
) -> None:
    user = await _make_user(db_session)
    seminars = [await _make_seminar(db_session) for _ in range(5)]
    _authenticate_as(user)

    body = {
        "choices": [
            {"seminar_id": str(seminars[0].id), "reason": "機械学習をやりたい"},
            {"seminar_id": str(seminars[1].id), "reason": "IoTを作りたい"},
        ]
    }
    resp = await client.post("/seminars/reason-matches", json=body)

    assert resp.status_code == 200  # POST が /{seminar_id} に横取りされていない
    results = resp.json()["results"]
    assert len(results) == 2

    first = results[0]
    assert first["seminar_id"] == str(seminars[0].id)
    assert first["selected_score"] == 75  # 選んだゼミ自身のマッチ度
    assert first["rubric"] == {"field": 75, "method": 75, "interest": 75, "style": 75}
    rec_ids = {r["seminar_id"] for r in first["recommendations"]}
    assert len(first["recommendations"]) == 3
    # 志望に入れた2ゼミは他ゼミTop3から除外される
    assert str(seminars[0].id) not in rec_ids
    assert str(seminars[1].id) not in rec_ids

    # 志望理由ごとに1コール = 2回
    assert len(fake_match_client.bulk_calls) == 2


async def test_reason_matches_skips_empty_reason(
    client, db_session, fake_match_client
) -> None:
    user = await _make_user(db_session)
    seminars = [await _make_seminar(db_session) for _ in range(4)]
    _authenticate_as(user)

    body = {
        "choices": [
            {"seminar_id": str(seminars[0].id), "reason": "   "},
            {"seminar_id": str(seminars[1].id), "reason": "有効な理由"},
        ]
    }
    resp = await client.post("/seminars/reason-matches", json=body)

    results = resp.json()["results"]
    assert len(results) == 1  # 空の志望理由スロットは対象外
    assert results[0]["seminar_id"] == str(seminars[1].id)
    assert len(fake_match_client.bulk_calls) == 1


async def test_reason_matches_message_when_all_reasons_empty(
    client, db_session, fake_match_client
) -> None:
    user = await _make_user(db_session)
    seminar = await _make_seminar(db_session)
    _authenticate_as(user)

    body = {"choices": [{"seminar_id": str(seminar.id), "reason": ""}]}
    resp = await client.post("/seminars/reason-matches", json=body)

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["results"] == []
    assert payload["message"]
    assert fake_match_client.bulk_calls == []


async def test_reason_matches_graceful_on_llm_failure(
    client, db_session, fake_match_client, monkeypatch
) -> None:
    user = await _make_user(db_session)
    seminars = [await _make_seminar(db_session) for _ in range(4)]
    _authenticate_as(user)

    async def _boom(*, student_text, seminars):
        raise RuntimeError("OpenAI down")

    monkeypatch.setattr(fake_match_client, "evaluate_all", _boom)

    body = {"choices": [{"seminar_id": str(seminars[0].id), "reason": "理由"}]}
    resp = await client.post("/seminars/reason-matches", json=body)

    assert resp.status_code == 200  # 失敗しても500にしない
    payload = resp.json()
    assert payload["results"] == []
    assert payload["message"]


async def test_reason_matches_requires_authentication(client, monkeypatch) -> None:
    monkeypatch.setattr(auth.settings, "auth_dev_mode", False)
    resp = await client.post(
        "/seminars/reason-matches",
        json={"choices": [{"seminar_id": str(uuid.uuid4()), "reason": "x"}]},
    )
    assert resp.status_code == 401
