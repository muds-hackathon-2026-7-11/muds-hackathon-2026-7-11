import uuid
from datetime import date

import pytest

from api.models import (
    MaterialType,
    RecruitmentTerm,
    RecruitmentTermStatus,
    Seminar,
    SeminarMaterial,
    SeminarMember,
    SeminarRecruitment,
    SeminarTeacher,
    User,
    UserRole,
)

pytestmark = pytest.mark.asyncio


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _make_seminar(db_session) -> Seminar:
    seminar = Seminar(name=_unique("seminar"))
    db_session.add(seminar)
    await db_session.flush()
    return seminar


async def _make_open_term(db_session, academic_year: int) -> RecruitmentTerm:
    term = RecruitmentTerm(
        academic_year=academic_year,
        starts_at=date(academic_year, 4, 1),
        ends_at=date(academic_year, 5, 1),
        status=RecruitmentTermStatus.open,
    )
    db_session.add(term)
    await db_session.flush()
    return term


async def _make_user(
    db_session, role: UserRole, research_theme: str | None = None
) -> User:
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name=_unique("name"),
        role=role,
        research_theme=research_theme,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_get_seminar_detail_includes_teachers_materials_and_current_members(
    client, db_session
) -> None:
    academic_year = 3000 + int(uuid.uuid4().int % 1000)
    term = await _make_open_term(db_session, academic_year)
    seminar = await _make_seminar(db_session)
    db_session.add(
        SeminarRecruitment(term_id=term.id, seminar_id=seminar.id, capacity=10)
    )

    teacher1 = await _make_user(db_session, UserRole.teacher, "研究テーマA")
    teacher2 = await _make_user(db_session, UserRole.teacher, "研究テーマB")
    db_session.add(SeminarTeacher(seminar_id=seminar.id, teacher_id=teacher1.id))
    db_session.add(SeminarTeacher(seminar_id=seminar.id, teacher_id=teacher2.id))

    db_session.add(
        SeminarMaterial(
            seminar_id=seminar.id,
            url="https://example.com/a.pdf",
            type=MaterialType.pdf,
        )
    )

    current_student = await _make_user(db_session, UserRole.student, "現役の研究テーマ")
    past_student = await _make_user(db_session, UserRole.student, "過去の研究テーマ")
    db_session.add(
        SeminarMember(
            seminar_id=seminar.id,
            student_id=current_student.id,
            academic_year=academic_year,
        )
    )
    db_session.add(
        SeminarMember(
            seminar_id=seminar.id,
            student_id=past_student.id,
            academic_year=academic_year - 1,
        )
    )
    await db_session.flush()

    resp = await client.get(f"/seminars/{seminar.id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(seminar.id)
    assert body["capacity"] == 10
    assert body["recruitment_start"] == f"{academic_year}-04-01"
    assert {t["name"] for t in body["teachers"]} == {teacher1.name, teacher2.name}
    assert len(body["materials"]) == 1
    assert body["materials"][0]["url"] == "https://example.com/a.pdf"
    member_names = {m["name"] for m in body["current_members"]}
    assert member_names == {current_student.name}
    assert past_student.name not in member_names


async def test_get_seminar_detail_unknown_id_returns_404(client) -> None:
    resp = await client.get(f"/seminars/{uuid.uuid4()}")

    assert resp.status_code == 404


async def test_get_seminar_detail_without_recruitment_data_returns_empty_lists(
    client, db_session
) -> None:
    seminar = await _make_seminar(db_session)
    await db_session.flush()

    resp = await client.get(f"/seminars/{seminar.id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["capacity"] is None
    assert body["teachers"] == []
    assert body["materials"] == []
    assert body["current_members"] == []
