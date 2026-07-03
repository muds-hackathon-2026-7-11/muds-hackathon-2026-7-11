import uuid
from datetime import date

import pytest
from sqlalchemy import select

from api.models import (
    AnswerRequest,
    RecruitmentTerm,
    RecruitmentTermStatus,
    Seminar,
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


async def _post_question(
    client, *, seminar_id, slack_user_id: str, content: str
) -> str:
    resp = await client.post(
        "/questions",
        json={
            "seminar_id": str(seminar_id),
            "slack_user_id": slack_user_id,
            "content": content,
        },
    )
    question_id: str = resp.json()["id"]
    return question_id


async def test_create_answer_success(client, db_session, fake_slack_client) -> None:
    await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)

    asker_slack_id = _unique("U-asker")
    await _make_user(db_session, UserRole.student, asker_slack_id)

    answerer_slack_id = _unique("U-answerer")
    answerer = await _make_user(db_session, UserRole.teacher, answerer_slack_id)
    db_session.add(SeminarTeacher(seminar_id=seminar.id, teacher_id=answerer.id))
    await db_session.flush()

    question_id = await _post_question(
        client, seminar_id=seminar.id, slack_user_id=asker_slack_id, content="質問です"
    )

    resp = await client.post(
        "/answers",
        json={
            "question_id": question_id,
            "slack_user_id": answerer_slack_id,
            "content": "回答です",
        },
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["content"] == "回答です"
    assert body["answerer_name"] == answerer.name

    question_get = await client.get(f"/questions?seminar_id={seminar.id}")
    assert question_get.json()[0]["status"] == "answered"


async def test_create_answer_notifies_asker(
    client, db_session, fake_slack_client
) -> None:
    await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)

    asker_slack_id = _unique("U-asker")
    await _make_user(db_session, UserRole.student, asker_slack_id)

    answerer_slack_id = _unique("U-answerer")
    answerer = await _make_user(db_session, UserRole.teacher, answerer_slack_id)
    db_session.add(SeminarTeacher(seminar_id=seminar.id, teacher_id=answerer.id))
    await db_session.flush()

    question_id = await _post_question(
        client, seminar_id=seminar.id, slack_user_id=asker_slack_id, content="質問です"
    )
    fake_slack_client.sent.clear()

    resp = await client.post(
        "/answers",
        json={
            "question_id": question_id,
            "slack_user_id": answerer_slack_id,
            "content": "回答です",
        },
    )

    assert resp.status_code == 201
    notified_ids = {sent.slack_user_id for sent in fake_slack_client.sent}
    assert asker_slack_id in notified_ids


async def test_create_answer_uses_slack_display_name_in_notifications(
    client, db_session, fake_slack_client
) -> None:
    await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)

    asker_slack_id = _unique("U-asker")
    await _make_user(db_session, UserRole.student, asker_slack_id)

    answerer_slack_id = _unique("U-answerer")
    answerer = await _make_user(db_session, UserRole.teacher, answerer_slack_id)
    db_session.add(SeminarTeacher(seminar_id=seminar.id, teacher_id=answerer.id))
    await db_session.flush()
    fake_slack_client.display_names[answerer_slack_id] = "[B3] 山田太郎"

    question_id = await _post_question(
        client, seminar_id=seminar.id, slack_user_id=asker_slack_id, content="質問です"
    )
    fake_slack_client.sent.clear()

    resp = await client.post(
        "/answers",
        json={
            "question_id": question_id,
            "slack_user_id": answerer_slack_id,
            "content": "回答です",
        },
    )

    assert resp.status_code == 201
    asker_message = next(
        sent for sent in fake_slack_client.sent if sent.slack_user_id == asker_slack_id
    )
    assert "[B3] 山田太郎" in asker_message.text
    assert answerer.name not in asker_message.text


async def test_create_answer_updates_other_pending_candidates(
    client, db_session, fake_slack_client
) -> None:
    await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)

    asker_slack_id = _unique("U-asker")
    await _make_user(db_session, UserRole.student, asker_slack_id)

    teacher1_slack_id = _unique("U-teacher1")
    teacher1 = await _make_user(db_session, UserRole.teacher, teacher1_slack_id)
    db_session.add(SeminarTeacher(seminar_id=seminar.id, teacher_id=teacher1.id))

    teacher2_slack_id = _unique("U-teacher2")
    teacher2 = await _make_user(db_session, UserRole.teacher, teacher2_slack_id)
    db_session.add(SeminarTeacher(seminar_id=seminar.id, teacher_id=teacher2.id))
    await db_session.flush()

    question_id = await _post_question(
        client, seminar_id=seminar.id, slack_user_id=asker_slack_id, content="質問です"
    )

    resp = await client.post(
        "/answers",
        json={
            "question_id": question_id,
            "slack_user_id": teacher1_slack_id,
            "content": "回答です",
        },
    )
    assert resp.status_code == 201

    requests_result = await db_session.execute(
        select(AnswerRequest).where(AnswerRequest.question_id == question_id)
    )
    requests_by_user = {r.user_id: r for r in requests_result.scalars().all()}
    assert requests_by_user[teacher1.id].status == "answered"
    assert requests_by_user[teacher2.id].status == "skipped"

    updated_channel_ids = {u.channel_id for u in fake_slack_client.updated}
    assert requests_by_user[teacher2.id].slack_dm_channel_id in updated_channel_ids


async def test_create_answer_unknown_slack_user_returns_404(client, db_session) -> None:
    await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    asker_slack_id = _unique("U-asker")
    await _make_user(db_session, UserRole.student, asker_slack_id)

    question_id = await _post_question(
        client, seminar_id=seminar.id, slack_user_id=asker_slack_id, content="質問です"
    )

    resp = await client.post(
        "/answers",
        json={
            "question_id": question_id,
            "slack_user_id": _unique("U-unknown"),
            "content": "回答です",
        },
    )

    assert resp.status_code == 404


async def test_create_answer_unknown_question_returns_404(client, db_session) -> None:
    slack_user_id = _unique("U")
    await _make_user(db_session, UserRole.teacher, slack_user_id)

    resp = await client.post(
        "/answers",
        json={
            "question_id": str(uuid.uuid4()),
            "slack_user_id": slack_user_id,
            "content": "回答です",
        },
    )

    assert resp.status_code == 404


async def test_create_answer_empty_content_is_rejected(client, db_session) -> None:
    seminar = await _make_seminar(db_session)
    asker_slack_id = _unique("U-asker")
    await _make_user(db_session, UserRole.student, asker_slack_id)
    answerer_slack_id = _unique("U-answerer")
    await _make_user(db_session, UserRole.teacher, answerer_slack_id)

    question_id = await _post_question(
        client, seminar_id=seminar.id, slack_user_id=asker_slack_id, content="質問です"
    )

    resp = await client.post(
        "/answers",
        json={
            "question_id": question_id,
            "slack_user_id": answerer_slack_id,
            "content": "",
        },
    )

    assert resp.status_code == 422
