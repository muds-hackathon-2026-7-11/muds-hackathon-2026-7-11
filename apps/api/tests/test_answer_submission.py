import uuid
from datetime import date

import pytest
from sqlalchemy import select

from api import auth
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

_SECRET = "test-internal-secret"


@pytest.fixture(autouse=True)
def _set_internal_secret(monkeypatch):
    monkeypatch.setattr(auth.settings, "internal_api_secret", _SECRET)


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
        headers={"X-Internal-Secret": _SECRET},
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
        headers={"X-Internal-Secret": _SECRET},
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
        headers={"X-Internal-Secret": _SECRET},
    )

    assert resp.status_code == 201
    notified_ids = {sent.slack_user_id for sent in fake_slack_client.sent}
    assert asker_slack_id in notified_ids


async def test_asker_gets_a_new_dm_for_each_answer_not_a_thread_reply(
    client, db_session, fake_slack_client
) -> None:
    """質問者への通知はスレッド化せず、回答のたびに独立した新規DMにする。"""
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
    fake_slack_client.sent.clear()

    first_resp = await client.post(
        "/answers",
        json={
            "question_id": question_id,
            "slack_user_id": teacher1_slack_id,
            "content": "最初の回答です",
        },
        headers={"X-Internal-Secret": _SECRET},
    )
    assert first_resp.status_code == 201
    assert len(fake_slack_client.sent) == 1
    assert fake_slack_client.sent[0].slack_user_id == asker_slack_id

    second_resp = await client.post(
        "/answers",
        json={
            "question_id": question_id,
            "slack_user_id": teacher2_slack_id,
            "content": "2件目の回答です",
        },
        headers={"X-Internal-Secret": _SECRET},
    )
    assert second_resp.status_code == 201
    # 質問者へは毎回新規DMを送る(スレッド返信にはしない)
    asker_messages = [
        s for s in fake_slack_client.sent if s.slack_user_id == asker_slack_id
    ]
    assert len(asker_messages) == 2
    assert "2件目の回答です" in asker_messages[1].text


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
        headers={"X-Internal-Secret": _SECRET},
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
        headers={"X-Internal-Secret": _SECRET},
    )
    assert resp.status_code == 201

    requests_result = await db_session.execute(
        select(AnswerRequest).where(AnswerRequest.question_id == question_id)
    )
    requests_by_user = {r.user_id: r for r in requests_result.scalars().all()}
    assert requests_by_user[teacher1.id].status == "answered"
    assert requests_by_user[teacher2.id].status == "skipped"

    replied_channel_ids = {r.channel_id for r in fake_slack_client.replies}
    assert requests_by_user[teacher2.id].slack_dm_channel_id in replied_channel_ids


async def test_create_answer_replies_in_thread_and_allows_additional_answers(
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
            "content": "最初の回答です",
        },
        headers={"X-Internal-Secret": _SECRET},
    )
    assert resp.status_code == 201

    requests_result = await db_session.execute(
        select(AnswerRequest).where(AnswerRequest.question_id == question_id)
    )
    teacher2_request = next(
        r for r in requests_result.scalars().all() if r.user_id == teacher2.id
    )
    reply = next(
        r
        for r in fake_slack_client.replies
        if r.channel_id == teacher2_request.slack_dm_channel_id
    )
    assert "最初の回答です" in reply.text

    # 元のメッセージは上書きされない(スレッド返信のみ)ので、
    # 別の候補者(teacher2)は引き続き「回答する」ボタンを押せる = 追加回答できること
    other_answer_resp = await client.post(
        "/answers",
        json={
            "question_id": question_id,
            "slack_user_id": teacher2_slack_id,
            "content": "追加の回答です",
        },
        headers={"X-Internal-Secret": _SECRET},
    )
    assert other_answer_resp.status_code == 201

    question_get = await client.get(f"/questions?seminar_id={seminar.id}")
    answers = question_get.json()[0]["answers"]
    assert {a["content"] for a in answers} == {"最初の回答です", "追加の回答です"}


async def test_earlier_answerer_still_gets_notified_of_later_answers(
    client, db_session, fake_slack_client
) -> None:
    """一度回答した人(status=answered)も、他の人の後続の回答について
    引き続き通知を受け取れること(既に回答済みだからと通知が止まらない)。
    """
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

    first_resp = await client.post(
        "/answers",
        json={
            "question_id": question_id,
            "slack_user_id": teacher1_slack_id,
            "content": "1件目の回答です",
        },
        headers={"X-Internal-Secret": _SECRET},
    )
    assert first_resp.status_code == 201

    requests_result = await db_session.execute(
        select(AnswerRequest).where(AnswerRequest.question_id == question_id)
    )
    teacher1_request = next(
        r for r in requests_result.scalars().all() if r.user_id == teacher1.id
    )
    assert teacher1_request.status == "answered"

    second_resp = await client.post(
        "/answers",
        json={
            "question_id": question_id,
            "slack_user_id": teacher2_slack_id,
            "content": "2件目の回答です",
        },
        headers={"X-Internal-Secret": _SECRET},
    )
    assert second_resp.status_code == 201

    # teacher1はすでにanswered状態だが、teacher2の回答についても
    # スレッド返信で通知が届くこと
    reply_to_teacher1 = next(
        r
        for r in fake_slack_client.replies
        if r.channel_id == teacher1_request.slack_dm_channel_id
    )
    assert "2件目の回答です" in reply_to_teacher1.text


async def test_create_answer_rejects_missing_secret(client, db_session) -> None:
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
            "slack_user_id": _unique("U-answerer"),
            "content": "回答です",
        },
    )

    assert resp.status_code == 403


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
        headers={"X-Internal-Secret": _SECRET},
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
        headers={"X-Internal-Secret": _SECRET},
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
        headers={"X-Internal-Secret": _SECRET},
    )

    assert resp.status_code == 422
