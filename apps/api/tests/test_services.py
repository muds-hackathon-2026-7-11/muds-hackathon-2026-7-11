import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import update

from api.models import (
    ApplicationForm,
    ApplicationStatus,
    RecruitmentTerm,
    RecruitmentTermStatus,
    Seminar,
    SeminarRecruitment,
    User,
    UserRole,
)
from api.services import (
    find_students_without_submission,
    get_current_term,
    normalize_grade,
    send_deadline_reminders,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("B1", "B1"),
        ("B2", "B2"),
        ("B3", "B3"),
        ("B4", "B4"),
        # MIDS学生も末尾のB1〜B4として扱う(#99)。
        ("MIDS/B1", "B1"),
        ("MIDS/B3", "B3"),
        ("MIDS/B4", "B4"),
        # 大学院生・guest・空文字・未設定はB1〜B4のどれにも一致しない。
        ("M1", None),
        ("M1 guest", None),
        ("M2", None),
        ("M2 guest", None),
        ("D1", None),
        ("", None),
        (None, None),
    ],
)
def test_normalize_grade(raw: str | None, expected: str | None) -> None:
    assert normalize_grade(raw) == expected


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _make_term(
    db_session,
    *,
    ends_at: date,
    status: RecruitmentTermStatus = RecruitmentTermStatus.open,
) -> RecruitmentTerm:
    term = RecruitmentTerm(
        academic_year=3000 + int(uuid.uuid4().int % 1000),
        starts_at=ends_at - timedelta(days=30),
        ends_at=ends_at,
        status=status,
    )
    db_session.add(term)
    await db_session.flush()
    return term


_UNSET = object()


async def _make_student(
    db_session,
    *,
    slack_user_id: str | None | object = _UNSET,
    is_active: bool = True,
    role: UserRole = UserRole.student,
    grade: str | None = "B3",
) -> User:
    resolved_slack_user_id = _unique("U") if slack_user_id is _UNSET else slack_user_id
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('student')}@example.com",
        name=_unique("student"),
        role=role,
        slack_user_id=resolved_slack_user_id,
        is_active=is_active,
        grade=grade,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_recruitment(
    db_session, *, term: RecruitmentTerm, target_grades: list[str]
) -> SeminarRecruitment:
    """termに対して対象学年付きの募集ゼミを1件作る。

    find_students_without_submissionは対象学年(target_grades)で絞るため
    (#153)、これが無い(=SeminarRecruitmentが1件も無い)termだと常に
    空リストを返す。
    """
    seminar = Seminar(name=_unique("seminar"))
    db_session.add(seminar)
    await db_session.flush()
    recruitment = SeminarRecruitment(
        term_id=term.id,
        seminar_id=seminar.id,
        capacity=10,
        target_grades=target_grades,
    )
    db_session.add(recruitment)
    await db_session.flush()
    return recruitment


async def _submit(db_session, *, term: RecruitmentTerm, student: User) -> None:
    db_session.add(
        ApplicationForm(
            term_id=term.id, student_id=student.id, status=ApplicationStatus.submitted
        )
    )
    await db_session.flush()


async def _close_all_open_terms(db_session) -> None:
    """send_deadline_remindersは全てのopen募集期間を走査するため、共有DB上の
    実データの募集期間が「今日」「明日」を締切日とたまたま一致すると、その
    期間の実学生にまで通知対象が及んでしまう。db_sessionはテスト終了時に
    rollbackされるため、一時的にclosedへ変更しても安全
    (test_applications_api.pyの同名ヘルパーと同じパターン)。
    """
    await db_session.execute(
        update(RecruitmentTerm)
        .where(RecruitmentTerm.status == RecruitmentTermStatus.open)
        .values(status=RecruitmentTermStatus.closed)
    )
    await db_session.flush()


# --- find_students_without_submission ---


