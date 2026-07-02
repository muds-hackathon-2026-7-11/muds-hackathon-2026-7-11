"""開発用: 自分のSlackユーザーIDをテスト用ユーザーに紐付けるスクリプト。

本来はGoogleログイン経由でusersレコードが作られる想定だが、認証機能が
まだ実装されていないため、Slack連携をローカルで試すための踏み台として用意する。
"""

import asyncio
import sys
import uuid

from sqlalchemy import select

from api.db import async_session
from api.models import User, UserRole


async def link_slack_user(slack_user_id: str) -> None:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.slack_user_id == slack_user_id)
        )
        user = result.scalar_one_or_none()
        if user is not None:
            print(f"already linked: {user.name} ({user.email})")
            return

        suffix = uuid.uuid4().hex[:8]
        user = User(
            google_id=f"dev-{suffix}",
            email=f"dev-{suffix}@example.com",
            name="開発用テストユーザー",
            role=UserRole.student,
            slack_user_id=slack_user_id,
        )
        session.add(user)
        await session.commit()
        print(f"linked {slack_user_id} as a new test user ({user.email})")


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: uv run python -m api.link_slack_user <SLACK_USER_ID>")
        sys.exit(1)
    asyncio.run(link_slack_user(sys.argv[1]))


if __name__ == "__main__":
    main()
