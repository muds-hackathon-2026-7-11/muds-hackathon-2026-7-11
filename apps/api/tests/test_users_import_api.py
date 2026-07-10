import uuid

import pytest
from sqlalchemy import select

from api.auth import get_current_user
from api.main import app
from api.models import User, UserRole

pytestmark = pytest.mark.asyncio

_CSV_HEADER = (
    "username,email,status,billing-active,has-2fa,has-sso,userid,"
    "fullname,displayname,expiration-timestamp"
)


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _authenticate_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


async def _make_admin(db_session) -> User:
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('admin')}@example.com",
        name=_unique("admin"),
        role=UserRole.admin,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_teacher(db_session) -> User:
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('teacher')}@example.com",
        name=_unique("teacher"),
        role=UserRole.teacher,
    )
    db_session.add(user)
    await db_session.flush()
    return user


def _csv_row(
    *, email: str, fullname: str, status: str = "Member", userid: str | None = None
) -> str:
    uid = userid or f"U-{email.split('@')[0]}"
    return f"{email.split('@')[0]},{email},{status},1,0,0,{uid},{fullname},{fullname},"


def _csv(rows: list[str]) -> bytes:
    return ("\n".join([_CSV_HEADER, *rows]) + "\n").encode("utf-8")


async def _post(client, csv_bytes: bytes):
    return await client.post(
        "/admin/users/import",
        files={"file": ("slack_member.csv", csv_bytes, "text/csv")},
    )


async def test_import_creates_and_updates_users(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    email = f"{_unique('s0000009-test')}@stu.musashino-u.ac.jp"

    resp = await _post(
        client,
        _csv([_csv_row(email=email, fullname="[B1] 新規 太郎 / Taro Shinki")]),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] == 1
    assert body["updated"] == 0

    user = (
        await db_session.execute(select(User).where(User.email == email))
    ).scalar_one()
    assert user.grade == "B1"

    resp2 = await _post(
        client,
        _csv([_csv_row(email=email, fullname="[B2] 新規 太郎 / Taro Shinki")]),
    )

    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["created"] == 0
    assert body2["updated"] == 1
    await db_session.refresh(user)
    assert user.grade == "B2"


async def test_import_reports_skipped_rows(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    deactivated_email = f"{_unique('deactivated-test')}@example.com"
    unparseable_email = f"{_unique('unparseable-test')}@example.com"

    resp = await _post(
        client,
        _csv(
            [
                _csv_row(
                    email=deactivated_email,
                    fullname="[B1] 退出済み 太郎 / Taro Taishutsu",
                    status="Deactivated",
                ),
                _csv_row(email=unparseable_email, fullname="山田 太郎"),
            ]
        ),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] == 0
    assert len(body["skipped"]) == 2
    reasons_by_email = {row["email"]: row["reason"] for row in body["skipped"]}
    assert "Deactivated" in reasons_by_email[deactivated_email]
    assert "パース" in reasons_by_email[unparseable_email]


async def test_import_skips_teacher_rows(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    teacher_email = f"{_unique('teacher-test')}@example.com"

    resp = await _post(
        client,
        _csv([_csv_row(email=teacher_email, fullname="[教員] 客員 教授 / Kyakuin")]),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] == 0
    assert len(body["skipped"]) == 1
    assert body["skipped"][0]["email"] == teacher_email

    result = await db_session.execute(select(User).where(User.email == teacher_email))
    assert result.scalar_one_or_none() is None


async def test_import_deactivates_students_missing_from_csv(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    graduate_email = f"{_unique('s0000010-test')}@stu.musashino-u.ac.jp"
    await _post(
        client,
        _csv([_csv_row(email=graduate_email, fullname="[B4] 卒業予定 花子 / Hanako")]),
    )
    user = (
        await db_session.execute(select(User).where(User.email == graduate_email))
    ).scalar_one()
    assert user.is_active is True

    # 翌年のCSVにこの学生は含まれない(=卒業/退学した)。他の在学生は含める。
    other_email = f"{_unique('s0000011-test')}@stu.musashino-u.ac.jp"
    resp = await _post(
        client,
        _csv([_csv_row(email=other_email, fullname="[B1] 在学 次郎 / Jiro")]),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["deactivated"] >= 1
    await db_session.refresh(user)
    assert user.is_active is False


async def test_import_requires_admin(client, db_session) -> None:
    _authenticate_as(await _make_teacher(db_session))

    resp = await _post(client, _csv([]))

    assert resp.status_code == 403
