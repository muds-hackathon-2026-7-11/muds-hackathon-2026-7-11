"""認証(JWT検証・ダミー認証・GET /me・require_role)のテスト。

実Googleに依存しないよう、JWKS検証はテスト内で生成したRSA鍵で自己完結させる。
"""

import time
import uuid
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from jose import jwk, jwt
from sqlalchemy import select

from api import auth
from api.auth import require_role
from api.models import User, UserRole

pytestmark = pytest.mark.asyncio

_ISSUER = "https://issuer.test"
_AUDIENCE = "seminar-platform"
_KID = "test-key"

# テスト用RSA鍵ペア(モジュール読み込み時に1度だけ生成)。
_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PRIVATE_PEM = _private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()
_public_pem = (
    _private_key.public_key()
    .public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    .decode()
)
_public_jwk: dict[str, Any] = jwk.construct(_public_pem, "RS256").to_dict()
_public_jwk.update({"kid": _KID, "use": "sig", "alg": "RS256"})
_JWKS: dict[str, Any] = {"keys": [_public_jwk]}


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _make_user(db_session, role: UserRole = UserRole.student) -> User:
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name=_unique("name"),
        role=role,
    )
    db_session.add(user)
    await db_session.flush()
    return user


def _make_token(
    *, overrides: dict[str, Any] | None = None, exp_delta: int = 3600
) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {
        "sub": "google-sub-123",
        "email": "jwt-user@example.com",
        "name": "JWT User",
        "iss": _ISSUER,
        "aud": _AUDIENCE,
        "iat": now,
        "exp": now + exp_delta,
    }
    if overrides:
        claims.update(overrides)
    token: str = jwt.encode(
        claims, _PRIVATE_PEM, algorithm="RS256", headers={"kid": _KID}
    )
    return token


def _use_jwks(monkeypatch: pytest.MonkeyPatch) -> None:
    """本番相当(dev_mode=False)でJWKS検証を使う設定に差し替える。"""
    monkeypatch.setattr(auth.settings, "auth_dev_mode", False)
    monkeypatch.setattr(auth.settings, "jwt_jwks_url", "https://issuer.test/jwks.json")
    monkeypatch.setattr(auth.settings, "jwt_issuer", _ISSUER)
    monkeypatch.setattr(auth.settings, "jwt_audience", _AUDIENCE)

    async def _fake_get_jwks(*, force: bool = False) -> dict[str, Any]:
        return _JWKS

    monkeypatch.setattr(auth, "_get_jwks", _fake_get_jwks)


# --- ダミー認証 ---


