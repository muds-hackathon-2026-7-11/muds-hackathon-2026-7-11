import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from api import auth
from api.auth import get_current_user
from api.main import app
from api.models import (
    RecruitmentTerm,
    RecruitmentTermStatus,
    Seminar,
    SeminarMember,
    User,
    UserRole,
)

pytestmark = pytest.mark.asyncio


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _make_term(db_session) -> RecruitmentTerm:
    today = date.today()
    term = RecruitmentTerm(
        academic_year=3000 + int(uuid.uuid4().int % 100000),
        starts_at=today - timedelta(days=1),
        ends_at=today + timedelta(days=30),
        status=RecruitmentTermStatus.open,
    )
    db_session.add(term)
    await db_session.flush()
    return term


async def _make_seminar(db_session) -> Seminar:
    seminar = Seminar(name=_unique("seminar"))
    db_session.add(seminar)
    await db_session.flush()
    return seminar


async def _make_student(db_session, student_id: str) -> User:
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name=_unique("name"),
        role=UserRole.student,
        student_id=student_id,
    )
    db_session.add(user)
    await db_session.flush()
    return user


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


def _csv(rows: list[tuple[str, str, str]]) -> bytes:
    lines = ["student_id,seminar_id,term_id"]
    lines += [f"{sid},{seminar_id},{term_id}" for sid, seminar_id, term_id in rows]
    return ("\n".join(lines) + "\n").encode("utf-8")


async def _post(client, csv_bytes: bytes):
    return await client.post(
        "/admin/assignments/import",
        files={"file": ("assignments.csv", csv_bytes, "text/csv")},
    )


async def test_import_creates_memberships(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    term = await _make_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_student(db_session, "s2311001")
    await _make_student(db_session, "s2311002")

    resp = await _post(
        client,
        _csv(
            [
                ("s2311001", str(seminar.id), str(term.id)),
                ("s2311002", str(seminar.id), str(term.id)),
            ]
        ),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] == 2
    assert body["existing"] == 0
    assert body["errors"] == []

    count = await db_session.execute(
        select(func.count())
        .select_from(SeminarMember)
        .where(SeminarMember.term_id == term.id, SeminarMember.seminar_id == seminar.id)
    )
    assert count.scalar_one() == 2


async def test_import_is_idempotent(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    term = await _make_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_student(db_session, "s2311010")
    rows = [("s2311010", str(seminar.id), str(term.id))]

    first = await _post(client, _csv(rows))
    second = await _post(client, _csv(rows))

    assert first.json()["created"] == 1
    assert second.json()["created"] == 0
    assert second.json()["existing"] == 1


async def test_import_allows_term_based_movement(client, db_session) -> None:
    # 同じ学生が 前期term=ゼミA、後期term=ゼミB に所属(移動)できる
    _authenticate_as(await _make_admin(db_session))
    first_half = await _make_term(db_session)
    second_half = await _make_term(db_session)
    seminar_a = await _make_seminar(db_session)
    seminar_b = await _make_seminar(db_session)
    await _make_student(db_session, "s2311020")

    resp = await _post(
        client,
        _csv(
            [
                ("s2311020", str(seminar_a.id), str(first_half.id)),
                ("s2311020", str(seminar_b.id), str(second_half.id)),
            ]
        ),
    )

    assert resp.status_code == 200
    assert resp.json()["created"] == 2
    assert resp.json()["errors"] == []


async def test_import_reports_errors_for_invalid_rows(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    term = await _make_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_student(db_session, "s2311030")

    resp = await _post(
        client,
        _csv(
            [
                ("s2311030", str(seminar.id), str(term.id)),  # OK
                ("s9999999", str(seminar.id), str(term.id)),  # 未知の学生
                ("s2311030", str(uuid.uuid4()), str(term.id)),  # 未知のゼミ
                ("s2311030", str(seminar.id), str(uuid.uuid4())),  # 未知のterm
                ("s2311030", "not-a-uuid", str(term.id)),  # UUID不正
            ]
        ),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] == 1
    error_rows = {e["row"] for e in body["errors"]}
    assert error_rows == {2, 3, 4, 5}


async def test_import_requires_admin(client, db_session) -> None:
    _authenticate_as(await _make_student(db_session, "s2311040"))
    resp = await _post(client, _csv([]))
    assert resp.status_code == 403


async def test_import_requires_authentication(client, monkeypatch) -> None:
    monkeypatch.setattr(auth.settings, "auth_dev_mode", False)
    resp = await _post(client, _csv([]))
    assert resp.status_code == 401
