"""DBモデルのテストは実Postgresへの接続が必要(CHECK制約等はSQLiteで代替不可)。

ローカルでは `docker compose up -d db && make migrate` 済みであることが前提。
CIでは postgres serviceコンテナ + `alembic upgrade head` をテスト実行前に行う。
"""

from datetime import date, datetime

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.consult_client import FakeConsultClient, get_consult_client
from api.db import async_session, get_db
from api.main import app
from api.match_client import FakeMatchClient, get_match_client
from api.services import JST
from api.slack_client import FakeSlackClient, get_slack_client


def jst_today() -> date:
    """テストが使う「今日」。プロダクトコードと同じJST基準で返す(#207)。

    date.today() はマシンのローカルタイムゾーン依存だが、プロダクト側は
    datetime.now(JST).date() を使う(api.services.get_current_term 等)。
    CI(GitHub Actions)のランナーはUTCで動くため、テストで date.today() を
    使うと JST 0時〜9時(UTC 15時〜24時)の間だけ日付が1日ズレ、「本日が締切」
    のような当日判定のテストが落ちる。開発者のローカルはJSTなので気づけない。

    タイムゾーンの定義が二重化すると同じズレが再発するため、JSTは
    api.services のものをそのまま使う。
    """
    return datetime.now(JST).date()


@pytest_asyncio.fixture
async def db_session():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest_asyncio.fixture
def fake_slack_client():
    return FakeSlackClient()


@pytest_asyncio.fixture
def fake_match_client():
    return FakeMatchClient()


@pytest_asyncio.fixture
def fake_consult_client():
    return FakeConsultClient()


@pytest_asyncio.fixture
async def client(db_session, fake_slack_client, fake_match_client, fake_consult_client):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_slack_client] = lambda: fake_slack_client
    app.dependency_overrides[get_match_client] = lambda: fake_match_client
    app.dependency_overrides[get_consult_client] = lambda: fake_consult_client
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
