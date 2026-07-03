import uuid
from datetime import date

import pytest
from sqlalchemy import select

from api.models import (
    AnswerRequest,
    RecruitmentTerm,
    RecruitmentTermStatus,
    Seminar,
    SeminarMember,
    SeminarTeacher,
    User,
    UserRole,
)
from api.slack_client import SentDM

pytestmark = pytest.mark.asyncio


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _make_seminar(db_session) -> Seminar:
    seminar = Seminar(name=_unique("seminar"))
    db_session.add(seminar)
    await db_session.flush()
    return seminar


async def _make_open_term(db_session) -> RecruitmentTerm:
    today = date.today()
    term = RecruitmentTerm(
        academic_year=3000 + int(uuid.uuid4().int % 1000),
        starts_at=today,
        ends_at=today,
        status=RecruitmentTermStatus.open,
    )
    db_session.add(term)
    await db_session.flush()
    return term


async def _make_user(
    db_session, role: UserRole = UserRole.student, slack_user_id: str | None = None
) -> User:
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name=_unique("name"),
        role=role,
        slack_user_id=slack_user_id,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _post_question(client, *, seminar_id, slack_user_id: str, content: str):
    return await client.post(
        "/questions",
        json={
            "seminar_id": str(seminar_id),
            "slack_user_id": slack_user_id,
            "content": content,
        },
    )


async def test_notifies_current_members_and_teachers(
    client, db_session, fake_slack_client
) -> None:
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)

    asker_slack_id = _unique("U-asker")
    await _make_user(db_session, UserRole.student, asker_slack_id)

    member = await _make_user(db_session, UserRole.student, _unique("U-member"))
    db_session.add(
        SeminarMember(
            seminar_id=seminar.id,
            student_id=member.id,
            academic_year=term.academic_year,
        )
    )
    teacher = await _make_user(db_session, UserRole.teacher, _unique("U-teacher"))
    db_session.add(SeminarTeacher(seminar_id=seminar.id, teacher_id=teacher.id))
    await db_session.flush()

    resp = await _post_question(
        client, seminar_id=seminar.id, slack_user_id=asker_slack_id, content="質問です"
    )

    assert resp.status_code == 201
    notified_slack_ids = {sent.slack_user_id for sent in fake_slack_client.sent}
    assert notified_slack_ids == {member.slack_user_id, teacher.slack_user_id}

    question_id = resp.json()["id"]
    requests_result = await db_session.execute(
        select(AnswerRequest).where(AnswerRequest.question_id == question_id)
    )
    requests = requests_result.scalars().all()
    assert {r.user_id for r in requests} == {member.id, teacher.id}
    assert all(r.status == "pending" for r in requests)


async def test_does_not_notify_users_without_slack_link(
    client, db_session, fake_slack_client
) -> None:
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)

    asker_slack_id = _unique("U-asker")
    await _make_user(db_session, UserRole.student, asker_slack_id)

    unlinked_member = await _make_user(db_session, UserRole.student, slack_user_id=None)
    db_session.add(
        SeminarMember(
            seminar_id=seminar.id,
            student_id=unlinked_member.id,
            academic_year=term.academic_year,
        )
    )
    await db_session.flush()

    resp = await _post_question(
        client, seminar_id=seminar.id, slack_user_id=asker_slack_id, content="質問です"
    )

    assert resp.status_code == 201
    assert fake_slack_client.sent == []


async def test_does_not_notify_the_asker_even_if_current_member(
    client, db_session, fake_slack_client
) -> None:
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)

    asker_slack_id = _unique("U-asker")
    asker = await _make_user(db_session, UserRole.student, asker_slack_id)
    db_session.add(
        SeminarMember(
            seminar_id=seminar.id,
            student_id=asker.id,
            academic_year=term.academic_year,
        )
    )
    await db_session.flush()

    resp = await _post_question(
        client, seminar_id=seminar.id, slack_user_id=asker_slack_id, content="質問です"
    )

    assert resp.status_code == 201
    assert fake_slack_client.sent == []


async def test_does_not_notify_past_members(
    client, db_session, fake_slack_client
) -> None:
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)

    asker_slack_id = _unique("U-asker")
    await _make_user(db_session, UserRole.student, asker_slack_id)

    past_member = await _make_user(db_session, UserRole.student, _unique("U-past"))
    db_session.add(
        SeminarMember(
            seminar_id=seminar.id,
            student_id=past_member.id,
            academic_year=term.academic_year - 1,
        )
    )
    await db_session.flush()

    resp = await _post_question(
        client, seminar_id=seminar.id, slack_user_id=asker_slack_id, content="質問です"
    )

    assert resp.status_code == 201
    assert fake_slack_client.sent == []


async def test_notification_failure_does_not_block_question_creation(
    client, db_session, fake_slack_client, monkeypatch
) -> None:
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)

    asker_slack_id = _unique("U-asker")
    await _make_user(db_session, UserRole.student, asker_slack_id)

    member = await _make_user(db_session, UserRole.student, _unique("U-member"))
    db_session.add(
        SeminarMember(
            seminar_id=seminar.id,
            student_id=member.id,
            academic_year=term.academic_year,
        )
    )
    await db_session.flush()

    async def _boom(*, slack_user_id: str, text: str) -> SentDM:
        raise RuntimeError("Slack API is down")

    monkeypatch.setattr(fake_slack_client, "send_dm", _boom)

    resp = await _post_question(
        client, seminar_id=seminar.id, slack_user_id=asker_slack_id, content="質問です"
    )

    assert resp.status_code == 201