@pytest.mark.asyncio
async def test_find_students_without_submission_excludes_submitted(
    db_session,
) -> None:
    term = await _make_term(db_session, ends_at=date.today())
    await _make_recruitment(db_session, term=term, target_grades=["B3"])
    not_submitted = await _make_student(db_session)
    submitted = await _make_student(db_session)
    await _submit(db_session, term=term, student=submitted)

    result = await find_students_without_submission(db_session, term_id=term.id)

    result_ids = {u.id for u in result}
    assert not_submitted.id in result_ids
    assert submitted.id not in result_ids


@pytest.mark.asyncio
async def test_find_students_without_submission_excludes_unlinked_and_inactive(
    db_session,
) -> None:
    term = await _make_term(db_session, ends_at=date.today())
    await _make_recruitment(db_session, term=term, target_grades=["B3"])
    unlinked = await _make_student(db_session, slack_user_id=None)
    inactive = await _make_student(db_session, is_active=False)

    result = await find_students_without_submission(db_session, term_id=term.id)

    result_ids = {u.id for u in result}
    assert unlinked.id not in result_ids
    assert inactive.id not in result_ids


@pytest.mark.asyncio
async def test_find_students_without_submission_includes_admin_role(
    db_session,
) -> None:
    # role=adminであっても実際には在学中の学生であるユーザーがいるため、
    # applications.pyの各エンドポイントと同様に対象に含める。
    term = await _make_term(db_session, ends_at=date.today())
    await _make_recruitment(db_session, term=term, target_grades=["B3"])
    admin_student = await _make_student(db_session, role=UserRole.admin)
    teacher = await _make_student(db_session, role=UserRole.teacher)

    result = await find_students_without_submission(db_session, term_id=term.id)

    result_ids = {u.id for u in result}
    assert admin_student.id in result_ids
    assert teacher.id not in result_ids


@pytest.mark.asyncio
async def test_find_students_without_submission_excludes_grade_not_targeted(
    db_session,
) -> None:
    # このラウンドがB3のみ対象の場合、B4の学生はそもそも志望を提出できない
    # (マイページで「準備中」表示)。提出できない学生にリマインダーで
    # 「まだの場合はご提出ください」と催促するのはおかしいため、対象外の
    # 学年は除外する。
    term = await _make_term(db_session, ends_at=date.today())
    await _make_recruitment(db_session, term=term, target_grades=["B3"])
    targeted = await _make_student(db_session, grade="B3")
    not_targeted = await _make_student(db_session, grade="B4")
    no_grade = await _make_student(db_session, grade=None)

    result = await find_students_without_submission(db_session, term_id=term.id)

    result_ids = {u.id for u in result}
    assert targeted.id in result_ids
    assert not_targeted.id not in result_ids
    assert no_grade.id not in result_ids


@pytest.mark.asyncio
async def test_find_students_without_submission_matches_mids_style_grade(
    db_session,
) -> None:
    # 表記揺れ(#99)。"MIDS/B3"のような学生もnormalize_grade経由でB3として
    # 対象学年判定される。
    term = await _make_term(db_session, ends_at=date.today())
    await _make_recruitment(db_session, term=term, target_grades=["B3"])
    mids_student = await _make_student(db_session, grade="MIDS/B3")

    result = await find_students_without_submission(db_session, term_id=term.id)

    assert mids_student.id in {u.id for u in result}


@pytest.mark.asyncio
async def test_find_students_without_submission_empty_when_term_has_no_recruitments(
    db_session,
) -> None:
    # SeminarRecruitmentが1件も無い(=対象学年が定義できない)募集ラウンドでは、
    # 「全学生が対象」にフォールバックしてはいけない。
    term = await _make_term(db_session, ends_at=date.today())
    await _make_student(db_session, grade="B3")

    result = await find_students_without_submission(db_session, term_id=term.id)

    assert result == []


# --- send_deadline_reminders ---


