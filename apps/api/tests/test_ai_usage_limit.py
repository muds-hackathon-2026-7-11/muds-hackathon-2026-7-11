"""AI機能の募集期間あたりの利用上限(#201)。

上限が効いていないことは請求額にしか現れないため、「上限を超えたらLLMを
呼ばない」ことを呼び出し記録(FakeClientのcalls)で直接確認する。
"""

import uuid
from datetime import date, timedelta

import pytest

from api import usage
from api.auth import get_current_user
from api.main import app
from api.models import (
    RecruitmentTerm,
    RecruitmentTermStatus,
    Seminar,
    User,
    UserRole,
)

pytestmark = pytest.mark.asyncio


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _make_user(db_session, role: UserRole = UserRole.student) -> User:
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name=_unique("name"),
        role=role,
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


async def _make_open_term(db_session, academic_year: int) -> RecruitmentTerm:
    """今日を含む open な募集期間。academic_year が大きいほど優先される
    (get_current_term の並び順)ため、テスト内で「次のラウンド」を作れる。"""
    today = date.today()
    term = RecruitmentTerm(
        academic_year=academic_year,
        starts_at=today - timedelta(days=1),
        ends_at=today + timedelta(days=30),
        status=RecruitmentTermStatus.open,
    )
    db_session.add(term)
    await db_session.flush()
    return term


def _authenticate_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


def _set_limits(monkeypatch, *, match: int = 0, consult: int = 0) -> None:
    """テスト対象の上限だけを有効にする(0 は無制限の設定値)。"""
    monkeypatch.setattr(usage.settings, "ai_match_limit_per_term", match)
    monkeypatch.setattr(usage.settings, "ai_consult_limit_per_term", consult)


async def _diagnose(client, seminar: Seminar, reason: str):
    return await client.post(
        "/seminars/reason-matches",
        json={"choices": [{"seminar_id": str(seminar.id), "reason": reason}]},
    )


async def test_within_limit_works_normally(
    client, db_session, fake_match_client, monkeypatch
) -> None:
    _set_limits(monkeypatch, match=2)
    user = await _make_user(db_session)
    seminar = await _make_seminar(db_session)
    _authenticate_as(user)

    first = await _diagnose(client, seminar, "機械学習をやりたい")
    second = await _diagnose(client, seminar, "IoTを作りたい")

    assert first.status_code == second.status_code == 200
    assert len(first.json()["results"]) == 1
    assert len(second.json()["results"]) == 1
    assert second.json()["message"] is None
    assert len(fake_match_client.bulk_calls) == 2


async def test_match_over_limit_skips_llm_and_returns_message(
    client, db_session, fake_match_client, monkeypatch
) -> None:
    _set_limits(monkeypatch, match=1)
    user = await _make_user(db_session)
    seminar = await _make_seminar(db_session)
    _authenticate_as(user)

    await _diagnose(client, seminar, "機械学習をやりたい")
    resp = await _diagnose(client, seminar, "別の理由なのでキャッシュには当たらない")

    assert resp.status_code == 200
    body = resp.json()
    assert body["results"] == []
    assert "上限" in body["message"]
    # 上限超過分はOpenAIを呼ばない(ここが課金の歯止め)
    assert len(fake_match_client.bulk_calls) == 1


async def test_consult_over_limit_skips_llm_and_returns_message(
    client, db_session, fake_consult_client, monkeypatch
) -> None:
    _set_limits(monkeypatch, consult=1)
    user = await _make_user(db_session)
    await _make_seminar(db_session)
    _authenticate_as(user)

    await client.post("/consult", json={"message": "ゼミ選びに悩んでいます"})
    resp = await client.post("/consult", json={"message": "もう一度相談したい"})

    assert resp.status_code == 200
    body = resp.json()
    assert "上限" in body["reply"]
    assert body["recommendations"] == []
    assert len(fake_consult_client.calls) == 1


async def test_counter_resets_on_new_recruitment_term(
    client, db_session, fake_match_client, monkeypatch
) -> None:
    _set_limits(monkeypatch, match=1)
    user = await _make_user(db_session)
    seminar = await _make_seminar(db_session)
    await _make_open_term(db_session, academic_year=2999)
    _authenticate_as(user)

    await _diagnose(client, seminar, "今期の理由")
    blocked = await _diagnose(client, seminar, "今期の2つめの理由")
    assert blocked.json()["results"] == []

    # 次の募集ラウンドが始まると別の行になるので、上限は仕切り直しになる
    await _make_open_term(db_session, academic_year=3000)
    resp = await _diagnose(client, seminar, "来期の理由")

    assert len(resp.json()["results"]) == 1
    assert len(fake_match_client.bulk_calls) == 2


async def test_cache_hit_does_not_consume_quota(
    client, db_session, fake_match_client, monkeypatch
) -> None:
    _set_limits(monkeypatch, match=1)
    user = await _make_user(db_session)
    seminar = await _make_seminar(db_session)
    _authenticate_as(user)

    first = await _diagnose(client, seminar, "同じ理由")
    second = await _diagnose(client, seminar, "同じ理由")

    # 2回目は採点キャッシュに当たりOpenAIを呼んでいない = 課金されていないので、
    # 上限を消費させない
    assert len(fake_match_client.bulk_calls) == 1
    assert len(first.json()["results"]) == 1
    assert len(second.json()["results"]) == 1
    assert second.json()["message"] is None


@pytest.mark.parametrize("role", [UserRole.teacher, UserRole.admin])
async def test_staff_are_exempt_from_limit(
    client, db_session, fake_match_client, monkeypatch, role
) -> None:
    _set_limits(monkeypatch, match=1)
    user = await _make_user(db_session, role=role)
    seminar = await _make_seminar(db_session)
    _authenticate_as(user)

    await _diagnose(client, seminar, "1回目の理由")
    resp = await _diagnose(client, seminar, "2回目の理由")

    assert len(resp.json()["results"]) == 1
    assert len(fake_match_client.bulk_calls) == 2


async def test_single_seminar_match_is_also_limited(
    client, db_session, fake_match_client, monkeypatch
) -> None:
    """フロント未使用でも認証さえ通れば叩けるため、抜け道を残さない。"""
    _set_limits(monkeypatch, match=1)
    user = await _make_user(db_session)
    first_seminar = await _make_seminar(db_session)
    second_seminar = await _make_seminar(db_session)
    _authenticate_as(user)

    ok = await client.get(f"/seminars/{first_seminar.id}/match")
    blocked = await client.get(f"/seminars/{second_seminar.id}/match")

    assert ok.json()["score"] == 75
    assert blocked.json()["score"] is None
    assert "上限" in blocked.json()["message"]
    assert len(fake_match_client.calls) == 1


async def test_zero_limit_means_unlimited(
    client, db_session, fake_match_client, monkeypatch
) -> None:
    _set_limits(monkeypatch, match=0)
    user = await _make_user(db_session)
    seminar = await _make_seminar(db_session)
    _authenticate_as(user)

    for i in range(3):
        resp = await _diagnose(client, seminar, f"理由{i}")
        assert len(resp.json()["results"]) == 1
    assert len(fake_match_client.bulk_calls) == 3
