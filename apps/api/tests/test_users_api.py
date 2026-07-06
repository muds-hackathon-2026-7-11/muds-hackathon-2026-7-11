import pytest

from api import auth
from api.models import User, UserRole

pytestmark = pytest.mark.asyncio

_SECRET = "test-internal-secret"


def _use_internal_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth.settings, "internal_api_secret", _SECRET)


async def test_exists_true_for_registered_email(
    client, db_session, monkeypatch
) -> None:
    _use_internal_secret(monkeypatch)
    db_session.add(
        User(
            google_id="import|registered@example.com",
            email="registered@example.com",
            name="登録済みユーザー",
            role=UserRole.student,
        )
    )
    await db_session.flush()

    resp = await client.get(
        "/users/exists",
        params={"email": "registered@example.com"},
        headers={"X-Internal-Secret": _SECRET},
    )

    assert resp.status_code == 200
    assert resp.json() == {"exists": True}


async def test_exists_false_for_unknown_email(client, monkeypatch) -> None:
    _use_internal_secret(monkeypatch)

    resp = await client.get(
        "/users/exists",
        params={"email": "unknown@example.com"},
        headers={"X-Internal-Secret": _SECRET},
    )

    assert resp.status_code == 200
    assert resp.json() == {"exists": False}


async def test_exists_is_case_insensitive(client, db_session, monkeypatch) -> None:
    _use_internal_secret(monkeypatch)
    db_session.add(
        User(
            google_id="import|mixedcase@example.com",
            email="mixedcase@example.com",
            name="大文字小文字テスト",
            role=UserRole.teacher,
        )
    )
    await db_session.flush()

    resp = await client.get(
        "/users/exists",
        params={"email": "MixedCase@Example.com"},
        headers={"X-Internal-Secret": _SECRET},
    )

    assert resp.status_code == 200
    assert resp.json() == {"exists": True}


async def test_exists_rejects_missing_secret(client, monkeypatch) -> None:
    _use_internal_secret(monkeypatch)

    resp = await client.get("/users/exists", params={"email": "anyone@example.com"})

    assert resp.status_code == 403


async def test_exists_rejects_wrong_secret(client, monkeypatch) -> None:
    _use_internal_secret(monkeypatch)

    resp = await client.get(
        "/users/exists",
        params={"email": "anyone@example.com"},
        headers={"X-Internal-Secret": "wrong-secret"},
    )

    assert resp.status_code == 403


async def test_exists_rejects_when_secret_not_configured(client, monkeypatch) -> None:
    # INTERNAL_API_SECRETが未設定(空文字列)の場合はfail-closedで常に拒否する。
    monkeypatch.setattr(auth.settings, "internal_api_secret", "")

    resp = await client.get(
        "/users/exists",
        params={"email": "anyone@example.com"},
        headers={"X-Internal-Secret": ""},
    )

    assert resp.status_code == 403
