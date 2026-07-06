"""指定年度の募集期間(recruitment_terms)を作成する(べき等)。

ダミーのゼミ・学生データまで入ってしまうapi.seedを使わずに、開発用に
最低限の募集期間を1件だけ作りたい場合に使う。実運用での募集期間の
作成・編集(前期・後期など複数回への対応含む)は運営向けAPI(#57)で行う。

使い方: uv run python -m api.ensure_recruitment_term <年度>
"""

import argparse
import asyncio

from api.db import async_session
from api.recruitment_terms import get_or_create_recruitment_term


async def ensure(academic_year: int) -> None:
    async with async_session() as session:
        term, created = await get_or_create_recruitment_term(session, academic_year)
        await session.commit()

    if created:
        print(
            f"{academic_year}年度の募集期間を作成しました"
            f"({term.starts_at} 〜 {term.ends_at})"
        )
    else:
        print(f"{academic_year}年度の募集期間は既に存在します(スキップ)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="募集期間(recruitment_terms)を作成する(べき等)"
    )
    parser.add_argument("academic_year", type=int)
    args = parser.parse_args()
    asyncio.run(ensure(args.academic_year))


if __name__ == "__main__":
    main()
