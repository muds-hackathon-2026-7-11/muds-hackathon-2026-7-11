import uuid
from datetime import date

import pytest

from api import auth
from api.auth import get_current_user
from api.main import app
from api.models import (
    RecruitmentTerm,
    RecruitmentTermStatus,
    Seminar,
    User,
    UserRole,
)

pytestmark = pytest.mark.asyncio


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _make_user(db_session, role: UserRole) -> User:
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name=_unique("name"),
        role=role,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_seminar(db_session) -> Seminar:
    seminar = Seminar(name=_unique("seminar"))
    db_session.add(seminar)
    await db_session.flush()
    return seminar


async def _make_term(
    db_session,
    *,
    academic_year: int,
    status: RecruitmentTermStatus = RecruitmentTermStatus.open,
) -> RecruitmentTerm:
    term = RecruitmentTerm(
        academic_year=academic_year,
        starts_at=date(academic_year, 4, 1),
        ends_at=date(academic_year, 12, 31),
        status=status,
    )
    db_session.add(term)
    await db_session.flush()
    return term


def _authenticate_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


# --- 募集ラウンド ---


async def test_create_and_list_recruitment_terms(client, db_session) -> None:
    _authenticate_as(await _make_user(db_session, UserRole.admin))

    resp = await client.post(
        "/admin/recruitment-terms",
        json={
            "academic_year": 4100,
            "starts_at": "4100-04-01",
            "ends_at": "4100-05-31",
            "status": "open",
        },
    )
    assert resp.status_code == 201
    created = resp.json()
    assert created["academic_year"] == 4100
    assert created["status"] == "open"

    listed = await client.get("/admin/recruitment-terms")
    assert listed.status_code == 200
    assert created["id"] in [t["id"] for t in listed.json()]


async def test_create_rejects_start_after_end(client, db_session) -> None:
    _authenticate_as(await _make_user(db_session, UserRole.admin))
    resp = await client.post(
        "/admin/recruitment-terms",
        json={
            "academic_year": 4101,
            "starts_at": "4101-06-01",
            "ends_at": "4101-05-01",
            "status": "preparing",
        },
    )
    assert resp.status_code == 400


async def test_allows_multiple_terms_in_same_year(client, db_session) -> None:
    _authenticate_as(await _make_user(db_session, UserRole.admin))
    r1 = await client.post(
        "/admin/recruitment-terms",
        json={
            "academic_year": 4102,
            "starts_at": "4102-04-01",
            "ends_at": "4102-05-31",
            "status": "preparing",
        },
    )
    r2 = await client.post(
        "/admin/recruitment-terms",
        json={
            "academic_year": 4102,
            "starts_at": "4102-09-01",
            "ends_at": "4102-10-31",
            "status": "preparing",
        },
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] != r2.json()["id"]


async def test_update_recruitment_term(client, db_session) -> None:
    _authenticate_as(await _make_user(db_session, UserRole.admin))
    term = await _make_term(
        db_session, academic_year=4103, status=RecruitmentTermStatus.preparing
    )

    resp = await client.patch(
        f"/admin/recruitment-terms/{term.id}",
        json={"status": "open", "ends_at": "4103-12-01"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "open"
    assert resp.json()["ends_at"] == "4103-12-01"


# --- ゼミ別 定員・対象学年 ---


async def test_upsert_and_list_seminar_recruitment(client, db_session) -> None:
    _authenticate_as(await _make_user(db_session, UserRole.admin))
    term = await _make_term(db_session, academic_year=4104)
    seminar = await _make_seminar(db_session)
    other = await _make_seminar(db_session)  # 未設定のまま

    create = await client.put(
        f"/admin/recruitment-terms/{term.id}/seminars/{seminar.id}",
        json={"capacity": 10, "target_grades": ["B1", "B2"]},
    )
    assert create.status_code == 200
    assert create.json()["capacity"] == 10
    assert create.json()["target_grades"] == ["B1", "B2"]

    update = await client.put(
        f"/admin/recruitment-terms/{term.id}/seminars/{seminar.id}",
        json={"capacity": 5, "target_grades": []},
    )
    assert update.json()["capacity"] == 5
    assert update.json()["target_grades"] == []

    listed = await client.get(f"/admin/recruitment-terms/{term.id}/seminars")
    assert listed.status_code == 200
    by_id = {s["seminar_id"]: s for s in listed.json()}
    assert by_id[str(seminar.id)]["capacity"] == 5
    # 未設定のゼミも一覧に含まれ、値は null
    assert by_id[str(other.id)]["capacity"] is None
    assert by_id[str(other.id)]["target_grades"] is None


async def test_upsert_rejects_unknown_grade(client, db_session) -> None:
    _authenticate_as(await _make_user(db_session, UserRole.admin))
    term = await _make_term(db_session, academic_year=4107)
    seminar = await _make_seminar(db_session)
    resp = await client.put(
        f"/admin/recruitment-terms/{term.id}/seminars/{seminar.id}",
        json={"capacity": 10, "target_grades": ["M1"]},
    )
    assert resp.status_code == 422


async def test_upsert_rejects_negative_capacity(client, db_session) -> None:
    _authenticate_as(await _make_user(db_session, UserRole.admin))
    term = await _make_term(db_session, academic_year=4105)
    seminar = await _make_seminar(db_session)
    resp = await client.put(
        f"/admin/recruitment-terms/{term.id}/seminars/{seminar.id}",
        json={"capacity": -1},
    )
    assert resp.status_code == 422


async def test_upsert_unknown_seminar_is_404(client, db_session) -> None:
    _authenticate_as(await _make_user(db_session, UserRole.admin))
    term = await _make_term(db_session, academic_year=4106)
    resp = await client.put(
        f"/admin/recruitment-terms/{term.id}/seminars/{uuid.uuid4()}",
        json={"capacity": 10, "target_grades": ["B1"]},
    )
    assert resp.status_code == 404


async def test_upsert_requires_target_grades(client, db_session) -> None:
    # このエンドポイントは全置換のため、target_gradesの省略時に暗黙で
    # 閉じる/開くどちらかにフォールバックさせず、明示必須にしている。
    _authenticate_as(await _make_user(db_session, UserRole.admin))
    term = await _make_term(db_session, academic_year=4108)
    seminar = await _make_seminar(db_session)
    resp = await client.put(
        f"/admin/recruitment-terms/{term.id}/seminars/{seminar.id}",
        json={"capacity": 10},
    )
    assert resp.status_code == 422


# --- 認可 ---


async def test_requires_admin_role(client, db_session) -> None:
    _authenticate_as(await _make_user(db_session, UserRole.student))
    resp = await client.get("/admin/recruitment-terms")
    assert resp.status_code == 403


async def test_requires_authentication(client, monkeypatch) -> None:
    monkeypatch.setattr(auth.settings, "auth_dev_mode", False)
    resp = await client.get("/admin/recruitment-terms")
    assert resp.status_code == 401
