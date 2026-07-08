import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import update

from api import auth
from api.auth import get_current_user
from api.main import app
from api.models import (
    RecruitmentTerm,
    RecruitmentTermStatus,
    Seminar,
    SeminarRecruitment,
    User,
    UserRole,
)

pytestmark = pytest.mark.asyncio


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _authenticate_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


async def _make_open_term(db_session) -> RecruitmentTerm:
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


async def _close_all_open_terms(db_session) -> None:
    """テストの前提を「現在アクティブな募集期間が無い」にするためのヘルパー。

    db_sessionは共有の開発用DBに接続しておりロールバックのみで確定しない
    ため、既存のopenな募集期間を一時的にclosedへ変更しても安全(他の
    テストファイルでも使われているパターン)。
    """
    await db_session.execute(
        update(RecruitmentTerm)
        .where(RecruitmentTerm.status == RecruitmentTermStatus.open)
        .values(status=RecruitmentTermStatus.closed)
    )
    await db_session.flush()


async def _make_seminar(db_session) -> Seminar:
    seminar = Seminar(name=_unique("seminar"))
    db_session.add(seminar)
    await db_session.flush()
    return seminar


async def _make_recruitment(
    db_session, *, term, seminar, target_grades: list[str]
) -> SeminarRecruitment:
    recruitment = SeminarRecruitment(
        term_id=term.id,
        seminar_id=seminar.id,
        capacity=10,
        target_grades=target_grades,
    )
    db_session.add(recruitment)
    await db_session.flush()
    return recruitment


async def _make_user(db_session, *, role: UserRole, grade: str | None = None) -> User:
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name=_unique("name"),
        role=role,
        grade=grade,
    )
    db_session.add(user)
    await db_session.flush()
    return user


def _names(resp) -> set[str]:
    return {s["name"] for s in resp.json()}


async def test_student_sees_seminar_targeting_their_grade(client, db_session) -> None:
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(
        db_session, term=term, seminar=seminar, target_grades=["B1"]
    )
    student = await _make_user(db_session, role=UserRole.student, grade="B1")

    _authenticate_as(student)
    resp = await client.get("/seminars")

    assert resp.status_code == 200
    assert seminar.name in _names(resp)


async def test_student_does_not_see_seminar_not_targeting_their_grade(
    client, db_session
) -> None:
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(
        db_session, term=term, seminar=seminar, target_grades=["B1"]
    )
    student = await _make_user(db_session, role=UserRole.student, grade="B2")

    _authenticate_as(student)
    resp = await client.get("/seminars")

    assert resp.status_code == 200
    assert seminar.name not in _names(resp)


async def test_student_does_not_see_seminar_with_no_recruitment_row(
    client, db_session
) -> None:
    await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)  # SeminarRecruitmentを作らない=未設定
    student = await _make_user(db_session, role=UserRole.student, grade="B1")

    _authenticate_as(student)
    resp = await client.get("/seminars")

    assert resp.status_code == 200
    assert seminar.name not in _names(resp)


async def test_student_does_not_see_seminar_with_empty_target_grades(
    client, db_session
) -> None:
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(db_session, term=term, seminar=seminar, target_grades=[])
    student = await _make_user(db_session, role=UserRole.student, grade="B1")

    _authenticate_as(student)
    resp = await client.get("/seminars")

    assert resp.status_code == 200
    assert seminar.name not in _names(resp)


async def test_student_grade_is_normalized_before_matching(client, db_session) -> None:
    # "MIDS/B1"のような表記も末尾のB1として扱う(#99のnormalize_grade)。
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(
        db_session, term=term, seminar=seminar, target_grades=["B1"]
    )
    student = await _make_user(db_session, role=UserRole.student, grade="MIDS/B1")

    _authenticate_as(student)
    resp = await client.get("/seminars")

    assert resp.status_code == 200
    assert seminar.name in _names(resp)


async def test_student_with_ungraded_grade_does_not_see_restricted_seminar(
    client, db_session
) -> None:
    # M1/M2/D1/guest/空文字はB1〜B4のどれにも正規化されないため、
    # target_gradesが全学年を含んでいても常に対象外(#99)。
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(
        db_session, term=term, seminar=seminar, target_grades=["B1", "B2", "B3", "B4"]
    )
    student = await _make_user(db_session, role=UserRole.student, grade="M1")

    _authenticate_as(student)
    resp = await client.get("/seminars")

    assert resp.status_code == 200
    assert seminar.name not in _names(resp)


async def test_teacher_sees_all_seminars_regardless_of_target_grades(
    client, db_session
) -> None:
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(db_session, term=term, seminar=seminar, target_grades=[])
    teacher = await _make_user(db_session, role=UserRole.teacher)

    _authenticate_as(teacher)
    resp = await client.get("/seminars")

    assert resp.status_code == 200
    assert seminar.name in _names(resp)


async def test_admin_sees_all_seminars_regardless_of_target_grades(
    client, db_session
) -> None:
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(db_session, term=term, seminar=seminar, target_grades=[])
    admin = await _make_user(db_session, role=UserRole.admin)

    _authenticate_as(admin)
    resp = await client.get("/seminars")

    assert resp.status_code == 200
    assert seminar.name in _names(resp)


async def test_no_filtering_when_there_is_no_active_term(client, db_session) -> None:
    await _close_all_open_terms(db_session)
    seminar = await _make_seminar(db_session)  # 対象学年の設定自体が存在しない
    student = await _make_user(db_session, role=UserRole.student, grade="M1")

    _authenticate_as(student)
    resp = await client.get("/seminars")

    assert resp.status_code == 200
    assert seminar.name in _names(resp)


async def test_list_seminars_requires_auth(client) -> None:
    resp = await client.get("/seminars")
    assert resp.status_code == 401


_SECRET = "test-internal-secret"


async def test_for_slack_bot_ignores_target_grades(
    client, db_session, monkeypatch
) -> None:
    monkeypatch.setattr(auth.settings, "internal_api_secret", _SECRET)
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(
        db_session, term=term, seminar=seminar, target_grades=["B1"]
    )

    resp = await client.get(
        "/seminars/for-slack-bot", headers={"X-Internal-Secret": _SECRET}
    )

    assert resp.status_code == 200
    assert seminar.name in _names(resp)


async def test_for_slack_bot_rejects_missing_secret(client, db_session) -> None:
    resp = await client.get("/seminars/for-slack-bot")
    assert resp.status_code == 403
