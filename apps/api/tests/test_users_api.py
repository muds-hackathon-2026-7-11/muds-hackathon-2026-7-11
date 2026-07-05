import pytest

from api.models import User, UserRole

pytestmark = pytest.mark.asyncio


async def test_exists_true_for_registered_email(client, db_session) -> None:
    db_session.add(
        User(
            google_id="import|registered@example.com",
            email="registered@example.com",
            name="登録済みユーザー",
            role=UserRole.student,
        )
    )
    await db_session.flush()

    resp = await client.get("/users/exists", params={"email": "registered@example.com"})

    assert resp.status_code == 200
    assert resp.json() == {"exists": True}


async def test_exists_false_for_unknown_email(client) -> None:
    resp = await client.get("/users/exists", params={"email": "unknown@example.com"})

    assert resp.status_code == 200
    assert resp.json() == {"exists": False}


async def test_exists_is_case_insensitive(client, db_session) -> None:
    db_session.add(
        User(
            google_id="import|mixedcase@example.com",
            email="mixedcase@example.com",
            name="大文字小文字テスト",
            role=UserRole.teacher,
        )
    )
    await db_session.flush()

    resp = await client.get("/users/exists", params={"email": "MixedCase@Example.com"})

    assert resp.status_code == 200
    assert resp.json() == {"exists": True}
