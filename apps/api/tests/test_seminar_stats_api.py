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
    SeminarTeacher,
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


async def _make_seminar(db_session, *, photo_url: str | None = None) -> Seminar:
    seminar = Seminar(name=_unique("seminar"), photo_url=photo_url)
    db_session.add(seminar)
    await db_session.flush()
    return seminar


async def _make_teacher(db_session, *, photo_url: str | None = None) -> User:
    teacher = User(
        google_id=_unique("google"),
        email=f"{_unique('teacher')}@example.com",
        name=_unique("teacher"),
        role=UserRole.teacher,
        photo_url=photo_url,
    )
    db_session.add(teacher)
    await db_session.flush()
    return teacher


async def _link_teacher(db_session, *, seminar: Seminar, teacher: User) -> None:
    db_session.add(SeminarTeacher(seminar_id=seminar.id, teacher_id=teacher.id))
    await db_session.flush()


async def _set_capacity(
    db_session, term, seminar, capacity: int, target_grades: list[str] | None = None
) -> None:
    db_session.add(
        SeminarRecruitment(
            term_id=term.id,
            seminar_id=seminar.id,
            capacity=capacity,
            target_grades=(
                target_grades if target_grades is not None else ["B1", "B2", "B3", "B4"]
            ),
        )
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
    # s1(B3)/s2(B3)がa@1、s3(B4)がa@2。
    assert a["priority_grade_counts"] == {"1": {"B3": 2}, "2": {"B4": 1}, "3": {}}
    assert a["ratio"] == 0.3
    assert a["continuing_count"] == 1
    # s1はseminar_aの在籍ゼミ生で、かつseminar_aを第1志望に選んでいる。
    assert a["continuing_first_choice_count"] == 1

    b = _find(stats, seminar_b.id)
    assert b["capacity"] == 4
    assert b["applicant_count"] == 2
    assert b["priority_counts"] == {"first": 1, "second": 1, "third": 0}
    # s3(B4)がb@1、s1(B3)がb@2。
    assert b["priority_grade_counts"] == {"1": {"B4": 1}, "2": {"B3": 1}, "3": {}}
    assert b["ratio"] == 0.5
    assert b["continuing_count"] == 0
    assert b["continuing_first_choice_count"] == 0


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
    assert stats["target_grades"] is None


async def test_seminar_stats_includes_target_grades(client, db_session) -> None:
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _set_capacity(db_session, term, seminar, 10, target_grades=["B1", "B2"])

    _authenticate_as(await _make_student(db_session))
    resp = await client.get("/seminars/stats")

    assert resp.status_code == 200
    stats = _find(resp.json(), seminar.id)
    assert stats["target_grades"] == ["B1", "B2"]


async def test_seminar_stats_target_grades_null_without_an_active_term(
    client, db_session
) -> None:
    academic_year = 3000 + int(uuid.uuid4().int % 1000)
    closed_term = RecruitmentTerm(
        academic_year=academic_year,
        starts_at=date.today() - timedelta(days=60),
        ends_at=date.today() - timedelta(days=30),
        status=RecruitmentTermStatus.closed,
    )
    db_session.add(closed_term)
    await db_session.flush()

    seminar = await _make_seminar(db_session)
    student = await _make_student(db_session)

    _authenticate_as(student)
    resp = await client.get("/seminars/stats")

    assert resp.status_code == 200
    stats = _find(resp.json(), seminar.id)
    assert stats["target_grades"] is None


async def test_seminar_stats_continuing_count_without_an_active_term(
    client, db_session
) -> None:
    # 募集期間が(open/日付内という意味で)アクティブでなくても、継続ゼミ生数は
    # 直近に作成された募集期間の年度を基準に数えられる(#77)。
    academic_year = 3000 + int(uuid.uuid4().int % 1000)
    closed_term = RecruitmentTerm(
        academic_year=academic_year,
        starts_at=date.today() - timedelta(days=60),
        ends_at=date.today() - timedelta(days=30),
        status=RecruitmentTermStatus.closed,
    )
    db_session.add(closed_term)
    await db_session.flush()

    seminar = await _make_seminar(db_session)
    student = await _make_student(db_session)
    db_session.add(
        SeminarMember(
            seminar_id=seminar.id, student_id=student.id, term_id=closed_term.id
        )
    )
    await db_session.flush()

    _authenticate_as(student)
    resp = await client.get("/seminars/stats")

    assert resp.status_code == 200
    stats = _find(resp.json(), seminar.id)
    assert stats["continuing_count"] == 1
    # 募集期間がアクティブでないため、志望集計自体は0のまま。
    assert stats["applicant_count"] == 0
    assert stats["continuing_first_choice_count"] == 0


async def test_seminar_stats_continuing_first_choice_count(client, db_session) -> None:
    # 継続希望人数は「在籍ゼミ生」かつ「同じゼミを第1志望」の両方を満たす
    # 学生だけを数える。それ以外(別ゼミが第1志望/自分のゼミだが第2志望)は
    # 数えないことを確認する。
    term = await _make_open_term(db_session)
    seminar_a = await _make_seminar(db_session)
    seminar_b = await _make_seminar(db_session)
    await _set_capacity(db_session, term, seminar_a, 10)
    await _set_capacity(db_session, term, seminar_b, 10)

    stays = await _make_student(db_session, grade="B3")  # a在籍、a@1
    leaves = await _make_student(
        db_session, grade="B3"
    )  # a在籍、b@1(継続希望に数えない)
    ranks_second = await _make_student(db_session, grade="B3")  # a在籍、a@2

    for student, choices in (
        (stays, [(seminar_a, 1)]),
        (leaves, [(seminar_b, 1)]),
        (ranks_second, [(seminar_b, 1), (seminar_a, 2)]),
    ):
        await _make_application(
            db_session,
            term=term,
            student=student,
            status=ApplicationStatus.submitted,
            choices=choices,
        )
    for student in (stays, leaves, ranks_second):
        db_session.add(
            SeminarMember(
                seminar_id=seminar_a.id, student_id=student.id, term_id=term.id
            )
        )
    await db_session.flush()

    _authenticate_as(await _make_student(db_session))
    resp = await client.get("/seminars/stats")

    assert resp.status_code == 200
    a = _find(resp.json(), seminar_a.id)
    assert a["continuing_count"] == 3
    assert a["continuing_first_choice_count"] == 1


async def test_seminar_stats_includes_seminar_photo_url(client, db_session) -> None:
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session, photo_url="https://example.com/lab.jpg")
    await _set_capacity(db_session, term, seminar, 10)

    _authenticate_as(await _make_student(db_session))
    resp = await client.get("/seminars/stats")

    assert resp.status_code == 200
    stats = _find(resp.json(), seminar.id)
    assert stats["photo_url"] == "https://example.com/lab.jpg"


