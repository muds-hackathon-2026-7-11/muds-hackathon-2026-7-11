"""Slackワークスペースメンバー一覧CSVから学生・教員データをDBへ投入するスクリプト。

使い方: uv run python -m api.import_users <CSVファイルパス>

CSV列(Slack管理画面のメンバー一覧エクスポート形式):
username, email, status, billing-active, has-2fa, has-sso, userid,
fullname, displayname, expiration-timestamp

fullname は `[学年] 氏名 / Romanized Name` 形式(例: `[B1] 山田 太郎 / Taro Yamada`)。
角括弧の中身が「教員」ならrole=teacher、それ以外は学年としてrole=studentにする。

ログイン前にemailキーでレコードを用意しておけば、実際にGoogleログインした際
api.auth._provision_user のemail一致ロジックで自動的にgoogle_idが後付けされる。
"""

import argparse
import asyncio
import csv
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import async_session
from api.models import User, UserRole

FULLNAME_RE = re.compile(r"^\[(.+?)\]\s*(.+)$")
STUDENT_ID_RE = re.compile(r"^[sg]\d+$")

TEACHER_BRACKET = "教員"


class ParsedProfile:
    def __init__(
        self, *, name: str, role: UserRole, grade: str | None, student_id: str | None
    ) -> None:
        self.name = name
        self.role = role
        self.grade = grade
        self.student_id = student_id


def parse_fullname(fullname: str, email: str) -> ParsedProfile | None:
    """fullname(`[学年/役職] 氏名 / Romanized`)をパースする。

    角括弧が無い行(botアカウント等の想定外フォーマット)はNoneを返す。
    """
    match = FULLNAME_RE.match(fullname.strip())
    if match is None:
        return None

    bracket = re.sub(r"\s*/\s*", "/", match.group(1).strip())
    name = match.group(2).split("/")[0].strip()

    if bracket == TEACHER_BRACKET:
        return ParsedProfile(
            name=name, role=UserRole.teacher, grade=None, student_id=None
        )

    local_part = email.split("@")[0]
    student_id = local_part if STUDENT_ID_RE.fullmatch(local_part) else None
    return ParsedProfile(
        name=name, role=UserRole.student, grade=bracket, student_id=student_id
    )


async def _get_or_create_user(
    session: AsyncSession, *, email: str, slack_user_id: str, profile: ParsedProfile
) -> tuple[User, bool]:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is not None:
        user.name = profile.name
        user.role = profile.role
        user.grade = profile.grade
        user.student_id = profile.student_id
        user.slack_user_id = slack_user_id
        return user, False

    user = User(
        google_id=f"import|{email}",
        email=email,
        name=profile.name,
        role=profile.role,
        grade=profile.grade,
        student_id=profile.student_id,
        slack_user_id=slack_user_id,
    )
    session.add(user)
    await session.flush()
    return user, True


async def import_csv(path: Path) -> None:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    async with async_session() as session:
        created = 0
        updated = 0
        skipped = 0

        for row in rows:
            email = row["email"].strip()
            profile = parse_fullname(row["fullname"], email)
            if profile is None:
                skipped += 1
                print(f"skip(fullnameをパースできません): {email} {row['fullname']!r}")
                continue

            _, was_created = await _get_or_create_user(
                session,
                email=email,
                slack_user_id=row["userid"].strip(),
                profile=profile,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        await session.commit()

    print(f"users: +{created} created, {updated} updated, {skipped} skipped")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Slackメンバー一覧CSVから学生・教員データをDBへ投入する"
    )
    parser.add_argument("csv_path", type=Path)
    args = parser.parse_args()
    asyncio.run(import_csv(args.csv_path))


if __name__ == "__main__":
    main()
