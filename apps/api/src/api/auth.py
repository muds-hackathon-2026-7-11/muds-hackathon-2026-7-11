"""認証(JWT検証)まわり。

本番: フロント(Auth.js)が発行したJWTを、JWKS経由で検証する(#6 の検証側)。
開発: `AUTH_DEV_MODE=true` のとき、実JWT検証を行わず X-Dev-User-Email ヘッダ
      のユーザーとして認証する(ローカル/CIで実Googleに依存せず動かすため)。

いずれの場合も、認証済みユーザーは users テーブルへ find-or-create
(JITプロビジョニング)し、ORMの `User` として各エンドポイントに注入する。
"""

import time
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from jose.exceptions import JWTError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.db import get_db
from api.models import User, UserRole

_bearer_scheme = HTTPBearer(auto_error=False)

# JWKSはURLから取得してメモリにキャッシュする(毎リクエストで取りに行かない)。
_JWKS_TTL_SECONDS = 3600.0
_jwks_cache: dict[str, Any] | None = None
_jwks_fetched_at: float = 0.0


async def _get_jwks(*, force: bool = False) -> dict[str, Any]:
    """JWKSを取得する。TTL内はキャッシュを返す。"""
    global _jwks_cache, _jwks_fetched_at

    now = time.monotonic()
    if force or _jwks_cache is None or now - _jwks_fetched_at > _JWKS_TTL_SECONDS:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(settings.jwt_jwks_url)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
        _jwks_cache = data
        _jwks_fetched_at = now
    return _jwks_cache


async def _verify_jwt(token: str) -> dict[str, Any]:
    """JWTをJWKSで検証し、claimsを返す。検証に失敗したら401。"""
    if not settings.jwt_jwks_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT検証が未設定です(JWT_JWKS_URL)。",
        )
    try:
        jwks = await _get_jwks()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="認証キーの取得に失敗しました。",
        ) from exc

    try:
        # python-joseはJWKセットを渡すとheaderのkidから鍵を選んで検証する。
        claims: dict[str, Any] = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=settings.jwt_audience or None,
            issuer=settings.jwt_issuer or None,
            options={"verify_aud": bool(settings.jwt_audience)},
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証トークンが無効です。",
        ) from exc
    return claims


async def _provision_user(
    db: AsyncSession,
    *,
    google_id: str,
    email: str,
    name: str,
    role: UserRole = UserRole.student,
) -> User:
    """claimsからusersをfind-or-create(JITプロビジョニング)する。

    google_id(=sub)で検索し、無ければemailで既存レコードに紐付け、
    それも無ければ新規作成する。初回同時ログインの競合はSAVEPOINTで吸収する。
    """
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    if email:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is not None:
            user.google_id = google_id
            await db.flush()
            return user

    user = User(
        google_id=google_id,
        email=email,
        name=name or email or google_id,
        role=role,
    )
    try:
        async with db.begin_nested():
            db.add(user)
            await db.flush()
    except IntegrityError:
        # 別リクエストが先に作成したケース。作成済みのレコードを取得し直す。
        result = await db.execute(select(User).where(User.google_id == google_id))
        user = result.scalar_one()
    return user


async def _authenticate_dev(request: Request, db: AsyncSession) -> User:
    """開発用ダミー認証。X-Dev-User-Email / X-Dev-User-Role でユーザーを特定する。"""
    email = request.headers.get("X-Dev-User-Email") or settings.auth_dev_user_email
    role_raw = request.headers.get("X-Dev-User-Role", UserRole.student.value)
    try:
        role = UserRole(role_raw)
    except ValueError:
        role = UserRole.student

    user = await _provision_user(
        db,
        google_id=f"dev|{email}",
        email=email,
        name=email.split("@")[0],
        role=role,
    )
    # 開発時はヘッダのroleで都度上書きし、role別の動作確認をしやすくする。
    if user.role != role:
        user.role = role
        await db.flush()
    return user


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """認証済みユーザーを返すFastAPI依存。未認証・無効トークンは401。"""
    if settings.auth_dev_mode:
        return await _authenticate_dev(request, db)

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証が必要です。",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = await _verify_jwt(credentials.credentials)
    google_id = claims.get("sub")
    if not google_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="トークンにsubがありません。",
        )
    return await _provision_user(
        db,
        google_id=str(google_id),
        email=str(claims.get("email", "")),
        name=str(claims.get("name", "")),
    )


async def require_internal_secret(request: Request) -> None:
    """web-api間の合言葉を要求する依存。

    ログイン前(未認証)に呼ぶ必要がありJWT検証を通せないエンドポイント
    (/users/exists 等)を、webサーバー以外からの直接アクセスから守る。
    """
    provided = request.headers.get("X-Internal-Secret")
    if not settings.internal_api_secret or provided != settings.internal_api_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このエンドポイントは内部からのみ呼び出せます。",
        )


def require_role(
    *roles: UserRole,
) -> Callable[[User], Awaitable[User]]:
    """指定ロールかつis_active=trueのユーザーのみ許可する依存を生成する。

    卒業・退学・退職等でis_active=falseになったユーザーは、ログイン前の
    /users/existsだけでなく、ログイン済みでもrole限定のエンドポイントを
    使えないようにする(トークン有効期限内に非アクティブ化された場合の対策)。
    """

    async def _dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="この操作を行う権限がありません。",
            )
        return user

    return _dependency