@pytest.mark.asyncio
async def test_send_deadline_reminders_sends_on_deadline_day(
    db_session, fake_slack_client
) -> None:
    await _close_all_open_terms(db_session)
    term = await _make_term(db_session, ends_at=date.today())
    await _make_recruitment(db_session, term=term, target_grades=["B3"])
    student = await _make_student(db_session)

    await send_deadline_reminders(db_session, fake_slack_client)

    sent_by_id = {s.slack_user_id: s for s in fake_slack_client.sent}
    assert student.slack_user_id in sent_by_id
    assert "本日" in sent_by_id[student.slack_user_id].text


@pytest.mark.asyncio
async def test_send_deadline_reminders_sends_the_day_before_deadline(
    db_session, fake_slack_client
) -> None:
    await _close_all_open_terms(db_session)
    term = await _make_term(db_session, ends_at=date.today() + timedelta(days=1))
    await _make_recruitment(db_session, term=term, target_grades=["B3"])
    student = await _make_student(db_session)

    await send_deadline_reminders(db_session, fake_slack_client)

    sent_by_id = {s.slack_user_id: s for s in fake_slack_client.sent}
    assert student.slack_user_id in sent_by_id
    assert "締切まで1日です" in sent_by_id[student.slack_user_id].text


@pytest.mark.asyncio
async def test_send_deadline_reminders_ignores_terms_two_days_out(
    db_session, fake_slack_client
) -> None:
    await _close_all_open_terms(db_session)
    term = await _make_term(db_session, ends_at=date.today() + timedelta(days=2))
    await _make_recruitment(db_session, term=term, target_grades=["B3"])
    student = await _make_student(db_session)

    await send_deadline_reminders(db_session, fake_slack_client)

    sent_ids = {s.slack_user_id for s in fake_slack_client.sent}
    assert student.slack_user_id not in sent_ids


@pytest.mark.asyncio
async def test_send_deadline_reminders_ignores_closed_terms(
    db_session, fake_slack_client
) -> None:
    await _close_all_open_terms(db_session)
    term = await _make_term(
        db_session, ends_at=date.today(), status=RecruitmentTermStatus.closed
    )
    await _make_recruitment(db_session, term=term, target_grades=["B3"])
    student = await _make_student(db_session)

    await send_deadline_reminders(db_session, fake_slack_client)

    sent_ids = {s.slack_user_id for s in fake_slack_client.sent}
    assert student.slack_user_id not in sent_ids


@pytest.mark.asyncio
async def test_send_deadline_reminders_skips_students_who_submitted(
    db_session, fake_slack_client
) -> None:
    await _close_all_open_terms(db_session)
    term = await _make_term(db_session, ends_at=date.today())
    await _make_recruitment(db_session, term=term, target_grades=["B3"])
    submitted = await _make_student(db_session)
    await _submit(db_session, term=term, student=submitted)

    await send_deadline_reminders(db_session, fake_slack_client)

    sent_ids = {s.slack_user_id for s in fake_slack_client.sent}
    assert submitted.slack_user_id not in sent_ids


@pytest.mark.asyncio
async def test_send_deadline_reminders_skips_students_whose_grade_is_not_targeted(
    db_session, fake_slack_client
) -> None:
    await _close_all_open_terms(db_session)
    term = await _make_term(db_session, ends_at=date.today())
    await _make_recruitment(db_session, term=term, target_grades=["B3"])
    not_targeted = await _make_student(db_session, grade="B4")

    await send_deadline_reminders(db_session, fake_slack_client)

    sent_ids = {s.slack_user_id for s in fake_slack_client.sent}
    assert not_targeted.slack_user_id not in sent_ids


