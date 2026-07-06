"""Slackワークスペースメンバー一覧CSVから学生・教員データをDBへ投入するスクリプト。

使い方: uv run python -m api.import_users <CSVファイルパス>

CSV列(Slack管理画面のメンバー一覧エクスポート形式):
username, email, status, billing-active, has-2fa, has-sso, userid,
fullname, displayname, expiration-timestamp

fullname は `[学年] 氏名 / Romanized Name` 形式(例: `[B1] 山田 太郎 / Taro Yamada`)。
角括弧の中身が「教員」ならrole=teacher、既知の学年パターン(B1-4, MIDS/B1-4,
M1/M2/D1等、guestサフィックス可)ならrole=studentにする。それ以外(卒業生の
「卒」、他学科、提携企業ゲスト、重複アカウント等)はデータサイエンス学科の
現役学生・教員ではないため無視する(全学ワークスペースのエクスポートには
これらが大量に混在するため)。

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
# 既知の学年パターンのみ許可するallowlist。例: B1-4, MIDS/B1-4, M1, M2,
# D1, M2 guest。全学エクスポートには「卒」「職員」「研究員」「他学科」
# 「アカウント重複」提携企業ゲスト等が大量に混ざるため、未知のパターンは
# 学生として取り込まず無視する(TEACHER_BRACKETと合わせて2段構えで判定)。
GRADE_RE = re.compile(r"^(MIDS/)?[BMD]\d+(\s*guest)?$")

TEACHER_BRACKET = "教員"
# 非アクティブ化の対象はstudentのみ。教員はSlack参加状況ではなく
# ゼミ・教員データ(import_seminars.py)で管理されており、Slackエクスポートに
# 居ないだけの現役教員(実在)を誤って非アクティブ化してしまう事故が
# 実際に発生したため、教員はこの仕組みの対象外にする。adminも対象外。
DEACTIVATION_MANAGED_ROLES = (UserRole.student,)


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

    角括弧が無い行や、教員でも既知の学年パターンでもない行(卒業生の「卒」、
    他学科、提携企業ゲスト、重複アカウント等)はNoneを返す。
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

    if not GRADE_RE.fullmatch(bracket):
        return None

    local_part = email.split("@")[0]
    student_id = local_part if STUDENT_ID_RE.fullmatch(local_part) else None
    return ParsedProfile(
        name=name, role=UserRole.student, grade=bracket, student_id=student_id
    )


def _is_deactivated_in_slack(row: dict[str, str]) -> bool:
    """Slackから退出済み(status=Deactivated)かどうか。

    billing-activeは実際にMember(現役)でも0になっているケースがあり
    信頼できないため使わない。statusのDeactivatedのみで判定する。
    """
    return row.get("status", "").strip() == "Deactivated"


async def _get_or_create_user(
    session: AsyncSession,
    *,
    email: str,
    slack_user_id: str | None,
    profile: ParsedProfile,
) -> tuple[User, bool]:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is not None:
        user.name = profile.name
        user.role = profile.role
        user.grade = profile.grade
        user.student_id = profile.student_id
        user.slack_user_id = slack_user_id
        # 以前は卒業/退学扱い(is_active=false)だったが、CSVに再登場した
        # (再入学・復学等)ケースを想定し、有効に戻す。
        user.is_active = True
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


async def _deactivate_missing_users(
    session: AsyncSession, *, active_emails: set[str]
) -> int:
    """CSVに存在しなくなった(卒業/退学した)学生を非アクティブ化する。

    質問・回答等がFK参照しているため物理削除はせず is_active=false にする。
    教員・adminはこのスクリプトが管理する対象外なので触らない
    (DEACTIVATION_MANAGED_ROLESのコメント参照)。

    active_emailsが空(CSVが空/パース失敗等)の場合は、事故で全員を
    非アクティブ化してしまわないよう、何もせずスキップする。
    """
    if not active_emails:
        print(
            "skip(非アクティブ化): CSVから有効なメールアドレスが1件も読めませんでした"
        )
        return 0

    result = await session.execute(
        select(User).where(
            User.role.in_(DEACTIVATION_MANAGED_ROLES),
            User.is_active.is_(True),
            User.email.not_in(active_emails),
        )
    )
    deactivated = 0
    for user in result.scalars().all():
        user.is_active = False
        deactivated += 1
    return deactivated


async def import_csv(path: Path) -> None:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    async with async_session() as session:
        created = 0
        updated = 0
        skipped = 0
        active_emails: set[str] = set()

        for row in rows:
            # Google OAuthのemail claimは小文字で返るため、大文字小文字の違いで
            # 同一人物が別ユーザーとして再作成されないよう小文字に正規化する。
            email = row["email"].strip().lower()

            if _is_deactivated_in_slack(row):
                skipped += 1
                print(f"skip(Deactivated): {email}")
                continue

            profile = parse_fullname(row["fullname"], email)
            if profile is None:
                skipped += 1
                print(f"skip(fullnameをパースできません): {email} {row['fullname']!r}")
                continue

            active_emails.add(email)
            _, was_created = await _get_or_create_user(
                session,
                email=email,
                slack_user_id=row["userid"].strip() or None,
                profile=profile,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        deactivated = await _deactivate_missing_users(
            session, active_emails=active_emails
        )
        await session.commit()

    print(
        f"users: +{created} created, {updated} updated, {skipped} skipped, "
        f"{deactivated} deactivated"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Slackメンバー一覧CSVから学生・教員データをDBへ投入する"
    )
    parser.add_argument("csv_path", type=Path)
    args = parser.parse_args()
    asyncio.run(import_csv(args.csv_path))


if __name__ == "__main__":
    main()
