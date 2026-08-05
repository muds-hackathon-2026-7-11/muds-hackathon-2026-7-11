"""締切リマインダー(#153)を今すぐ1回分、手動で実行する。

本来は毎日12:00(JST)にAPSchedulerが自動実行するが、サーバー負荷などで
misfire(取りこぼし)した場合に、同じ処理を手動で1回分だけ実行するための
CLI。send_deadline_reminders自体は重複排除を行わないため、同じ日に
2回実行すると同じ学生に2通届く点に注意。

使い方: uv run python -m api.send_deadline_reminders_now
本番では `docker compose exec api uv run python -m api.send_deadline_reminders_now` で
実行する(そのコンテナのSLACK_BOT_TOKENが実際に使われる)。

SLACK_BOT_TOKENが設定されている環境では実際にSlack DMが飛ぶため、
実行前に確認を挟む(--yes で確認をスキップできる。cron等からの呼び出し用)。
"""

import argparse
import asyncio

from api.db import async_session
from api.services import send_deadline_reminders
from api.slack_client import RealSlackClient, get_slack_client


async def run(*, skip_confirm: bool) -> None:
    client = get_slack_client()
    is_real = isinstance(client, RealSlackClient)

    if is_real and not skip_confirm:
        answer = input(
            "SLACK_BOT_TOKENが設定されています。実行すると、未提出の学生へ"
            "本物のSlack DMが送信されます。続行しますか? (yes と入力): "
        )
        if answer.strip().lower() != "yes":
            print("中止しました。")
            return

    if is_real:
        mode = "実際にSlackへ送信します"
    else:
        mode = "SLACK_BOT_TOKEN未設定のため実送信はされません"
    print(f"締切リマインダーを実行します...({mode})")
    async with async_session() as session:
        await send_deadline_reminders(session, client)
        await session.commit()
    print("完了しました。")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="締切リマインダー(#153)を今すぐ1回分、手動で実行する"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="実送信前の確認プロンプトをスキップする(cron等からの呼び出し用)",
    )
    args = parser.parse_args()
    asyncio.run(run(skip_confirm=args.yes))


if __name__ == "__main__":
    main()
