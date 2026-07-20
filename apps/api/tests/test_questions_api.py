import uuid
from datetime import date, timedelta

import pytest

from api import auth
from api.auth import get_current_user
from api.main import app
from api.models import (
    AnswerSource,
    Question,
    RecruitmentTerm,
    RecruitmentTermStatus,
    Seminar,
    SeminarMember,
    User,
    UserRole,
)
from api.services import record_answer

pytestmark = pytest.mark.asyncio

_SECRET = "test-internal-secret"


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _authenticate_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


async def _make_seminar(db_session) -> Seminar:
    seminar = Seminar(name=_unique("seminar"))
    db_session.add(seminar)
    await db_session.flush()
    return seminar


async def _make_open_term(db_session) -> RecruitmentTerm:
    today = date.today()
    term = RecruitmentTerm(
        academic_year=3000 + int(uuid.uuid4().int % 1000),
        starts_at=today - timedelta(days=1),
        ends_at=today + timedelta(days=30),
        status=RecruitmentTermStatus.open,
    )
    db_session.add(term)
    await db_session.flush()
    return term


async def _make_user(
    db_session,
    role: UserRole = UserRole.student,
    *,
    slack_user_id: str | None = None,
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


async def test_list_seminars(client, db_session) -> None:
    # 教員は学年別募集(#99/#103)の絞り込みを受けないため認証はteacherにする。
    _authenticate_as(await _make_user(db_session, UserRole.teacher))
    seminar = await _make_seminar(db_session)

    resp = await client.get("/seminars")

    assert resp.status_code == 200
    names = [s["name"] for s in resp.json()]
    assert seminar.name in names


async def test_create_question_success(client, db_session, monkeypatch) -> None:
    monkeypatch.setattr(auth.settings, "internal_api_secret", _SECRET)
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
        headers={"X-Internal-Secret": _SECRET},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["seminar_id"] == str(seminar.id)
    assert body["content"] == "プログラミング未経験でも大丈夫ですか？"
    assert "user_id" not in body  # 匿名化: APIレスポンスにuser_idを含めない


async def test_create_question_rejects_missing_secret(client, db_session) -> None:
    seminar = await _make_seminar(db_session)
    await db_session.flush()

    resp = await client.post(
        "/questions",
        json={
            "seminar_id": str(seminar.id),
            "slack_user_id": _unique("U"),
            "content": "質問です",
        },
    )

    assert resp.status_code == 403


async def test_create_question_unknown_slack_user_returns_404(
    client, db_session, monkeypatch
) -> None:
    monkeypatch.setattr(auth.settings, "internal_api_secret", _SECRET)
    seminar = await _make_seminar(db_session)
    await db_session.flush()

    resp = await client.post(
        "/questions",
        json={
            "seminar_id": str(seminar.id),
            "slack_user_id": _unique("U-unknown"),
            "content": "質問です",
        },
        headers={"X-Internal-Secret": _SECRET},
    )

    assert resp.status_code == 404


async def test_create_question_unknown_seminar_returns_404(
    client, db_session, monkeypatch
) -> None:
    monkeypatch.setattr(auth.settings, "internal_api_secret", _SECRET)
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
        headers={"X-Internal-Secret": _SECRET},
    )

    assert resp.status_code == 404


async def test_create_question_empty_content_is_rejected(
    client, db_session, monkeypatch
) -> None:
    monkeypatch.setattr(auth.settings, "internal_api_secret", _SECRET)
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
        headers={"X-Internal-Secret": _SECRET},
    )

    assert resp.status_code == 422


async def test_create_question_web_success(
    client, db_session, fake_slack_client
) -> None:
    student = await _make_user(db_session, UserRole.student)
    seminar = await _make_seminar(db_session)
    _authenticate_as(student)

    resp = await client.post(
        "/questions/me",
        json={
            "seminar_id": str(seminar.id),
            "content": "プログラミング未経験でも大丈夫ですか？",
        },
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["seminar_id"] == str(seminar.id)
    assert body["content"] == "プログラミング未経験でも大丈夫ですか？"
    assert "user_id" not in body

    created = await db_session.get(Question, uuid.UUID(body["id"]))
    assert created is not None
    assert created.user_id == student.id

    # 回答候補者がいない(在籍ゼミ生・教員なし)ため、通知は0件。
    assert fake_slack_client.sent == []


async def test_create_question_web_notifies_answer_candidates(
    client, db_session, fake_slack_client
) -> None:
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    asker = await _make_user(db_session, UserRole.student)
    member = await _make_user(
        db_session, UserRole.student, slack_user_id=_unique("U-member")
    )
    db_session.add(
        SeminarMember(seminar_id=seminar.id, student_id=member.id, term_id=term.id)
    )
    await db_session.flush()
    _authenticate_as(asker)

    resp = await client.post(
        "/questions/me",
        json={"seminar_id": str(seminar.id), "content": "質問です"},
    )

    assert resp.status_code == 201
    notified_slack_ids = {sent.slack_user_id for sent in fake_slack_client.sent}
    assert notified_slack_ids == {member.slack_user_id}


async def test_create_question_web_unknown_seminar_returns_404(
    client, db_session
) -> None:
    _authenticate_as(await _make_user(db_session, UserRole.student))

    resp = await client.post(
        "/questions/me",
        json={"seminar_id": str(uuid.uuid4()), "content": "質問です"},
    )

    assert resp.status_code == 404


async def test_create_question_web_empty_content_is_rejected(
    client, db_session
) -> None:
    seminar = await _make_seminar(db_session)
    _authenticate_as(await _make_user(db_session, UserRole.student))

    resp = await client.post(
        "/questions/me",
        json={"seminar_id": str(seminar.id), "content": ""},
    )

    assert resp.status_code == 422


async def test_create_question_web_requires_authentication(client, monkeypatch) -> None:
    from api import auth

    monkeypatch.setattr(auth.settings, "auth_dev_mode", False)

    resp = await client.post(
        "/questions/me",
        json={"seminar_id": str(uuid.uuid4()), "content": "質問です"},
    )

    assert resp.status_code == 401


async def test_create_question_web_rejects_teacher(client, db_session) -> None:
    seminar = await _make_seminar(db_session)
    _authenticate_as(await _make_user(db_session, UserRole.teacher))

    resp = await client.post(
        "/questions/me",
        json={"seminar_id": str(seminar.id), "content": "質問です"},
    )

    assert resp.status_code == 403


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


async def test_get_question_returns_answers_with_answerer_names(
    client, db_session
) -> None:
    seminar = await _make_seminar(db_session)
    asker = await _make_user(db_session, UserRole.student)
    teacher = await _make_user(db_session, UserRole.teacher)

    question = Question(seminar_id=seminar.id, user_id=asker.id, content="質問")
    db_session.add(question)
    await db_session.flush()

    await record_answer(
        db_session,
        question=question,
        user_id=teacher.id,
        content="回答です",
        source=AnswerSource.web,
    )
    await db_session.flush()

    resp = await client.get(f"/questions/{question.id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["content"] == "質問"
    assert "user_id" not in body
    assert len(body["answers"]) == 1
    assert body["answers"][0]["answerer_name"] == teacher.name


async def test_get_question_unknown_id_returns_404(client) -> None:
    resp = await client.get(f"/questions/{uuid.uuid4()}")

    assert resp.status_code == 404
