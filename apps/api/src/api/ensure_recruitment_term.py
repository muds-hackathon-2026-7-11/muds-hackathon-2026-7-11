"""指定年度の募集期間(recruitment_terms)を作成する(べき等)。

import_seminars.py は対象年度の募集期間が事前に存在することを前提にしている
(定員・応募はrecruitment_terms/seminar_recruitmentsに年度単位で紐づくため)。
ダミーのゼミ・学生データまで入ってしまうapi.seedを使わずに、この1件だけを
作りたい場合に使う。

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
