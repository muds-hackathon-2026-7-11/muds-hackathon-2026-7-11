import uuid

import pytest

from api.models import AnswerSource, Question, Seminar, User, UserRole
from api.services import record_answer

pytestmark = pytest.mark.asyncio


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _make_seminar(db_session) -> Seminar:
    seminar = Seminar(name=_unique("seminar"))
    db_session.add(seminar)
    await db_session.flush()
    return seminar


async def _make_user(db_session, role: UserRole = UserRole.student) -> User:
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name=_unique("name"),
        role=role,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_list_seminars(client, db_session) -> None:
    seminar = await _make_seminar(db_session)

    resp = await client.get("/seminars")

    assert resp.status_code == 200
    names = [s["name"] for s in resp.json()]
    assert seminar.name in names


async def test_create_question_success(client, db_session) -> None:
    slack_user_id = _unique("U")
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name="Test User",
        role=UserRole.student,
        slack_user_id=slack_user_id,
    )
    db_session.add(user)
    seminar = await _make_seminar(db_session)
    await db_session.flush()

    resp = await client.post(
        "/questions",
        json={
            "seminar_id": str(seminar.id),
            "slack_user_id": slack_user_id,
            "content": "プログラミング未経験でも大丈夫ですか？",
        },
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["seminar_id"] == str(seminar.id)
    assert body["content"] == "プログラミング未経験でも大丈夫ですか？"
    assert "user_id" not in body  # 匿名化: APIレスポンスにuser_idを含めない


async def test_create_question_unknown_slack_user_returns_404(
    client, db_session
) -> None:
    seminar = await _make_seminar(db_session)
    await db_session.flush()

    resp = await client.post(
        "/questions",
        json={
            "seminar_id": str(seminar.id),
            "slack_user_id": _unique("U-unknown"),
            "content": "質問です",
        },
    )

    assert resp.status_code == 404


async def test_create_question_unknown_seminar_returns_404(client, db_session) -> None:
    slack_user_id = _unique("U")
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name="Test User",
        role=UserRole.student,
        slack_user_id=slack_user_id,
    )
    db_session.add(user)
    await db_session.flush()

    resp = await client.post(
        "/questions",
        json={
            "seminar_id": str(uuid.uuid4()),
            "slack_user_id": slack_user_id,
            "content": "質問です",
        },
    )

    assert resp.status_code == 404


async def test_create_question_empty_content_is_rejected(client, db_session) -> None:
    slack_user_id = _unique("U")
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name="Test User",
        role=UserRole.student,
        slack_user_id=slack_user_id,
    )
    db_session.add(user)
    seminar = await _make_seminar(db_session)
    await db_session.flush()

    resp = await client.post(
        "/questions",
        json={
            "seminar_id": str(seminar.id),
            "slack_user_id": slack_user_id,
            "content": "",
        },
    )

    assert resp.status_code == 422


async def test_list_questions_returns_answered_and_unanswered(
    client, db_session
) -> None:
    seminar = await _make_seminar(db_session)
    asker = await _make_user(db_session, UserRole.student)
    teacher = await _make_user(db_session, UserRole.teacher)

    answered_question = Question(
        seminar_id=seminar.id, user_id=asker.id, content="質問A"
    )
    unanswered_question = Question(
        seminar_id=seminar.id, user_id=asker.id, content="質問B"
    )
    db_session.add_all([answered_question, unanswered_question])
    await db_session.flush()

    await record_answer(
        db_session,
        question=answered_question,
        user_id=teacher.id,
        content="回答です",
        source=AnswerSource.web,
    )
    await db_session.flush()

    resp = await client.get(f"/questions?seminar_id={seminar.id}")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2

    answered_body = next(q for q in body if q["content"] == "質問A")
    assert answered_body["status"] == "answered"
    assert len(answered_body["answers"]) == 1
    assert answered_body["answers"][0]["content"] == "回答です"
    assert answered_body["answers"][0]["answerer_name"] == teacher.name

    unanswered_body = next(q for q in body if q["content"] == "質問B")
    assert unanswered_body["status"] == "waiting"
    assert unanswered_body["answers"] == []


async def test_list_questions_groups_multiple_answers_under_one_question(
    client, db_session
) -> None:
    seminar = await _make_seminar(db_session)
    asker = await _make_user(db_session, UserRole.student)
    teacher1 = await _make_user(db_session, UserRole.teacher)
    teacher2 = await _make_user(db_session, UserRole.student)

    question = Question(seminar_id=seminar.id, user_id=asker.id, content="質問")
    db_session.add(question)
    await db_session.flush()

    await record_answer(
        db_session,
        question=question,
        user_id=teacher1.id,
        content="回答1",
        source=AnswerSource.web,
    )
    await record_answer(
        db_session,
        question=question,
        user_id=teacher2.id,
        content="回答2",
        source=AnswerSource.web,
    )
    await db_session.flush()

    resp = await client.get(f"/questions?seminar_id={seminar.id}")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    answers = body[0]["answers"]
    assert len(answers) == 2
    assert {a["content"] for a in answers} == {"回答1", "回答2"}
    assert {a["answerer_name"] for a in answers} == {teacher1.name, teacher2.name}


async def test_list_questions_does_not_leak_asker_identity(client, db_session) -> None:
    seminar = await _make_seminar(db_session)
    asker = await _make_user(db_session, UserRole.student)
    db_session.add(Question(seminar_id=seminar.id, user_id=asker.id, content="質問"))
    await db_session.flush()

    resp = await client.get(f"/questions?seminar_id={seminar.id}")

    assert resp.status_code == 200
    assert "user_id" not in resp.json()[0]


async def test_list_questions_unknown_seminar_returns_404(client) -> None:
    resp = await client.get(f"/questions?seminar_id={uuid.uuid4()}")

    assert resp.status_code == 404


async def test_list_questions_missing_seminar_id_returns_422(client) -> None:
    resp = await client.get("/questions")

    assert resp.status_code == 422
