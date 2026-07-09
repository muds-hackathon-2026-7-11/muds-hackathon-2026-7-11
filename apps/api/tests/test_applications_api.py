import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select, update

from api import auth
from api.models import (
    ApplicationChoice,
    ApplicationForm,
    ApplicationStatus,
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


async def _make_student(
    db_session,
    *,
    is_active: bool = True,
    grade: str | None = "B1",
    slack_user_id: str | None = None,
) -> User:
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('student')}@example.com",
        name="テスト学生",
        role=UserRole.student,
        is_active=is_active,
        grade=grade,
        slack_user_id=slack_user_id,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_seminar(db_session) -> Seminar:
    seminar = Seminar(name=_unique("seminar"))
    db_session.add(seminar)
    await db_session.flush()
    return seminar


async def _make_open_term(
    db_session, *, academic_year: int | None = None
) -> RecruitmentTerm:
    today = date.today()
    term = RecruitmentTerm(
        academic_year=academic_year or (3000 + int(uuid.uuid4().int % 1000)),
        starts_at=today - timedelta(days=1),
        ends_at=today + timedelta(days=30),
        status=RecruitmentTermStatus.open,
    )
    db_session.add(term)
    await db_session.flush()
    return term


async def _make_closed_term(
    db_session, *, starts_at: date, academic_year: int | None = None
) -> RecruitmentTerm:
    term = RecruitmentTerm(
        academic_year=academic_year or (3000 + int(uuid.uuid4().int % 1000)),
        starts_at=starts_at,
        ends_at=starts_at + timedelta(days=30),
        status=RecruitmentTermStatus.closed,
    )
    db_session.add(term)
    await db_session.flush()
    return term


async def _close_all_open_terms(db_session) -> None:
    """「現在アクティブな募集期間が無い」ことを前提にするテスト用。

    db_sessionは共有の開発用DBに接続しており(tests/conftest.py参照)、
    実データの募集期間が存在すると get_current_term() がそれを「現在の
    募集期間」として返してしまい、テストの前提が崩れる。db_sessionは
    テスト終了時にrollbackされ実データへは反映されないため、既存の
    open な募集期間を一時的にclosedへ変更しても安全。
    """
    await db_session.execute(
        update(RecruitmentTerm)
        .where(RecruitmentTerm.status == RecruitmentTermStatus.open)
        .values(status=RecruitmentTermStatus.closed)
    )
    await db_session.flush()


async def _make_recruitment(
    db_session,
    *,
    term: RecruitmentTerm,
    seminar: Seminar,
    target_grades: list[str] | None = None,
) -> SeminarRecruitment:
    recruitment = SeminarRecruitment(
        term_id=term.id,
        seminar_id=seminar.id,
        capacity=10,
        target_grades=(
            target_grades if target_grades is not None else ["B1", "B2", "B3", "B4"]
        ),
    )
    db_session.add(recruitment)
    await db_session.flush()
    return recruitment


def _auth_headers(email: str) -> dict[str, str]:
    return {"X-Dev-User-Email": email, "X-Dev-User-Role": "student"}


@pytest.fixture(autouse=True)
def _enable_dev_auth(monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_dev_mode", True)


# --- GET /applications/me ---


async def test_get_returns_empty_draft_when_no_term_and_no_history(
    client, db_session
) -> None:
    await _close_all_open_terms(db_session)
    student = await _make_student(db_session)

    resp = await client.get("/applications/me", headers=_auth_headers(student.email))

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] is None
    assert body["status"] == "draft"
    assert body["choices"] == []
    assert body["is_editable"] is False


async def test_get_returns_empty_editable_draft_when_no_form_yet(
    client, db_session
) -> None:
    student = await _make_student(db_session)
    await _make_open_term(db_session)

    resp = await client.get("/applications/me", headers=_auth_headers(student.email))

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] is None
    assert body["is_editable"] is True


async def test_get_returns_existing_form_and_choices(client, db_session) -> None:
    student = await _make_student(db_session)
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(db_session, term=term, seminar=seminar)

    form = ApplicationForm(term_id=term.id, student_id=student.id)
    db_session.add(form)
    await db_session.flush()
    db_session.add(
        ApplicationChoice(
            application_form_id=form.id,
            seminar_id=seminar.id,
            priority=1,
            reason="第1志望の理由",
        )
    )
    await db_session.flush()

    resp = await client.get("/applications/me", headers=_auth_headers(student.email))

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(form.id)
    assert body["status"] == "draft"
    assert body["is_editable"] is True
    assert len(body["choices"]) == 1
    assert body["choices"][0]["seminar_id"] == str(seminar.id)
    assert body["choices"][0]["reason"] == "第1志望の理由"


