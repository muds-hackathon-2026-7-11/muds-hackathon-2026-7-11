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
    MaterialType,
    RecruitmentTerm,
    RecruitmentTermStatus,
    Seminar,
    SeminarMaterial,
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
    research_title: str | None = None,
    research_theme: str | None = None,
) -> User:
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name=_unique("name"),
        role=role,
        grade=grade,
        is_active=is_active,
        student_id=student_id,
        research_title=research_title,
        research_theme=research_theme,
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
        db_session,
        UserRole.student,
        grade="B3",
        student_id="s2311777",
        research_title="推薦システムの研究",
        research_theme="協調フィルタリングによる推薦精度の向上について研究しています。",
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
    assert "研究タイトル" in text
    assert "研究概要" in text
    assert "前回所属ゼミ" in text
    assert "過去の所属ゼミ" not in text
    assert "s2311777" in text
    assert student.name in text
    assert "推薦システムの研究" in text
    assert "協調フィルタリングによる推薦精度の向上について研究しています。" in text


async def test_applicants_csv_shows_only_the_most_recent_past_seminar(
    client, db_session
) -> None:
    term = await _make_open_term(db_session)
    teacher = await _make_user(db_session, UserRole.teacher)
    seminar = await _make_seminar(db_session)
    old_seminar = await _make_seminar(db_session)
    older_seminar = await _make_seminar(db_session)
    await _link_teacher(db_session, seminar, teacher)
    student = await _make_user(db_session, UserRole.student, grade="B4")
    await _apply(
        db_session,
        term=term,
        student=student,
        status=ApplicationStatus.submitted,
        choices=[(seminar, 1, "志望します")],
    )

    recent_term = RecruitmentTerm(
        academic_year=term.academic_year - 1,
        starts_at=date(term.academic_year - 1, 4, 1),
        ends_at=date(term.academic_year - 1, 9, 30),
        status=RecruitmentTermStatus.closed,
    )
    older_term = RecruitmentTerm(
        academic_year=term.academic_year - 2,
        starts_at=date(term.academic_year - 2, 4, 1),
        ends_at=date(term.academic_year - 2, 9, 30),
        status=RecruitmentTermStatus.closed,
    )
    db_session.add_all([recent_term, older_term])
    await db_session.flush()
    db_session.add_all(
        [
            SeminarMember(
                seminar_id=old_seminar.id,
                student_id=student.id,
                term_id=recent_term.id,
            ),
            SeminarMember(
                seminar_id=older_seminar.id,
                student_id=student.id,
                term_id=older_term.id,
            ),
        ]
    )
    await db_session.flush()

    _authenticate_as(teacher)
    resp = await client.get("/teacher/applicants.csv")

    assert resp.status_code == 200
    text = resp.text
    assert old_seminar.name in text
    assert older_seminar.name not in text


async def test_all_applicants_csv_includes_other_teachers_seminars(
    client, db_session
) -> None:
    term = await _make_open_term(db_session)
    teacher = await _make_user(db_session, UserRole.teacher)
    other_teacher = await _make_user(db_session, UserRole.teacher)
    my_seminar = await _make_seminar(db_session)
    other_seminar = await _make_seminar(db_session)
    await _link_teacher(db_session, my_seminar, teacher)
    await _link_teacher(db_session, other_seminar, other_teacher)

    my_student = await _make_user(
        db_session, UserRole.student, grade="B3", student_id="s2311001"
    )
    other_student = await _make_user(
        db_session, UserRole.student, grade="B4", student_id="s2311002"
    )
    await _apply(
        db_session,
        term=term,
        student=my_student,
        status=ApplicationStatus.submitted,
        choices=[(my_seminar, 1, "自ゼミへの志望理由")],
    )
    await _apply(
        db_session,
        term=term,
        student=other_student,
        status=ApplicationStatus.submitted,
        choices=[(other_seminar, 1, "他ゼミへの志望理由")],
    )

    # 自分の担当ではないother_seminarの応募者を含め、"全体"扱いで担当していない
    # 教員として参照する(#146: 教員向けCSV出力「自分のゼミ、全体csv」)。
    _authenticate_as(teacher)
    resp = await client.get("/teacher/applicants/all.csv")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    text = resp.text
    assert my_seminar.name in text
    assert other_seminar.name in text
    assert my_student.name in text
    assert other_student.name in text


