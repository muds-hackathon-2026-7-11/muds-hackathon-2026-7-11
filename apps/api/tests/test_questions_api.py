import uuid

import pytest

from api.models import Seminar, User, UserRole

pytestmark = pytest.mark.asyncio


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _make_seminar(db_session) -> Seminar:
    seminar = Seminar(name=_unique("seminar"))
    db_session.add(seminar)
    await db_session.flush()
    return seminar


async def test_list_seminars(client, db_session) -> None:
    seminar = await _make_seminar(db_session)

    resp = await client.get("/seminars")

    assert resp.status_code == 200
    names = [s["name"] for s in resp.json()]
    assert seminar.name in names


async def test_create_question_success(client, db_session) -> None:
    slack_user_id = _unique("U")
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name="Test User",
        role=UserRole.student,
        slack_user_id=slack_user_id,
    )
    db_session.add(user)
    seminar = await _make_seminar(db_session)
    await db_session.flush()

    resp = await client.post(
        "/questions",
        json={
            "seminar_id": str(seminar.id),
            "slack_user_id": slack_user_id,
            "content": "プログラミング未経験でも大丈夫ですか？",
        },
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["seminar_id"] == str(seminar.id)
    assert body["content"] == "プログラミング未経験でも大丈夫ですか？"
    assert "user_id" not in body  # 匿名化: APIレスポンスにuser_idを含めない


async def test_create_question_unknown_slack_user_returns_404(
    client, db_session
) -> None:
    seminar = await _make_seminar(db_session)
    await db_session.flush()

    resp = await client.post(
        "/questions",
        json={
            "seminar_id": str(seminar.id),
            "slack_user_id": _unique("U-unknown"),
            "content": "質問です",
        },
    )

    assert resp.status_code == 404


async def test_create_question_unknown_seminar_returns_404(client, db_session) -> None:
    slack_user_id = _unique("U")
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name="Test User",
        role=UserRole.student,
        slack_user_id=slack_user_id,
    )
    db_session.add(user)
    await db_session.flush()

    resp = await client.post(
        "/questions",
        json={
            "seminar_id": str(uuid.uuid4()),
            "slack_user_id": slack_user_id,
            "content": "質問です",
        },
    )

    assert resp.status_code == 404


async def test_create_question_empty_content_is_rejected(client, db_session) -> None:
    slack_user_id = _unique("U")
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name="Test User",
        role=UserRole.student,
        slack_user_id=slack_user_id,
    )
    db_session.add(user)
    seminar = await _make_seminar(db_session)
    await db_session.flush()

    resp = await client.post(
        "/questions",
        json={
            "seminar_id": str(seminar.id),
            "slack_user_id": slack_user_id,
            "content": "",
        },
    )

    assert resp.status_code == 422
