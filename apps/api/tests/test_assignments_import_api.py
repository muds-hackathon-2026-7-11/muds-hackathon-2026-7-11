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


def _csv(rows: list[tuple[str, str]]) -> bytes:
    lines = ["student_id,seminar_id"]
    lines += [f"{sid},{seminar_id}" for sid, seminar_id in rows]
    return ("\n".join(lines) + "\n").encode("utf-8")


async def _post(client, csv_bytes: bytes, *, term_id):
    return await client.post(
        "/admin/assignments/import",
        data={"term_id": str(term_id)},
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
        _csv([("s2311001", str(seminar.id)), ("s2311002", str(seminar.id))]),
        term_id=term.id,
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
    rows = [("s2311010", str(seminar.id))]

    first = await _post(client, _csv(rows), term_id=term.id)
    second = await _post(client, _csv(rows), term_id=term.id)

    assert first.json()["created"] == 1
    assert second.json()["created"] == 0
    assert second.json()["existing"] == 1


async def test_import_allows_term_based_movement(client, db_session) -> None:
    # 同じ学生が 前期term=ゼミA、後期term=ゼミB に所属(移動)できる。
    # term_idはアップロード単位で1つなので、ラウンドごとに別アップロードになる。
    _authenticate_as(await _make_admin(db_session))
    first_half = await _make_term(db_session)
    second_half = await _make_term(db_session)
    seminar_a = await _make_seminar(db_session)
    seminar_b = await _make_seminar(db_session)
    await _make_student(db_session, "s2311020")

    first = await _post(
        client, _csv([("s2311020", str(seminar_a.id))]), term_id=first_half.id
    )
    second = await _post(
        client, _csv([("s2311020", str(seminar_b.id))]), term_id=second_half.id
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["created"] == 1
    assert second.json()["created"] == 1


async def test_import_reports_errors_for_invalid_rows(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    term = await _make_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_student(db_session, "s2311030")

    resp = await _post(
        client,
        _csv(
            [
                ("s2311030", str(seminar.id)),  # OK
                ("s9999999", str(seminar.id)),  # 未知の学生
                ("s2311030", str(uuid.uuid4())),  # 未知のゼミID
                ("s2311030", "存在しないゼミ名"),  # 未知のゼミ名
            ]
        ),
        term_id=term.id,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] == 1
    errors_by_row = {e["row"]: e["reason"] for e in body["errors"]}
    assert set(errors_by_row) == {2, 3, 4}
    assert "学生が見つかりません" in errors_by_row[2]
    assert "ゼミが見つかりません" in errors_by_row[3]
    assert "ゼミが見つかりません" in errors_by_row[4]


async def test_import_resolves_seminar_by_name(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    term = await _make_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_student(db_session, "s2311060")

    resp = await _post(client, _csv([("s2311060", seminar.name)]), term_id=term.id)

    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] == 1
    assert body["errors"] == []

    count = await db_session.execute(
        select(func.count())
        .select_from(SeminarMember)
        .where(SeminarMember.term_id == term.id, SeminarMember.seminar_id == seminar.id)
    )
    assert count.scalar_one() == 1


async def test_import_resolves_student_by_bare_number(client, db_session) -> None:
    # 実運用のCSV(data/users_seminar.csv)はs/g接頭辞の無い学籍番号(生数字)を
    # 使うため、その形式でもDBのstudent_id("s"+数字)と照合できる必要がある。
    # 番号は共有DBの実データ(data/users_seminar.csv由来)と衝突しないよう
    # 一意な値を生成する。
    _authenticate_as(await _make_admin(db_session))
    term = await _make_term(db_session)
    seminar = await _make_seminar(db_session)
    bare_number = str(900_000_000 + (uuid.uuid4().int % 99_999_999))
    student = await _make_student(db_session, f"s{bare_number}")

    resp = await _post(client, _csv([(bare_number, str(seminar.id))]), term_id=term.id)

    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] == 1
    assert body["errors"] == []

    count = await db_session.execute(
        select(func.count())
        .select_from(SeminarMember)
        .where(
            SeminarMember.term_id == term.id,
            SeminarMember.student_id == student.id,
        )
    )
    assert count.scalar_one() == 1


async def test_import_rejects_unknown_term(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    seminar = await _make_seminar(db_session)
    await _make_student(db_session, "s2311050")

    resp = await _post(
        client,
        _csv([("s2311050", str(seminar.id))]),
        term_id=uuid.uuid4(),
    )

    assert resp.status_code == 404


async def test_import_rejects_malformed_term_id(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))

    resp = await client.post(
        "/admin/assignments/import",
        data={"term_id": "not-a-uuid"},
        files={"file": ("assignments.csv", _csv([]), "text/csv")},
    )

    assert resp.status_code == 422


async def test_import_requires_admin(client, db_session) -> None:
    _authenticate_as(await _make_student(db_session, "s2311040"))
    term = await _make_term(db_session)
    resp = await _post(client, _csv([]), term_id=term.id)
    assert resp.status_code == 403


async def test_import_requires_authentication(client, monkeypatch) -> None:
    monkeypatch.setattr(auth.settings, "auth_dev_mode", False)
    resp = await _post(client, _csv([]), term_id=uuid.uuid4())
    assert resp.status_code == 401