async def test_get_shows_past_submission_read_only_when_no_active_term(
    client, db_session
) -> None:
    await _close_all_open_terms(db_session)
    student = await _make_student(db_session)
    seminar = await _make_seminar(db_session)
    past_term = await _make_closed_term(
        db_session, starts_at=date.today() - timedelta(days=400)
    )
    await _make_recruitment(db_session, term=past_term, seminar=seminar)

    form = ApplicationForm(
        term_id=past_term.id,
        student_id=student.id,
        status=ApplicationStatus.submitted,
    )
    db_session.add(form)
    await db_session.flush()
    db_session.add(
        ApplicationChoice(
            application_form_id=form.id,
            seminar_id=seminar.id,
            priority=1,
            reason="前回の志望理由",
        )
    )
    await db_session.flush()

    resp = await client.get("/applications/me", headers=_auth_headers(student.email))

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(form.id)
    assert body["is_editable"] is False
    assert body["choices"][0]["reason"] == "前回の志望理由"


async def test_get_shows_form_from_the_most_recent_term(client, db_session) -> None:
    await _close_all_open_terms(db_session)
    student = await _make_student(db_session)
    seminar = await _make_seminar(db_session)

    older_term = await _make_closed_term(
        db_session, starts_at=date.today() - timedelta(days=800)
    )
    newer_term = await _make_closed_term(
        db_session, starts_at=date.today() - timedelta(days=400)
    )
    await _make_recruitment(db_session, term=older_term, seminar=seminar)
    await _make_recruitment(db_session, term=newer_term, seminar=seminar)

    older_form = ApplicationForm(term_id=older_term.id, student_id=student.id)
    newer_form = ApplicationForm(term_id=newer_term.id, student_id=student.id)
    db_session.add_all([older_form, newer_form])
    await db_session.flush()
    db_session.add_all(
        [
            ApplicationChoice(
                application_form_id=older_form.id,
                seminar_id=seminar.id,
                priority=1,
                reason="古い方",
            ),
            ApplicationChoice(
                application_form_id=newer_form.id,
                seminar_id=seminar.id,
                priority=1,
                reason="新しい方",
            ),
        ]
    )
    await db_session.flush()

    resp = await client.get("/applications/me", headers=_auth_headers(student.email))

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(newer_form.id)
    assert body["choices"][0]["reason"] == "新しい方"


async def test_get_rejects_non_student(client, db_session) -> None:
    teacher = User(
        google_id=_unique("google"),
        email=f"{_unique('teacher')}@example.com",
        name="テスト教員",
        role=UserRole.teacher,
    )
    db_session.add(teacher)
    await db_session.flush()

    resp = await client.get(
        "/applications/me",
        headers={"X-Dev-User-Email": teacher.email, "X-Dev-User-Role": "teacher"},
    )

    assert resp.status_code == 403


async def test_get_rejects_inactive_student(client, db_session) -> None:
    student = await _make_student(db_session, is_active=False)

    resp = await client.get("/applications/me", headers=_auth_headers(student.email))

    assert resp.status_code == 403


async def test_get_allows_admin_who_is_also_a_student(client, db_session) -> None:
    # role=adminでも実際には在学中の学生であるユーザーがいるため、
    # self-serviceな/me系エンドポイントはadminも許可する。
    await _close_all_open_terms(db_session)
    admin = User(
        google_id=_unique("google"),
        email=f"{_unique('admin')}@example.com",
        name="テスト管理者",
        role=UserRole.admin,
        grade="B3",
    )
    db_session.add(admin)
    await db_session.flush()

    resp = await client.get(
        "/applications/me",
        headers={"X-Dev-User-Email": admin.email, "X-Dev-User-Role": "admin"},
    )

    assert resp.status_code == 200


# --- PUT /applications/me ---


