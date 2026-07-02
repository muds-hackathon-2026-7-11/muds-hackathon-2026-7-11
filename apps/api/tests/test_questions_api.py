import uuid
from datetime import date

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.db import get_db
from api.main import app
from api.models import Seminar, User, UserRole

pytestmark = pytest.mark.asyncio


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


async def _make_seminar(db_session) -> Seminar:
    seminar = Seminar(
        name=_unique("seminar"),
        capacity=10,
        recruitment_start=date(2026, 4, 1),
        recruitment_end=date(2026, 5, 1),
    )
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
    assert body["user_id"] == str(user.id)
    assert body["content"] == "プログラミング未経験でも大丈夫ですか？"


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
