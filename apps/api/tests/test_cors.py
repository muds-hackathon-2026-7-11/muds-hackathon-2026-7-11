"""CORS設定(#42: ブラウザからapiFetchで直接叩けるようにする)のテスト。"""

import pytest

from api.config import Settings, settings


def test_web_app_url_strips_trailing_slash() -> None:
    # Originヘッダには末尾スラッシュが付かないため、比較がズレないよう正規化する。
    assert Settings(web_app_url="http://localhost:3100/").web_app_url == (
        "http://localhost:3100"
    )


@pytest.mark.asyncio
async def test_allows_configured_web_origin(client) -> None:
    resp = await client.get("/health", headers={"Origin": settings.web_app_url})

    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == settings.web_app_url


@pytest.mark.asyncio
async def test_preflight_allows_authorization_header(client) -> None:
    resp = await client.options(
        "/me",
        headers={
            "Origin": settings.web_app_url,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == settings.web_app_url


@pytest.mark.asyncio
async def test_rejects_unconfigured_origin(client) -> None:
    resp = await client.get("/health", headers={"Origin": "http://evil.example.com"})

    assert resp.status_code == 200
    assert "access-control-allow-origin" not in resp.headers