@pytest.mark.asyncio
async def test_send_deadline_reminders_continues_after_individual_failure(
    db_session, fake_slack_client, monkeypatch
) -> None:
    await _close_all_open_terms(db_session)
    term = await _make_term(db_session, ends_at=date.today())
    await _make_recruitment(db_session, term=term, target_grades=["B3"])
    failing_student = await _make_student(db_session)
    other_student = await _make_student(db_session)

    original_send_dm = fake_slack_client.send_dm

    async def _flaky_send_dm(*, slack_user_id: str, text: str, blocks=None):
        if slack_user_id == failing_student.slack_user_id:
            raise RuntimeError("Slack API is down")
        return await original_send_dm(
            slack_user_id=slack_user_id, text=text, blocks=blocks
        )

    monkeypatch.setattr(fake_slack_client, "send_dm", _flaky_send_dm)

    await send_deadline_reminders(db_session, fake_slack_client)

    # failing_studentへの送信失敗が、other_studentへの送信を止めない。
    sent_ids = {s.slack_user_id for s in fake_slack_client.sent}
    assert failing_student.slack_user_id not in sent_ids
    assert other_student.slack_user_id in sent_ids


@pytest.mark.asyncio
async def test_get_current_term_prefers_latest_created_at_when_academic_year_ties(
    db_session,
) -> None:
    # 前期・後期のように、同じacademic_yearでopenな募集ラウンドが複数
    # 存在し、両方が同時にアクティブな場合(#57で作成可能、実際に運用DBで
    # 発生した)、created_atが最も新しいもの(=最後に設定されたラウンド)
    # が決定的に選ばれることを確認する(#182)。starts_atはdate型で日単位
    # までしか区別できない(かつ運営の任意入力)ため、あえて同じ日付にして
    # starts_atでは区別できないケースであることを明示している。academic_year
    # を3000+乱数にしているのは、実DBに残っている本物の募集ラウンドより
    # 必ず新しい年度にして、そちらを誤って拾わないようにするため。
    academic_year = 3000 + int(uuid.uuid4().int % 1000)
    today = date.today()
    now = datetime.now(UTC)
    older = RecruitmentTerm(
        academic_year=academic_year,
        starts_at=today,
        ends_at=today + timedelta(days=90),
        status=RecruitmentTermStatus.open,
        created_at=now - timedelta(seconds=10),
    )
    newer = RecruitmentTerm(
        academic_year=academic_year,
        starts_at=today,
        ends_at=today + timedelta(days=10),
        status=RecruitmentTermStatus.open,
        created_at=now,
    )
    db_session.add_all([older, newer])
    await db_session.flush()

    term = await get_current_term(db_session)

    assert term is not None
    assert term.id == newer.id


@pytest.mark.asyncio
async def test_get_current_term_is_deterministic_even_when_fully_tied(
    db_session,
) -> None:
    # academic_year・starts_at・created_atまで全て一致する場合(同一
    # トランザクションでの一括作成などで理論上起こりうる。Postgresの
    # NOW()はトランザクション開始時刻なので、同時に複数行INSERTすると
    # created_atも同値になる)でも、idによる最終フォールバックで毎回
    # 同じ行を返すことを確認する(#182)。業務的な「正しさ」は無いが、
    # 同じリクエストのたびに結果が変わらないことが重要。
    academic_year = 3000 + int(uuid.uuid4().int % 1000)
    today = date.today()
    same_created_at = datetime.now(UTC)
    first = RecruitmentTerm(
        academic_year=academic_year,
        starts_at=today,
        ends_at=today + timedelta(days=30),
        status=RecruitmentTermStatus.open,
        created_at=same_created_at,
    )
    second = RecruitmentTerm(
        academic_year=academic_year,
        starts_at=today,
        ends_at=today + timedelta(days=30),
        status=RecruitmentTermStatus.open,
        created_at=same_created_at,
    )
    db_session.add_all([first, second])
    await db_session.flush()

    first_call = await get_current_term(db_session)
    second_call = await get_current_term(db_session)

    assert first_call is not None
    assert second_call is not None
    assert first_call.id == second_call.id
