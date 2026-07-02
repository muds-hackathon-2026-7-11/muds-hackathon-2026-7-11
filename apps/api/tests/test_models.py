import uuid
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from api.models import (
    ApplicationChoice,
    ApplicationForm,
    Seminar,
    SeminarMember,
    User,
    UserRole,
)

pytestmark = pytest.mark.asyncio


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _make_user(db_session, role: UserRole = UserRole.student) -> User:
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name="Test User",
        role=role,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_seminar(db_session) -> Seminar:
    seminar = Seminar(
        name=_unique("seminar"),
        capacity=10,
        recruitment_start=date(2026, 4, 1),
        recruitment_end=date(2026, 5, 1),
    )
    db_session.add(seminar)
    await db_session.flush()
    return seminar


async def test_create_user(db_session) -> None:
    user = await _make_user(db_session)
    assert user.id is not None
    assert user.role == UserRole.student


async def test_invalid_role_is_rejected_by_db_check_constraint(db_session) -> None:
    # ORM経由だとPythonのEnum型チェックで弾かれるため、CHECK制約自体を
    # 検証するにはORMをバイパスした生SQLで確認する。
    with pytest.raises(IntegrityError):
        await db_session.execute(
            text(
                "INSERT INTO users (id, google_id, email, name, role) "
                "VALUES (gen_random_uuid(), :google_id, :email, 'test', 'invalid_role')"
            ),
            {"google_id": _unique("google"), "email": f"{_unique('bad')}@example.com"},
        )


async def test_deleting_seminar_cascades_to_seminar_members(db_session) -> None:
    seminar = await _make_seminar(db_session)
    student = await _make_user(db_session)
    db_session.add(
        SeminarMember(
            seminar_id=seminar.id,
            student_id=student.id,
            academic_year=2026,
            is_current=True,
        )
    )
    await db_session.flush()

    await db_session.delete(seminar)
    await db_session.flush()

    remaining = await db_session.execute(
        text("SELECT COUNT(*) FROM seminar_members WHERE seminar_id = :id"),
        {"id": seminar.id},
    )
    assert remaining.scalar_one() == 0


async def test_application_choice_priority_must_be_unique_per_form(db_session) -> None:
    student = await _make_user(db_session)
    seminar_a = await _make_seminar(db_session)
    seminar_b = await _make_seminar(db_session)
    form = ApplicationForm(student_id=student.id)
    db_session.add(form)
    await db_session.flush()

    db_session.add(
        ApplicationChoice(
            application_form_id=form.id,
            seminar_id=seminar_a.id,
            priority=1,
            reason="第1志望の理由",
        )
    )
    await db_session.flush()

    db_session.add(
        ApplicationChoice(
            application_form_id=form.id,
            seminar_id=seminar_b.id,
            priority=1,
            reason="重複した第1志望",
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
