"""DBモデルのテストは実Postgresへの接続が必要(CHECK制約等はSQLiteで代替不可)。

ローカルでは `docker compose up -d db && make migrate` 済みであることが前提。
CIでは postgres serviceコンテナ + `alembic upgrade head` をテスト実行前に行う。
"""

import pytest_asyncio

from api.db import async_session


@pytest_asyncio.fixture
async def db_session():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.rollback()
