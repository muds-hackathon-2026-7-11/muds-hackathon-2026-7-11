"""DBモデルのテストは実Postgresへの接続が必要(CHECK制約等はSQLiteで代替不可)。

ローカルでは `docker compose up -d db && make migrate` 済みであることが前提。
CIでは postgres serviceコンテナ + `alembic upgrade head` をテスト実行前に行う。
"""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.db import async_session, get_db
from api.main import app
from api.slack_client import FakeSlackClient, get_slack_client


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
async def client(db_session, fake_slack_client):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_slack_client] = lambda: fake_slack_client
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