async def test_put_creates_draft_with_choices(client, db_session) -> None:
    student = await _make_student(db_session)
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(db_session, term=term, seminar=seminar)

    resp = await client.put(
        "/applications/me",
        headers=_auth_headers(student.email),
        json={
            "choices": [
                {
                    "seminar_id": str(seminar.id),
                    "priority": 1,
                    "reason": "興味があるため",
                }
            ]
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "draft"
    assert len(body["choices"]) == 1


async def test_put_replaces_existing_choices(client, db_session) -> None:
    student = await _make_student(db_session)
    term = await _make_open_term(db_session)
    seminar_a = await _make_seminar(db_session)
    seminar_b = await _make_seminar(db_session)
    await _make_recruitment(db_session, term=term, seminar=seminar_a)
    await _make_recruitment(db_session, term=term, seminar=seminar_b)

    await client.put(
        "/applications/me",
        headers=_auth_headers(student.email),
        json={
            "choices": [{"seminar_id": str(seminar_a.id), "priority": 1, "reason": "A"}]
        },
    )
    resp = await client.put(
        "/applications/me",
        headers=_auth_headers(student.email),
        json={
            "choices": [{"seminar_id": str(seminar_b.id), "priority": 1, "reason": "B"}]
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["choices"]) == 1
    assert body["choices"][0]["seminar_id"] == str(seminar_b.id)


async def test_put_keeps_submitted_status_and_refreshes_submitted_at(
    client, db_session
) -> None:
    # docs/requirements.md通り、提出後の上書きはsubmittedのまま
    # (取り下げ扱いにはしない)、submitted_atだけ更新される。
    student = await _make_student(db_session)
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(db_session, term=term, seminar=seminar)

    await client.put(
        "/applications/me",
        headers=_auth_headers(student.email),
        json={
            "choices": [{"seminar_id": str(seminar.id), "priority": 1, "reason": "A"}]
        },
    )
    submit_resp = await client.post(
        "/applications/me/submit", headers=_auth_headers(student.email)
    )
    first_submitted_at = submit_resp.json()["submitted_at"]

    resp = await client.put(
        "/applications/me",
        headers=_auth_headers(student.email),
        json={
            "choices": [
                {"seminar_id": str(seminar.id), "priority": 1, "reason": "改稿"}
            ]
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "submitted"
    assert body["choices"][0]["reason"] == "改稿"
    assert body["submitted_at"] is not None
    assert body["submitted_at"] != first_submitted_at


async def test_put_keeps_draft_status_as_draft(client, db_session) -> None:
    student = await _make_student(db_session)
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(db_session, term=term, seminar=seminar)

    await client.put(
        "/applications/me",
        headers=_auth_headers(student.email),
        json={
            "choices": [{"seminar_id": str(seminar.id), "priority": 1, "reason": "A"}]
        },
    )
    resp = await client.put(
        "/applications/me",
        headers=_auth_headers(student.email),
        json={
            "choices": [{"seminar_id": str(seminar.id), "priority": 1, "reason": "B"}]
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "draft"
    assert body["submitted_at"] is None


async def test_put_rejects_duplicate_priority(client, db_session) -> None:
    student = await _make_student(db_session)
    term = await _make_open_term(db_session)
    seminar_a = await _make_seminar(db_session)
    seminar_b = await _make_seminar(db_session)
    await _make_recruitment(db_session, term=term, seminar=seminar_a)
    await _make_recruitment(db_session, term=term, seminar=seminar_b)

    resp = await client.put(
        "/applications/me",
        headers=_auth_headers(student.email),
        json={
            "choices": [
                {"seminar_id": str(seminar_a.id), "priority": 1, "reason": "A"},
                {"seminar_id": str(seminar_b.id), "priority": 1, "reason": "B"},
            ]
        },
    )

    assert resp.status_code == 400


async def test_put_rejects_duplicate_seminar(client, db_session) -> None:
    student = await _make_student(db_session)
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(db_session, term=term, seminar=seminar)

    resp = await client.put(
        "/applications/me",
        headers=_auth_headers(student.email),
        json={
            "choices": [
                {"seminar_id": str(seminar.id), "priority": 1, "reason": "A"},
                {"seminar_id": str(seminar.id), "priority": 2, "reason": "B"},
            ]
        },
    )

    assert resp.status_code == 400


async def test_put_rejects_reason_over_400_chars(client, db_session) -> None:
    student = await _make_student(db_session)
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(db_session, term=term, seminar=seminar)

    resp = await client.put(
        "/applications/me",
        headers=_auth_headers(student.email),
        json={
            "choices": [
                {
                    "seminar_id": str(seminar.id),
                    "priority": 1,
                    "reason": "あ" * 401,
                }
            ]
        },
    )

    assert resp.status_code == 422


async def test_put_accepts_reason_at_400_chars(client, db_session) -> None:
    student = await _make_student(db_session)
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(db_session, term=term, seminar=seminar)

    resp = await client.put(
        "/applications/me",
        headers=_auth_headers(student.email),
        json={
            "choices": [
                {
                    "seminar_id": str(seminar.id),
                    "priority": 1,
                    "reason": "あ" * 400,
                }
            ]
        },
    )

    assert resp.status_code == 200


async def test_put_rejects_non_recruiting_seminar(client, db_session) -> None:
    student = await _make_student(db_session)
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(db_session, term=term, seminar=seminar, target_grades=[])

    resp = await client.put(
        "/applications/me",
        headers=_auth_headers(student.email),
        json={
            "choices": [{"seminar_id": str(seminar.id), "priority": 1, "reason": "A"}]
        },
    )

    assert resp.status_code == 400


async def test_put_rejects_seminar_not_targeting_students_grade(
    client, db_session
) -> None:
    student = await _make_student(db_session, grade="B2")
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(
        db_session, term=term, seminar=seminar, target_grades=["B1"]
    )

    resp = await client.put(
        "/applications/me",
        headers=_auth_headers(student.email),
        json={
            "choices": [{"seminar_id": str(seminar.id), "priority": 1, "reason": "A"}]
        },
    )

    assert resp.status_code == 400


async def test_put_accepts_seminar_targeting_students_grade_via_mids_suffix(
    client, db_session
) -> None:
    # "MIDS/B1"のような学生も、末尾のB1として学年別募集の対象に含める(#99)。
    student = await _make_student(db_session, grade="MIDS/B1")
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(
        db_session, term=term, seminar=seminar, target_grades=["B1"]
    )

    resp = await client.put(
        "/applications/me",
        headers=_auth_headers(student.email),
        json={
            "choices": [{"seminar_id": str(seminar.id), "priority": 1, "reason": "A"}]
        },
    )

    assert resp.status_code == 200


async def test_put_rejects_seminar_for_student_with_ungraded_grade(
    client, db_session
) -> None:
    # M1/M2/D1/guest/空文字はB1〜B4のどれにも一致しないため、target_gradesが
    # 全学年を含んでいても常に対象外(#99)。
    student = await _make_student(db_session, grade="M1")
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(
        db_session, term=term, seminar=seminar, target_grades=["B1", "B2", "B3", "B4"]
    )

    resp = await client.put(
        "/applications/me",
        headers=_auth_headers(student.email),
        json={
            "choices": [{"seminar_id": str(seminar.id), "priority": 1, "reason": "A"}]
        },
    )

    assert resp.status_code == 400


async def test_put_rejects_seminar_with_no_recruitment_row(client, db_session) -> None:
    student = await _make_student(db_session)
    await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)  # このtermに紐づくrecruitmentが無い

    resp = await client.put(
        "/applications/me",
        headers=_auth_headers(student.email),
        json={
            "choices": [{"seminar_id": str(seminar.id), "priority": 1, "reason": "A"}]
        },
    )

    assert resp.status_code == 400


async def test_put_rejects_more_than_three_choices(client, db_session) -> None:
    student = await _make_student(db_session)
    term = await _make_open_term(db_session)
    seminars = [await _make_seminar(db_session) for _ in range(4)]
    for seminar in seminars:
        await _make_recruitment(db_session, term=term, seminar=seminar)

    resp = await client.put(
        "/applications/me",
        headers=_auth_headers(student.email),
        json={
            "choices": [
                {"seminar_id": str(s.id), "priority": i + 1, "reason": "A"}
                for i, s in enumerate(seminars)
            ]
        },
    )

    assert resp.status_code == 422


async def test_put_requires_active_term(client, db_session) -> None:
    await _close_all_open_terms(db_session)
    student = await _make_student(db_session)

    resp = await client.put(
        "/applications/me",
        headers=_auth_headers(student.email),
        json={"choices": []},
    )

    assert resp.status_code == 400


# --- POST /applications/me/submit ---


async def test_submit_moves_draft_to_submitted(client, db_session) -> None:
    student = await _make_student(db_session)
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(db_session, term=term, seminar=seminar)
    await client.put(
        "/applications/me",
        headers=_auth_headers(student.email),
        json={
            "choices": [{"seminar_id": str(seminar.id), "priority": 1, "reason": "A"}]
        },
    )

    resp = await client.post(
        "/applications/me/submit", headers=_auth_headers(student.email)
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "submitted"
    assert body["submitted_at"] is not None


async def test_submit_sends_slack_confirmation(
    client, db_session, fake_slack_client
) -> None:
    student = await _make_student(db_session, slack_user_id=_unique("U"))
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(db_session, term=term, seminar=seminar)
    await client.put(
        "/applications/me",
        headers=_auth_headers(student.email),
        json={
            "choices": [{"seminar_id": str(seminar.id), "priority": 1, "reason": "A"}]
        },
    )

    resp = await client.post(
        "/applications/me/submit", headers=_auth_headers(student.email)
    )

    assert resp.status_code == 200
    assert len(fake_slack_client.sent) == 1
    sent = fake_slack_client.sent[0]
    assert sent.slack_user_id == student.slack_user_id
    assert seminar.name in sent.text


async def test_submit_skips_slack_notification_without_slack_link(
    client, db_session, fake_slack_client
) -> None:
    student = await _make_student(db_session, slack_user_id=None)
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(db_session, term=term, seminar=seminar)
    await client.put(
        "/applications/me",
        headers=_auth_headers(student.email),
        json={
            "choices": [{"seminar_id": str(seminar.id), "priority": 1, "reason": "A"}]
        },
    )

    resp = await client.post(
        "/applications/me/submit", headers=_auth_headers(student.email)
    )

    assert resp.status_code == 200
    assert fake_slack_client.sent == []


async def test_submit_succeeds_even_if_slack_notification_fails(
    client, db_session, fake_slack_client, monkeypatch
) -> None:
    student = await _make_student(db_session, slack_user_id=_unique("U"))
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(db_session, term=term, seminar=seminar)
    await client.put(
        "/applications/me",
        headers=_auth_headers(student.email),
        json={
            "choices": [{"seminar_id": str(seminar.id), "priority": 1, "reason": "A"}]
        },
    )

    async def _boom(*, slack_user_id: str, text: str, blocks=None):
        raise RuntimeError("Slack API is down")

    monkeypatch.setattr(fake_slack_client, "send_dm", _boom)

    resp = await client.post(
        "/applications/me/submit", headers=_auth_headers(student.email)
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "submitted"


async def test_submit_without_draft_returns_404(client, db_session) -> None:
    student = await _make_student(db_session)
    await _make_open_term(db_session)

    resp = await client.post(
        "/applications/me/submit", headers=_auth_headers(student.email)
    )

    assert resp.status_code == 404


async def test_submit_without_choices_returns_400(client, db_session) -> None:
    student = await _make_student(db_session)
    await _make_open_term(db_session)
    await client.put(
        "/applications/me", headers=_auth_headers(student.email), json={"choices": []}
    )

    resp = await client.post(
        "/applications/me/submit", headers=_auth_headers(student.email)
    )

    assert resp.status_code == 400


async def test_submit_requires_active_term(client, db_session) -> None:
    await _close_all_open_terms(db_session)
    student = await _make_student(db_session)

    resp = await client.post(
        "/applications/me/submit", headers=_auth_headers(student.email)
    )

    assert resp.status_code == 400


async def test_submit_rejects_seminar_that_stopped_recruiting_after_draft_saved(
    client, db_session
) -> None:
    # 下書き保存時は募集中だったが、提出前に運営が募集を締め切ったケース。
    student = await _make_student(db_session)
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(db_session, term=term, seminar=seminar)

    await client.put(
        "/applications/me",
        headers=_auth_headers(student.email),
        json={
            "choices": [{"seminar_id": str(seminar.id), "priority": 1, "reason": "A"}]
        },
    )

    result = await db_session.execute(
        select(SeminarRecruitment).where(SeminarRecruitment.seminar_id == seminar.id)
    )
    recruitment = result.scalar_one()
    recruitment.target_grades = []
    await db_session.flush()

    resp = await client.post(
        "/applications/me/submit", headers=_auth_headers(student.email)
    )

    assert resp.status_code == 400
