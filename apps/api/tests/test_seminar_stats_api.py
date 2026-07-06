import uuid
from datetime import date, datetime, timedelta, timezone

import pytest

from api.auth import get_current_user
from api.main import app
from api.models import (
    ApplicationChoice,
    ApplicationForm,
    ApplicationStatus,
    RecruitmentTerm,
    RecruitmentTermStatus,
    Seminar,
    SeminarMember,
    SeminarRecruitment,
    User,
    UserRole,
)

pytestmark = pytest.mark.asyncio


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _make_open_term(db_session) -> RecruitmentTerm:
    # seed(2026)と衝突しないよう遠い未来の年度を使い、これを「現在の募集」にする。
    academic_year = 3000 + int(uuid.uuid4().int % 1000)
    today = date.today()
    term = RecruitmentTerm(
        academic_year=academic_year,
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


async def _set_capacity(db_session, term, seminar, capacity: int) -> None:
    db_session.add(
        SeminarRecruitment(term_id=term.id, seminar_id=seminar.id, capacity=capacity)
    )
    await db_session.flush()


async def _make_student(
    db_session, *, grade: str | None = None, is_active: bool = True
) -> User:
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name=_unique("name"),
        role=UserRole.student,
        grade=grade,
        is_active=is_active,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_application(
    db_session,
    *,
    term,
    student,
    status: ApplicationStatus,
    choices: list[tuple[Seminar, int]],
) -> ApplicationForm:
    form = ApplicationForm(
        term_id=term.id,
        student_id=student.id,
        status=status,
        submitted_at=(
            datetime.now(timezone.utc)
            if status == ApplicationStatus.submitted
            else None
        ),
    )
    db_session.add(form)
    await db_session.flush()
    for seminar, priority in choices:
        db_session.add(
            ApplicationChoice(
                application_form_id=form.id,
                seminar_id=seminar.id,
                priority=priority,
                reason="理由",
            )
        )
    await db_session.flush()
    return form


def _find(stats: list[dict], seminar_id) -> dict:
    return next(s for s in stats if s["id"] == str(seminar_id))


def _authenticate_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


async def test_seminar_stats_aggregates_counts_ratio_grade(client, db_session) -> None:
    term = await _make_open_term(db_session)
    seminar_a = await _make_seminar(db_session)
    seminar_b = await _make_seminar(db_session)
    await _set_capacity(db_session, term, seminar_a, 10)
    await _set_capacity(db_session, term, seminar_b, 4)

    s1 = await _make_student(db_session, grade="B3")
    s2 = await _make_student(db_session, grade="B3")
    s3 = await _make_student(db_session, grade="B4")
    await _make_application(
        db_session,
        term=term,
        student=s1,
        status=ApplicationStatus.submitted,
        choices=[(seminar_a, 1), (seminar_b, 2)],
    )
    await _make_application(
        db_session,
        term=term,
        student=s2,
        status=ApplicationStatus.submitted,
        choices=[(seminar_a, 1)],
    )
    await _make_application(
        db_session,
        term=term,
        student=s3,
        status=ApplicationStatus.submitted,
        choices=[(seminar_a, 2), (seminar_b, 1)],
    )
    # 継続者(現ラウンドの所属ゼミ生)を1名
    db_session.add(
        SeminarMember(seminar_id=seminar_a.id, student_id=s1.id, term_id=term.id)
    )
    await db_session.flush()

    _authenticate_as(await _make_student(db_session))
    resp = await client.get("/seminars/stats")

    assert resp.status_code == 200
    stats = resp.json()

    a = _find(stats, seminar_a.id)
    assert a["capacity"] == 10
    assert a["applicant_count"] == 3
    assert a["priority_counts"] == {"first": 2, "second": 1, "third": 0}
    assert a["grade_counts"] == {"B3": 2, "B4": 1}
    assert a["ratio"] == 0.3
    assert a["continuing_count"] == 1

    b = _find(stats, seminar_b.id)
    assert b["capacity"] == 4
    assert b["applicant_count"] == 2
    assert b["priority_counts"] == {"first": 1, "second": 1, "third": 0}
    assert b["ratio"] == 0.5
    assert b["continuing_count"] == 0


async def test_seminar_stats_excludes_draft_and_inactive(client, db_session) -> None:
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _set_capacity(db_session, term, seminar, 5)

    ok = await _make_student(db_session, grade="B3")
    drafter = await _make_student(db_session, grade="B3")
    inactive = await _make_student(db_session, grade="B3", is_active=False)
    await _make_application(
        db_session,
        term=term,
        student=ok,
        status=ApplicationStatus.submitted,
        choices=[(seminar, 1)],
    )
    await _make_application(
        db_session,
        term=term,
        student=drafter,
        status=ApplicationStatus.draft,
        choices=[(seminar, 1)],
    )
    await _make_application(
        db_session,
        term=term,
        student=inactive,
        status=ApplicationStatus.submitted,
        choices=[(seminar, 1)],
    )

    _authenticate_as(ok)
    resp = await client.get("/seminars/stats")

    assert resp.status_code == 200
    stats = _find(resp.json(), seminar.id)
    # draft と 非アクティブ学生は除外され、有効な1件だけ数える
    assert stats["applicant_count"] == 1
    assert stats["priority_counts"] == {"first": 1, "second": 0, "third": 0}


async def test_seminar_stats_ratio_null_when_no_capacity(client, db_session) -> None:
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)  # SeminarRecruitment を作らない=定員なし

    student = await _make_student(db_session, grade="B4")
    await _make_application(
        db_session,
        term=term,
        student=student,
        status=ApplicationStatus.submitted,
        choices=[(seminar, 1)],
    )

    _authenticate_as(student)
    resp = await client.get("/seminars/stats")

    assert resp.status_code == 200
    stats = _find(resp.json(), seminar.id)
    assert stats["capacity"] is None
    assert stats["applicant_count"] == 1
    assert stats["ratio"] is None


async def test_seminar_stats_requires_auth(client) -> None:
    # get_current_user を override しない=未認証 → 401
    resp = await client.get("/seminars/stats")
    assert resp.status_code == 401
