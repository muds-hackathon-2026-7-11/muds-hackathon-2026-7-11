import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from api import auth
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
    year = 3000 + int(uuid.uuid4().int % 1000)
    today = date.today()
    term = RecruitmentTerm(
        academic_year=year,
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


async def _make_user(
    db_session,
    role: UserRole,
    *,
    grade: str | None = None,
    is_active: bool = True,
    student_id: str | None = None,
) -> User:
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name=_unique("name"),
        role=role,
        grade=grade,
        is_active=is_active,
        student_id=student_id,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _link_teacher(db_session, seminar: Seminar, teacher: User) -> None:
    db_session.add(SeminarTeacher(seminar_id=seminar.id, teacher_id=teacher.id))
    await db_session.flush()


async def _apply(
    db_session,
    *,
    term: RecruitmentTerm,
    student: User,
    status: ApplicationStatus,
    choices: list[tuple[Seminar, int, str]],
) -> None:
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
    for seminar, priority, reason in choices:
        db_session.add(
            ApplicationChoice(
                application_form_id=form.id,
                seminar_id=seminar.id,
                priority=priority,
                reason=reason,
            )
        )
    await db_session.flush()


def _authenticate_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


def _seminar_entry(body: list[dict], seminar_id) -> dict:
    return next(s for s in body if s["seminar_id"] == str(seminar_id))


# --- 応募者一覧 ---


async def test_applicants_grouped_with_priority_and_past_seminars(
    client, db_session
) -> None:
    term = await _make_open_term(db_session)
    teacher = await _make_user(db_session, UserRole.teacher)
    other_teacher = await _make_user(db_session, UserRole.teacher)
    my_seminar = await _make_seminar(db_session)
    other_seminar = await _make_seminar(db_session)
    past_seminar = await _make_seminar(db_session)
    await _link_teacher(db_session, my_seminar, teacher)
    await _link_teacher(db_session, other_seminar, other_teacher)

    s1 = await _make_user(
        db_session, UserRole.student, grade="B3", student_id="s2311001"
    )
    s2 = await _make_user(
        db_session, UserRole.student, grade="B4", student_id="s2311002"
    )
    # s1: 自ゼミ第1志望 + 他ゼミ第2志望 / s2: 自ゼミ第2志望
    await _apply(
        db_session,
        term=term,
        student=s1,
        status=ApplicationStatus.submitted,
        choices=[(my_seminar, 1, "ぜひ入りたい"), (other_seminar, 2, "次点")],
    )
    await _apply(
        db_session,
        term=term,
        student=s2,
        status=ApplicationStatus.submitted,
        choices=[(my_seminar, 2, "興味があります")],
    )
    # s1 の過去所属(前年度=別の募集ラウンド)
    past_term = RecruitmentTerm(
        academic_year=term.academic_year - 1,
        starts_at=date(term.academic_year - 1, 4, 1),
        ends_at=date(term.academic_year - 1, 9, 30),
        status=RecruitmentTermStatus.closed,
    )
    db_session.add(past_term)
    await db_session.flush()
    db_session.add(
        SeminarMember(
            seminar_id=past_seminar.id,
            student_id=s1.id,
            term_id=past_term.id,
        )
    )
    await db_session.flush()

    _authenticate_as(teacher)
    resp = await client.get("/teacher/applicants")

    assert resp.status_code == 200
    body = resp.json()
    # 担当ゼミ(my_seminar)のみ。other_seminar は含まれない
    assert [s["seminar_id"] for s in body] == [str(my_seminar.id)]

    entry = _seminar_entry(body, my_seminar.id)
    applicants = {a["name"]: a for a in entry["applicants"]}
    assert len(applicants) == 2
    assert applicants[s1.name]["priority"] == 1
    assert applicants[s1.name]["student_id"] == "s2311001"
    assert applicants[s1.name]["grade"] == "B3"
    assert applicants[s1.name]["reason"] == "ぜひ入りたい"
    assert [p["seminar_name"] for p in applicants[s1.name]["past_seminars"]] == [
        past_seminar.name
    ]
    assert applicants[s2.name]["priority"] == 2


async def test_applicants_excludes_draft_and_inactive(client, db_session) -> None:
    term = await _make_open_term(db_session)
    teacher = await _make_user(db_session, UserRole.teacher)
    seminar = await _make_seminar(db_session)
    await _link_teacher(db_session, seminar, teacher)

    ok = await _make_user(db_session, UserRole.student, grade="B3")
    drafter = await _make_user(db_session, UserRole.student, grade="B3")
    inactive = await _make_user(
        db_session, UserRole.student, grade="B3", is_active=False
    )
    await _apply(
        db_session,
        term=term,
        student=ok,
        status=ApplicationStatus.submitted,
        choices=[(seminar, 1, "理由")],
    )
    await _apply(
        db_session,
        term=term,
        student=drafter,
        status=ApplicationStatus.draft,
        choices=[(seminar, 1, "理由")],
    )
    await _apply(
        db_session,
        term=term,
        student=inactive,
        status=ApplicationStatus.submitted,
        choices=[(seminar, 1, "理由")],
    )

    _authenticate_as(teacher)
    resp = await client.get("/teacher/applicants")

    assert resp.status_code == 200
    entry = _seminar_entry(resp.json(), seminar.id)
    assert [a["name"] for a in entry["applicants"]] == [ok.name]


async def test_applicants_csv(client, db_session) -> None:
    term = await _make_open_term(db_session)
    teacher = await _make_user(db_session, UserRole.teacher)
    seminar = await _make_seminar(db_session)
    await _link_teacher(db_session, seminar, teacher)
    student = await _make_user(
        db_session, UserRole.student, grade="B3", student_id="s2311777"
    )
    await _apply(
        db_session,
        term=term,
        student=student,
        status=ApplicationStatus.submitted,
        choices=[(seminar, 1, "志望します")],
    )

    _authenticate_as(teacher)
    resp = await client.get("/teacher/applicants.csv")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]
    text = resp.text
    assert "学籍番号" in text
    assert "s2311777" in text
    assert student.name in text


