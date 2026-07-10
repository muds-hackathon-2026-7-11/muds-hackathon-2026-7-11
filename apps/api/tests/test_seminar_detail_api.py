import uuid
from datetime import date, timedelta

import pytest

from api import auth
from api.models import (
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


def _auth_headers(email: str) -> dict[str, str]:
    return {"X-Dev-User-Email": email, "X-Dev-User-Role": "student"}


@pytest.fixture(autouse=True)
def _enable_dev_auth(monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_dev_mode", True)


async def _make_seminar(db_session) -> Seminar:
    seminar = Seminar(name=_unique("seminar"))
    db_session.add(seminar)
    await db_session.flush()
    return seminar


async def _make_open_term(db_session, academic_year: int) -> RecruitmentTerm:
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


async def _make_user(
    db_session, role: UserRole, research_theme: str | None = None
) -> User:
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name=_unique("name"),
        role=role,
        research_theme=research_theme,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_get_seminar_detail_includes_teachers_materials_and_current_members(
    client, db_session
) -> None:
    academic_year = 3000 + int(uuid.uuid4().int % 1000)
    term = await _make_open_term(db_session, academic_year)
    seminar = await _make_seminar(db_session)
    db_session.add(
        SeminarRecruitment(term_id=term.id, seminar_id=seminar.id, capacity=10)
    )

    teacher1 = await _make_user(db_session, UserRole.teacher, "研究テーマA")
    teacher2 = await _make_user(db_session, UserRole.teacher, "研究テーマB")
    db_session.add(SeminarTeacher(seminar_id=seminar.id, teacher_id=teacher1.id))
    db_session.add(SeminarTeacher(seminar_id=seminar.id, teacher_id=teacher2.id))

    db_session.add(
        SeminarMaterial(
            seminar_id=seminar.id,
            url="https://example.com/a.pdf",
            type=MaterialType.pdf,
        )
    )

    past_term = await _make_open_term(db_session, academic_year - 1)
    current_student = await _make_user(db_session, UserRole.student, "現役の研究テーマ")
    past_student = await _make_user(db_session, UserRole.student, "過去の研究テーマ")
    db_session.add(
        SeminarMember(
            seminar_id=seminar.id,
            student_id=current_student.id,
            term_id=term.id,
        )
    )
    db_session.add(
        SeminarMember(
            seminar_id=seminar.id,
            student_id=past_student.id,
            term_id=past_term.id,
        )
    )
    await db_session.flush()

    resp = await client.get(
        f"/seminars/{seminar.id}", headers=_auth_headers(current_student.email)
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(seminar.id)
    assert body["capacity"] == 10
    assert body["recruitment_start"] == str(term.starts_at)
    assert {t["name"] for t in body["teachers"]} == {teacher1.name, teacher2.name}
    assert len(body["materials"]) == 1
    assert body["materials"][0]["url"] == "https://example.com/a.pdf"
    member_names = {m["name"] for m in body["current_members"]}
    assert member_names == {current_student.name}
    assert past_student.name not in member_names


async def test_get_seminar_detail_unknown_id_returns_404(client, db_session) -> None:
    user = await _make_user(db_session, UserRole.student)
    resp = await client.get(
        f"/seminars/{uuid.uuid4()}", headers=_auth_headers(user.email)
    )

    assert resp.status_code == 404


async def test_get_seminar_detail_requires_auth(
    client, db_session, monkeypatch
) -> None:
    seminar = await _make_seminar(db_session)
    await db_session.flush()
    monkeypatch.setattr(auth.settings, "auth_dev_mode", False)

    resp = await client.get(f"/seminars/{seminar.id}")

    assert resp.status_code == 401


async def test_get_seminar_detail_without_recruitment_data_returns_empty_lists(
    client, db_session
) -> None:
    seminar = await _make_seminar(db_session)
    user = await _make_user(db_session, UserRole.student)
    await db_session.flush()

    resp = await client.get(
        f"/seminars/{seminar.id}", headers=_auth_headers(user.email)
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["capacity"] is None
    assert body["teachers"] == []
    assert body["materials"] == []
    assert body["current_members"] == []


async def test_get_seminar_detail_shows_current_members_without_an_active_term(
    client, db_session
) -> None:
    # 募集期間が(open/日付内という意味で)アクティブでなくても、現在のゼミ生は
    # 直近に作成された募集期間の年度を基準に表示できる(#77)。
    academic_year = 3000 + int(uuid.uuid4().int % 1000)
    closed_term = RecruitmentTerm(
        academic_year=academic_year,
        starts_at=date.today() - timedelta(days=60),
        ends_at=date.today() - timedelta(days=30),
        status=RecruitmentTermStatus.closed,
    )
    db_session.add(closed_term)
    await db_session.flush()

    seminar = await _make_seminar(db_session)
    student = await _make_user(db_session, UserRole.student, "現役の研究テーマ")
    db_session.add(
        SeminarMember(
            seminar_id=seminar.id, student_id=student.id, term_id=closed_term.id
        )
    )
    await db_session.flush()

    resp = await client.get(
        f"/seminars/{seminar.id}", headers=_auth_headers(student.email)
    )

    assert resp.status_code == 200
    body = resp.json()
    # 募集期間がアクティブでないため定員は未設定のままだが、現在のゼミ生は見える。
    assert body["capacity"] is None
    assert {m["name"] for m in body["current_members"]} == {student.name}


async def test_get_seminar_detail_ignores_a_newer_preparing_term_for_current_members(
    client, db_session
) -> None:
    # 運営が来年度分のラウンドをstatus=preparingで前倒しに作っただけの
    # 段階では、それを「現在の年度」にしてしまうと在籍ゼミ生が誰も
    # 表示されなくなってしまっていた(実際の不具合)。
    academic_year = 3000 + int(uuid.uuid4().int % 1000)
    term = await _make_open_term(db_session, academic_year)
    seminar = await _make_seminar(db_session)
    student = await _make_user(db_session, UserRole.student, "現役の研究テーマ")
    db_session.add(
        SeminarMember(seminar_id=seminar.id, student_id=student.id, term_id=term.id)
    )
    # まだ何の配属も行われていない、準備段階の次年度ラウンド。
    next_term = RecruitmentTerm(
        academic_year=academic_year + 1,
        starts_at=date.today() + timedelta(days=300),
        ends_at=date.today() + timedelta(days=330),
        status=RecruitmentTermStatus.preparing,
    )
    db_session.add(next_term)
    await db_session.flush()

    resp = await client.get(
        f"/seminars/{seminar.id}", headers=_auth_headers(student.email)
    )

    assert resp.status_code == 200
    assert {m["name"] for m in resp.json()["current_members"]} == {student.name}


async def test_get_seminar_detail_ignores_a_term_opened_before_it_starts(
    client, db_session
) -> None:
    # status=preparingを除くだけでは不十分: 運営がまだ始まっていない
    # 来年度分のラウンドを(準備目的で)早めにstatus=openにしただけでも、
    # 在籍ゼミ生が消えないことを確認する。
    academic_year = 3000 + int(uuid.uuid4().int % 1000)
    term = await _make_open_term(db_session, academic_year)
    seminar = await _make_seminar(db_session)
    student = await _make_user(db_session, UserRole.student, "現役の研究テーマ")
    db_session.add(
        SeminarMember(seminar_id=seminar.id, student_id=student.id, term_id=term.id)
    )
    # まだ何の配属も行われていない、始まる前の次年度ラウンド(status=open)。
    next_term = RecruitmentTerm(
        academic_year=academic_year + 1,
        starts_at=date.today() + timedelta(days=30),
        ends_at=date.today() + timedelta(days=60),
        status=RecruitmentTermStatus.open,
    )
    db_session.add(next_term)
    await db_session.flush()

    resp = await client.get(
        f"/seminars/{seminar.id}", headers=_auth_headers(student.email)
    )

    assert resp.status_code == 200
    assert {m["name"] for m in resp.json()["current_members"]} == {student.name}


async def test_get_seminar_detail_ignores_open_term_outside_its_date_range(
    client, db_session
) -> None:
    # status=open でも starts_at より前、あるいは ends_at より後なら
    # 「募集中」として扱わない(運営が翌年度分を早めにopenにしても
    # 開始日前は反映されない、というのが今回直した挙動)。
    academic_year = 3000 + int(uuid.uuid4().int % 1000)
    future_term = RecruitmentTerm(
        academic_year=academic_year,
        starts_at=date.today() + timedelta(days=30),
        ends_at=date.today() + timedelta(days=60),
        status=RecruitmentTermStatus.open,
    )
    db_session.add(future_term)
    await db_session.flush()

    seminar = await _make_seminar(db_session)
    db_session.add(
        SeminarRecruitment(term_id=future_term.id, seminar_id=seminar.id, capacity=10)
    )
    user = await _make_user(db_session, UserRole.student)
    await db_session.flush()

    resp = await client.get(
        f"/seminars/{seminar.id}", headers=_auth_headers(user.email)
    )

    assert resp.status_code == 200
    body = resp.json()
    # このゼミはfuture_term(期間外)のSeminarRecruitmentしか持たないため、
    # (他にDB上に本当にactiveな募集ラウンドがあるかどうかに関わらず)
    # このゼミ自身の定員は反映されないはず
    assert body["capacity"] is None