async def test_seminar_stats_uses_sole_teacher_photo(client, db_session) -> None:
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _set_capacity(db_session, term, seminar, 10)
    teacher = await _make_teacher(db_session, photo_url="https://example.com/t.jpg")
    await _link_teacher(db_session, seminar=seminar, teacher=teacher)

    _authenticate_as(await _make_student(db_session))
    resp = await client.get("/seminars/stats")

    assert resp.status_code == 200
    stats = _find(resp.json(), seminar.id)
    assert stats["teacher_photo_url"] == "https://example.com/t.jpg"


async def test_seminar_stats_teacher_photo_null_with_multiple_teachers(
    client, db_session
) -> None:
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _set_capacity(db_session, term, seminar, 10)
    teacher_a = await _make_teacher(db_session, photo_url="https://example.com/a.jpg")
    teacher_b = await _make_teacher(db_session, photo_url="https://example.com/b.jpg")
    await _link_teacher(db_session, seminar=seminar, teacher=teacher_a)
    await _link_teacher(db_session, seminar=seminar, teacher=teacher_b)

    _authenticate_as(await _make_student(db_session))
    resp = await client.get("/seminars/stats")

    assert resp.status_code == 200
    stats = _find(resp.json(), seminar.id)
    # 教員が複数いる場合は、特定の1人を代表にできないためnull。
    assert stats["teacher_photo_url"] is None


async def test_seminar_stats_teacher_photo_null_with_no_teachers(
    client, db_session
) -> None:
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _set_capacity(db_session, term, seminar, 10)

    _authenticate_as(await _make_student(db_session))
    resp = await client.get("/seminars/stats")

    assert resp.status_code == 200
    stats = _find(resp.json(), seminar.id)
    assert stats["teacher_photo_url"] is None


async def test_seminar_stats_photo_fields_present_without_an_active_term(
    client, db_session
) -> None:
    seminar = await _make_seminar(db_session, photo_url="https://example.com/lab.jpg")

    _authenticate_as(await _make_student(db_session))
    resp = await client.get("/seminars/stats")

    assert resp.status_code == 200
    stats = _find(resp.json(), seminar.id)
    assert stats["photo_url"] == "https://example.com/lab.jpg"
    assert stats["teacher_photo_url"] is None


async def test_seminar_stats_requires_auth(client) -> None:
    # get_current_user を override しない=未認証 → 401
    resp = await client.get("/seminars/stats")
    assert resp.status_code == 401