async def test_all_applicants_csv_requires_teacher_role(client, db_session) -> None:
    _authenticate_as(await _make_user(db_session, UserRole.student))
    resp = await client.get("/teacher/applicants/all.csv")
    assert resp.status_code == 403


# --- 未提出者一覧 (#182) ---


async def _make_recruitment(
    db_session,
    *,
    term: RecruitmentTerm,
    seminar: Seminar,
    target_grades: list[str],
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


async def test_unsubmitted_applicants_lists_targeted_students_without_submission(
    client, db_session
) -> None:
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(
        db_session, term=term, seminar=seminar, target_grades=["B3", "B4"]
    )
    teacher = await _make_user(db_session, UserRole.teacher)
    await _link_teacher(db_session, seminar, teacher)

    # 表記揺れ(#99)のある学生も、末尾一致でB3の対象として拾えるかを確認する。
    not_submitted = await _make_user(db_session, UserRole.student, grade="MIDS/B3")
    submitted = await _make_user(db_session, UserRole.student, grade="B3")
    draft_only = await _make_user(db_session, UserRole.student, grade="B4")
    out_of_target_grade = await _make_user(db_session, UserRole.student, grade="B1")
    inactive = await _make_user(
        db_session, UserRole.student, grade="B3", is_active=False
    )

    await _apply(
        db_session,
        term=term,
        student=submitted,
        status=ApplicationStatus.submitted,
        choices=[(seminar, 1, "志望します")],
    )
    await _apply(
        db_session,
        term=term,
        student=draft_only,
        status=ApplicationStatus.draft,
        choices=[(seminar, 1, "下書き")],
    )

    _authenticate_as(teacher)
    resp = await client.get("/teacher/unsubmitted-applicants")

    assert resp.status_code == 200
    body = resp.json()
    names = [a["name"] for a in body]
    assert not_submitted.name in names
    assert draft_only.name in names
    assert submitted.name not in names
    assert out_of_target_grade.name not in names
    assert inactive.name not in names

    not_submitted_entry = next(a for a in body if a["name"] == not_submitted.name)
    assert not_submitted_entry["grade"] == "MIDS/B3"
    assert not_submitted_entry["normalized_grade"] == "B3"


async def test_unsubmitted_applicants_returns_empty_when_term_has_no_recruitments(
    client, db_session
) -> None:
    # 募集ラウンドはopenでも、対象ゼミ(SeminarRecruitment)が1件も無ければ
    # 対象学年が定義できない。実DBで同じacademic_yearのopenラウンドが複数
    # 存在し、そのうち定員設定が空のものをget_current_termが拾ってしまう
    # ケースを想定した回帰テスト(#182)。「全学生が未提出」ではなく空配列を
    # 返すべき。
    await _make_open_term(db_session)
    teacher = await _make_user(db_session, UserRole.teacher)
    await _make_user(db_session, UserRole.student, grade="B1")

    _authenticate_as(teacher)
    resp = await client.get("/teacher/unsubmitted-applicants")

    assert resp.status_code == 200
    assert resp.json() == []


async def test_unsubmitted_applicants_allows_admin(client, db_session) -> None:
    term = await _make_open_term(db_session)
    seminar = await _make_seminar(db_session)
    await _make_recruitment(
        db_session, term=term, seminar=seminar, target_grades=["B1"]
    )
    admin = await _make_user(db_session, UserRole.admin)
    student = await _make_user(db_session, UserRole.student, grade="B1")

    _authenticate_as(admin)
    resp = await client.get("/teacher/unsubmitted-applicants")

    assert resp.status_code == 200
    # 実DB(共有の開発用DB)には他のB1学生も存在しうるため、対象学生が
    # 含まれていることだけを確認する(完全一致は実データに左右され壊れやすい)。
    assert student.name in [a["name"] for a in resp.json()]


async def test_unsubmitted_applicants_requires_teacher_or_admin_role(
    client, db_session
) -> None:
    _authenticate_as(await _make_user(db_session, UserRole.student))
    resp = await client.get("/teacher/unsubmitted-applicants")
    assert resp.status_code == 403


# --- 自ゼミの紹介内容編集 ---


async def test_list_own_seminars_includes_materials_and_excludes_others(
    client, db_session
) -> None:
    teacher = await _make_user(db_session, UserRole.teacher)
    other_teacher = await _make_user(db_session, UserRole.teacher)
    my_seminar = await _make_seminar(db_session)
    my_seminar.description = "紹介文"
    other_seminar = await _make_seminar(db_session)
    await _link_teacher(db_session, my_seminar, teacher)
    await _link_teacher(db_session, other_seminar, other_teacher)
    db_session.add(
        SeminarMaterial(
            seminar_id=my_seminar.id,
            url="https://example.com/slide.pdf",
            type=MaterialType.pdf,
        )
    )
    await db_session.flush()

    _authenticate_as(teacher)
    resp = await client.get("/teacher/seminars")

    assert resp.status_code == 200
    body = resp.json()
    assert [s["id"] for s in body] == [str(my_seminar.id)]
    assert body[0]["description"] == "紹介文"
    assert [m["url"] for m in body[0]["materials"]] == ["https://example.com/slide.pdf"]


async def test_list_own_seminars_excludes_inactive_co_teachers(
    client, db_session
) -> None:
    # 退職教員(is_active=false)は担当付け外し自体は残る運用のため、
    # 共同担当の一覧に「現役」として表示され続けないようにする(#171)。
    teacher = await _make_user(db_session, UserRole.teacher)
    retired_teacher = await _make_user(db_session, UserRole.teacher, is_active=False)
    seminar = await _make_seminar(db_session)
    await _link_teacher(db_session, seminar, teacher)
    await _link_teacher(db_session, seminar, retired_teacher)
    await db_session.flush()

    _authenticate_as(teacher)
    resp = await client.get("/teacher/seminars")

    assert resp.status_code == 200
    teacher_ids = {t["id"] for t in resp.json()[0]["teachers"]}
    assert str(teacher.id) in teacher_ids
    assert str(retired_teacher.id) not in teacher_ids


async def test_list_own_seminars_reflects_current_round_capacity(
    client, db_session
) -> None:
    # 定員(#184)は募集ラウンドごとのSeminarRecruitmentに紐づくため、
    # まだ設定していなければnull、PATCH .../recruitmentで設定した後は
    # その値がGET /teacher/seminarsにも反映されることを確認する。
    await _make_open_term(db_session)
    teacher = await _make_user(db_session, UserRole.teacher)
    seminar = await _make_seminar(db_session)
    await _link_teacher(db_session, seminar, teacher)

    _authenticate_as(teacher)
    before = await client.get("/teacher/seminars")
    assert before.status_code == 200
    assert before.json()[0]["capacity"] is None

    patch_resp = await client.patch(
        f"/teacher/seminars/{seminar.id}/recruitment",
        json={"capacity": 15},
    )
    assert patch_resp.status_code == 200

    after = await client.get("/teacher/seminars")
    assert after.json()[0]["capacity"] == 15


async def test_update_own_seminar(client, db_session) -> None:
    teacher = await _make_user(db_session, UserRole.teacher)
    seminar = await _make_seminar(db_session)
    await _link_teacher(db_session, seminar, teacher)

    _authenticate_as(teacher)
    resp = await client.patch(
        f"/teacher/seminars/{seminar.id}",
        json={
            "description": "新しい紹介文",
            "photo_url": "https://example.com/lab.jpg",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["description"] == "新しい紹介文"
    assert body["photo_url"] == "https://example.com/lab.jpg"
    assert body["name"] == seminar.name  # 名称は変更されない

    await db_session.refresh(seminar)
    assert seminar.description == "新しい紹介文"


async def test_update_own_seminar_keeps_omitted_fields(client, db_session) -> None:
    teacher = await _make_user(db_session, UserRole.teacher)
    seminar = await _make_seminar(db_session)
    seminar.description = "元の紹介文"
    await db_session.flush()
    await _link_teacher(db_session, seminar, teacher)

    _authenticate_as(teacher)
    resp = await client.patch(
        f"/teacher/seminars/{seminar.id}",
        json={"photo_url": "https://example.com/lab.jpg"},
    )

    assert resp.status_code == 200
    assert resp.json()["description"] == "元の紹介文"


async def test_update_seminar_forbidden_for_other_teachers_seminar(
    client, db_session
) -> None:
    teacher = await _make_user(db_session, UserRole.teacher)
    not_mine = await _make_seminar(db_session)

    _authenticate_as(teacher)
    resp = await client.patch(
        f"/teacher/seminars/{not_mine.id}", json={"description": "勝手に編集"}
    )
    assert resp.status_code == 403


async def test_create_own_seminar_material(client, db_session) -> None:
    teacher = await _make_user(db_session, UserRole.teacher)
    seminar = await _make_seminar(db_session)
    await _link_teacher(db_session, seminar, teacher)

    _authenticate_as(teacher)
    resp = await client.post(
        f"/teacher/seminars/{seminar.id}/materials",
        json={"url": "https://example.com/slide.pdf", "type": "pdf"},
    )

    assert resp.status_code == 201
    assert resp.json()["url"] == "https://example.com/slide.pdf"

    result = await db_session.execute(
        select(SeminarMaterial).where(SeminarMaterial.seminar_id == seminar.id)
    )
    assert result.scalar_one().url == "https://example.com/slide.pdf"


async def test_create_own_seminar_material_rejects_non_http_scheme(
    client, db_session
) -> None:
    # javascript: 等はそのままリンクにするとクリックで実行されてしまうため
    # 拒否する(#172)。
    teacher = await _make_user(db_session, UserRole.teacher)
    seminar = await _make_seminar(db_session)
    await _link_teacher(db_session, seminar, teacher)

    _authenticate_as(teacher)
    resp = await client.post(
        f"/teacher/seminars/{seminar.id}/materials",
        json={"url": "javascript:alert(1)", "type": "pdf"},
    )

    assert resp.status_code == 422


async def test_create_material_forbidden_for_other_teachers_seminar(
    client, db_session
) -> None:
    teacher = await _make_user(db_session, UserRole.teacher)
    not_mine = await _make_seminar(db_session)

    _authenticate_as(teacher)
    resp = await client.post(
        f"/teacher/seminars/{not_mine.id}/materials",
        json={"url": "https://example.com/slide.pdf", "type": "pdf"},
    )
    assert resp.status_code == 403


async def test_delete_own_seminar_material(client, db_session) -> None:
    teacher = await _make_user(db_session, UserRole.teacher)
    seminar = await _make_seminar(db_session)
    await _link_teacher(db_session, seminar, teacher)
    material = SeminarMaterial(
        seminar_id=seminar.id, url="https://example.com/old.pdf", type=MaterialType.pdf
    )
    db_session.add(material)
    await db_session.flush()

    _authenticate_as(teacher)
    resp = await client.delete(
        f"/teacher/seminars/{seminar.id}/materials/{material.id}"
    )

    assert resp.status_code == 204
    assert await db_session.get(SeminarMaterial, material.id) is None


async def test_delete_material_forbidden_for_other_teachers_seminar(
    client, db_session
) -> None:
    teacher = await _make_user(db_session, UserRole.teacher)
    other_teacher = await _make_user(db_session, UserRole.teacher)
    not_mine = await _make_seminar(db_session)
    await _link_teacher(db_session, not_mine, other_teacher)
    material = SeminarMaterial(
        seminar_id=not_mine.id, url="https://example.com/old.pdf", type=MaterialType.pdf
    )
    db_session.add(material)
    await db_session.flush()

    _authenticate_as(teacher)
    resp = await client.delete(
        f"/teacher/seminars/{not_mine.id}/materials/{material.id}"
    )
    assert resp.status_code == 403


async def test_delete_material_unknown_id_returns_404(client, db_session) -> None:
    teacher = await _make_user(db_session, UserRole.teacher)
    seminar = await _make_seminar(db_session)
    await _link_teacher(db_session, seminar, teacher)

    _authenticate_as(teacher)
    resp = await client.delete(
        f"/teacher/seminars/{seminar.id}/materials/{uuid.uuid4()}"
    )
    assert resp.status_code == 404


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