async def test_me_dev_mode_provisions_user(client, db_session, monkeypatch) -> None:
    monkeypatch.setattr(auth.settings, "auth_dev_mode", True)

    resp = await client.get(
        "/me",
        headers={
            "X-Dev-User-Email": "devx@example.com",
            "X-Dev-User-Role": "teacher",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "devx@example.com"
    assert body["role"] == "teacher"

    # usersにJITプロビジョニングされていること。
    result = await db_session.execute(
        select(User).where(User.email == "devx@example.com")
    )
    assert result.scalar_one_or_none() is not None


async def test_me_dev_mode_default_email(client, monkeypatch) -> None:
    monkeypatch.setattr(auth.settings, "auth_dev_mode", True)
    monkeypatch.setattr(auth.settings, "auth_dev_user_email", "fallback@example.com")

    resp = await client.get("/me")

    assert resp.status_code == 200
    assert resp.json()["email"] == "fallback@example.com"


# --- JWKS検証(本番相当) ---


async def test_me_with_valid_jwt(client, monkeypatch) -> None:
    _use_jwks(monkeypatch)

    resp = await client.get("/me", headers={"Authorization": f"Bearer {_make_token()}"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "jwt-user@example.com"
    assert body["role"] == "student"


async def test_me_with_expired_jwt_is_401(client, monkeypatch) -> None:
    _use_jwks(monkeypatch)

    resp = await client.get(
        "/me", headers={"Authorization": f"Bearer {_make_token(exp_delta=-10)}"}
    )

    assert resp.status_code == 401


async def test_me_with_garbage_token_is_401(client, monkeypatch) -> None:
    _use_jwks(monkeypatch)

    resp = await client.get("/me", headers={"Authorization": "Bearer not.a.jwt"})

    assert resp.status_code == 401


async def test_me_without_auth_is_401(client, monkeypatch) -> None:
    _use_jwks(monkeypatch)

    resp = await client.get("/me")

    assert resp.status_code == 401


# --- require_role(下地) ---


async def test_require_role_forbids_and_allows(db_session) -> None:
    dependency = require_role(UserRole.admin)

    student = await _make_user(db_session, UserRole.student)
    with pytest.raises(HTTPException) as exc_info:
        await dependency(student)
    assert exc_info.value.status_code == 403

    admin = await _make_user(db_session, UserRole.admin)
    assert await dependency(admin) is admin


async def test_require_role_allows_any_listed_role(db_session) -> None:
    dependency = require_role(UserRole.teacher, UserRole.admin)

    teacher = await _make_user(db_session, UserRole.teacher)
    assert await dependency(teacher) is teacher


# --- プロビジョニング・検証の強化 ---


async def test_me_provisioning_is_idempotent(client, db_session, monkeypatch) -> None:
    _use_jwks(monkeypatch)
    token = _make_token()

    first = await client.get("/me", headers={"Authorization": f"Bearer {token}"})
    second = await client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]

    # 2回叩いてもユーザーは重複作成されない。
    result = await db_session.execute(
        select(User).where(User.google_id == "google-sub-123")
    )
    assert len(result.scalars().all()) == 1


async def test_me_links_existing_email_user(client, db_session, monkeypatch) -> None:
    """事前に存在するemailのユーザー(seed等)は、初回ログインでgoogle_idが紐付く。"""
    _use_jwks(monkeypatch)
    existing = User(
        google_id=_unique("placeholder"),
        email="jwt-user@example.com",
        name="Seeded User",
        role=UserRole.teacher,
    )
    db_session.add(existing)
    await db_session.flush()

    resp = await client.get("/me", headers={"Authorization": f"Bearer {_make_token()}"})

    assert resp.status_code == 200
    assert resp.json()["id"] == str(existing.id)
    assert resp.json()["role"] == "teacher"
    # 重複ユーザーは作られない。
    result = await db_session.execute(
        select(User).where(User.email == "jwt-user@example.com")
    )
    assert len(result.scalars().all()) == 1


async def test_me_with_wrong_audience_is_401(client, monkeypatch) -> None:
    _use_jwks(monkeypatch)
    token = _make_token(overrides={"aud": "someone-else"})

    resp = await client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 401


async def test_me_with_wrong_issuer_is_401(client, monkeypatch) -> None:
    _use_jwks(monkeypatch)
    token = _make_token(overrides={"iss": "https://evil.test"})

    resp = await client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 401


async def test_me_with_unknown_signing_key_is_401(client, monkeypatch) -> None:
    """JWKSに無い鍵で署名されたトークンは、署名検証で弾かれる(401)。"""
    _use_jwks(monkeypatch)
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_pem = other_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    now = int(time.time())
    token: str = jwt.encode(
        {
            "sub": "google-sub-123",
            "email": "jwt-user@example.com",
            "iss": _ISSUER,
            "aud": _AUDIENCE,
            "exp": now + 3600,
        },
        other_pem,
        algorithm="RS256",
        headers={"kid": _KID},
    )

    resp = await client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 401


async def test_me_without_sub_is_401(client, monkeypatch) -> None:
    _use_jwks(monkeypatch)
    token = _make_token(overrides={"sub": ""})

    resp = await client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 401
