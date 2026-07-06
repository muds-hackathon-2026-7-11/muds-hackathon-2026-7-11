"""ゼミ・教員データCSVをDBへ投入するスクリプト。

使い方: uv run python -m api.import_seminars <CSVファイルパス>

CSV列: ゼミ名, ゼミ紹介文, 教員写真URL, 教員氏名, 教員メールアドレス
同じ「ゼミ名」の行が複数あれば、教員が複数いるゼミとして同一ゼミに紐付ける。

定員・募集期間(recruitment_terms/seminar_recruitments)はここでは扱わない。
運営がUI/API([Backend] 運営: 募集ラウンド・定員設定API #57)から設定する。
"""

import argparse
import asyncio
import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import async_session
from api.models import Seminar, SeminarTeacher, User, UserRole


async def _get_or_create_seminar(
    session: AsyncSession, *, name: str, description: str | None
) -> tuple[Seminar, bool]:
    result = await session.execute(select(Seminar).where(Seminar.name == name))
    seminar = result.scalar_one_or_none()
    if seminar is not None:
        return seminar, False

    seminar = Seminar(name=name, description=description)
    session.add(seminar)
    await session.flush()
    return seminar, True


async def _get_or_create_teacher(
    session: AsyncSession, *, name: str, email: str, photo_url: str | None
) -> tuple[User, bool]:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is not None:
        user.name = name
        user.photo_url = photo_url
        return user, False

    user = User(
        google_id=f"import|{email}",
        email=email,
        name=name,
        role=UserRole.teacher,
        photo_url=photo_url,
    )
    session.add(user)
    await session.flush()
    return user, True


async def _get_or_create_link(
    session: AsyncSession, *, seminar: Seminar, teacher: User
) -> bool:
    result = await session.execute(
        select(SeminarTeacher).where(
            SeminarTeacher.seminar_id == seminar.id,
            SeminarTeacher.teacher_id == teacher.id,
        )
    )
    if result.scalar_one_or_none() is not None:
        return False

    session.add(SeminarTeacher(seminar_id=seminar.id, teacher_id=teacher.id))
    return True


async def import_csv(path: Path) -> None:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    async with async_session() as session:
        seminars_by_name: dict[str, Seminar] = {}
        seminar_created = 0
        teacher_created = 0
        link_created = 0

        for row in rows:
            name = row["ゼミ名"].strip()
            if name not in seminars_by_name:
                seminar, created = await _get_or_create_seminar(
                    session,
                    name=name,
                    description=row["ゼミ紹介文"].strip() or None,
                )
                seminars_by_name[name] = seminar
                if created:
                    seminar_created += 1
            seminar = seminars_by_name[name]

            teacher, created = await _get_or_create_teacher(
                session,
                name=row["教員氏名"].strip(),
                # import_users.py(Slackメンバー一覧の取り込み)と同じ正規化にし、
                # 大文字小文字違いで同一教員が別レコードとして重複作成されるのを防ぐ。
                email=row["教員メールアドレス"].strip().lower(),
                photo_url=row["教員写真URL"].strip() or None,
            )
            if created:
                teacher_created += 1

            if await _get_or_create_link(session, seminar=seminar, teacher=teacher):
                link_created += 1

        await session.commit()

    print(
        f"seminars: +{seminar_created}, teachers: +{teacher_created}, "
        f"links: +{link_created}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="ゼミ・教員データCSVをDBへ投入する")
    parser.add_argument("csv_path", type=Path)
    args = parser.parse_args()
    asyncio.run(import_csv(args.csv_path))


if __name__ == "__main__":
    main()
