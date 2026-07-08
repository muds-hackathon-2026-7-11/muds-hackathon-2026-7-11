import uuid
from datetime import date

import pytest
from sqlalchemy import select

from api.import_seminar_members import (
    _find_seminar,
    _find_student,
    _upsert_membership,
)
from api.models import (
    RecruitmentTerm,
    RecruitmentTermStatus,
    Seminar,
    SeminarMember,
    User,
)

pytestmark = pytest.mark.asyncio


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _make_student(db_session, *, student_id: str) -> User:
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name=_unique("name"),
        role="student",
        student_id=student_id,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_seminar(db_session) -> Seminar:
    seminar = Seminar(name=_unique("seminar"))
    db_session.add(seminar)
    await db_session.flush()
    return seminar


async def _make_term(db_session, academic_year: int) -> RecruitmentTerm:
    term = RecruitmentTerm(
        academic_year=academic_year,
        starts_at=date(academic_year, 4, 1),
        ends_at=date(academic_year, 12, 31),
        status=RecruitmentTermStatus.open,
    )
    db_session.add(term)
    await db_session.flush()
    return term


async def test_find_student_matches_s_prefix(db_session) -> None:
    number = str(3000000 + int(uuid.uuid4().int % 900000))
    student = await _make_student(db_session, student_id=f"s{number}")

    found = await _find_student(db_session, student_number=number)

    assert found is not None
    assert found.id == student.id


async def test_find_student_matches_g_prefix(db_session) -> None:
    number = str(3000000 + int(uuid.uuid4().int % 900000))
    student = await _make_student(db_session, student_id=f"g{number}")

    found = await _find_student(db_session, student_number=number)

    assert found is not None
    assert found.id == student.id


async def test_find_student_returns_none_when_not_found(db_session) -> None:
    found = await _find_student(db_session, student_number="0000000")
    assert found is None


async def test_find_seminar_matches_exact_name(db_session) -> None:
    seminar = await _make_seminar(db_session)

    found = await _find_seminar(db_session, name=seminar.name)

    assert found is not None
    assert found.id == seminar.id


async def test_upsert_membership_creates_when_absent(db_session) -> None:
    student = await _make_student(db_session, student_id=f"s{_unique('9')[:7]}")
    seminar = await _make_seminar(db_session)
    term = await _make_term(db_session, 3000 + int(uuid.uuid4().int % 1000))

    result = await _upsert_membership(
        db_session, seminar=seminar, student=student, term=term
    )
    await db_session.flush()

    assert result == "created"
    row = (
        await db_session.execute(
            select(SeminarMember).where(
                SeminarMember.student_id == student.id,
                SeminarMember.term_id == term.id,
            )
        )
    ).scalar_one()
    assert row.seminar_id == seminar.id


async def test_upsert_membership_is_idempotent(db_session) -> None:
    student = await _make_student(db_session, student_id=f"s{_unique('9')[:7]}")
    seminar = await _make_seminar(db_session)
    term = await _make_term(db_session, 3000 + int(uuid.uuid4().int % 1000))

    await _upsert_membership(db_session, seminar=seminar, student=student, term=term)
    await db_session.flush()

    result = await _upsert_membership(
        db_session, seminar=seminar, student=student, term=term
    )

    assert result == "unchanged"


async def test_upsert_membership_consolidates_duplicate_rows(db_session) -> None:
    # 同一学生・同一年度に(過去の重複データ等で)複数の所属行が残っている
    # ケース。scalar_one_or_none()だとMultipleResultsFoundで落ちて
    # バッチ全体が失敗するため、CSVの内容(new_seminar)に1件へ統一する。
    student = await _make_student(db_session, student_id=f"s{_unique('9')[:7]}")
    stale_seminar_a = await _make_seminar(db_session)
    stale_seminar_b = await _make_seminar(db_session)
    new_seminar = await _make_seminar(db_session)
    term = await _make_term(db_session, 3000 + int(uuid.uuid4().int % 1000))

    db_session.add_all(
        [
            SeminarMember(
                seminar_id=stale_seminar_a.id, student_id=student.id, term_id=term.id
            ),
            SeminarMember(
                seminar_id=stale_seminar_b.id, student_id=student.id, term_id=term.id
            ),
        ]
    )
    await db_session.flush()

    result = await _upsert_membership(
        db_session, seminar=new_seminar, student=student, term=term
    )
    await db_session.flush()

    assert result == "updated"
    rows = (
        (
            await db_session.execute(
                select(SeminarMember).where(
                    SeminarMember.student_id == student.id,
                    SeminarMember.term_id == term.id,
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].seminar_id == new_seminar.id


async def test_upsert_membership_corrects_seminar_when_changed(db_session) -> None:
    student = await _make_student(db_session, student_id=f"s{_unique('9')[:7]}")
    old_seminar = await _make_seminar(db_session)
    new_seminar = await _make_seminar(db_session)
    term = await _make_term(db_session, 3000 + int(uuid.uuid4().int % 1000))

    await _upsert_membership(
        db_session, seminar=old_seminar, student=student, term=term
    )
    await db_session.flush()

    result = await _upsert_membership(
        db_session, seminar=new_seminar, student=student, term=term
    )
    await db_session.flush()

    assert result == "updated"
    row = (
        await db_session.execute(
            select(SeminarMember).where(
                SeminarMember.student_id == student.id,
                SeminarMember.term_id == term.id,
            )
        )
    ).scalar_one()
    assert row.seminar_id == new_seminar.id