# --- 自ゼミ定員設定 ---


async def test_set_own_seminar_recruitment(client, db_session) -> None:
    term = await _make_open_term(db_session)
    teacher = await _make_user(db_session, UserRole.teacher)
    seminar = await _make_seminar(db_session)
    await _link_teacher(db_session, seminar, teacher)

    _authenticate_as(teacher)
    resp = await client.patch(
        f"/teacher/seminars/{seminar.id}/recruitment",
        json={"capacity": 12, "target_grades": ["B1", "B2"]},
    )
    assert resp.status_code == 200
    assert resp.json()["capacity"] == 12
    assert resp.json()["target_grades"] == ["B1", "B2"]

    result = await db_session.execute(
        select(SeminarRecruitment).where(
            SeminarRecruitment.term_id == term.id,
            SeminarRecruitment.seminar_id == seminar.id,
        )
    )
    assert result.scalar_one().capacity == 12


async def test_set_own_seminar_recruitment_keeps_target_grades_when_omitted(
    client, db_session
) -> None:
    await _make_open_term(db_session)
    teacher = await _make_user(db_session, UserRole.teacher)
    seminar = await _make_seminar(db_session)
    await _link_teacher(db_session, seminar, teacher)

    _authenticate_as(teacher)
    await client.patch(
        f"/teacher/seminars/{seminar.id}/recruitment",
        json={"capacity": 12, "target_grades": ["B1"]},
    )

    # target_gradesを送らない更新は、既存の値を据え置く。
    resp = await client.patch(
        f"/teacher/seminars/{seminar.id}/recruitment",
        json={"capacity": 20},
    )
    assert resp.status_code == 200
    assert resp.json()["capacity"] == 20
    assert resp.json()["target_grades"] == ["B1"]


async def test_set_recruitment_forbidden_for_other_teachers_seminar(
    client, db_session
) -> None:
    await _make_open_term(db_session)
    teacher = await _make_user(db_session, UserRole.teacher)
    not_mine = await _make_seminar(db_session)  # 担当リンクを作らない

    _authenticate_as(teacher)
    resp = await client.patch(
        f"/teacher/seminars/{not_mine.id}/recruitment", json={"capacity": 5}
    )
    assert resp.status_code == 403


async def test_set_recruitment_without_active_term_is_400(
    client, db_session, monkeypatch
) -> None:
    teacher = await _make_user(db_session, UserRole.teacher)
    seminar = await _make_seminar(db_session)
    await _link_teacher(db_session, seminar, teacher)

    async def _no_term(_db):
        return None

    monkeypatch.setattr("api.routers.teacher.get_current_term", _no_term)

    _authenticate_as(teacher)
    resp = await client.patch(
        f"/teacher/seminars/{seminar.id}/recruitment", json={"capacity": 5}
    )
    assert resp.status_code == 400


# --- 認可 ---


async def test_requires_teacher_role(client, db_session) -> None:
    _authenticate_as(await _make_user(db_session, UserRole.student))
    resp = await client.get("/teacher/applicants")
    assert resp.status_code == 403


async def test_requires_authentication(client, monkeypatch) -> None:
    monkeypatch.setattr(auth.settings, "auth_dev_mode", False)
    resp = await client.get("/teacher/applicants")
    assert resp.status_code == 401
