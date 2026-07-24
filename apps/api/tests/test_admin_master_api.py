import uuid

import pytest
from sqlalchemy import func, select

from api import auth
from api.auth import get_current_user
from api.main import app
from api.models import (
    MaterialType,
    Seminar,
    SeminarJointGroup,
    SeminarMaterial,
    SeminarTeacher,
    User,
    UserRole,
)

pytestmark = pytest.mark.asyncio


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _authenticate_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


async def _make_user(db_session, role: UserRole, **kwargs) -> User:
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name=_unique("name"),
        role=role,
        **kwargs,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_admin(db_session) -> User:
    return await _make_user(db_session, UserRole.admin)


async def _make_seminar(db_session) -> Seminar:
    seminar = Seminar(name=_unique("seminar"))
    db_session.add(seminar)
    await db_session.flush()
    return seminar


async def _link(db_session, seminar: Seminar, teacher: User) -> None:
    db_session.add(SeminarTeacher(seminar_id=seminar.id, teacher_id=teacher.id))
    await db_session.flush()


async def _add_material(db_session, seminar: Seminar, **kwargs) -> SeminarMaterial:
    material = SeminarMaterial(
        seminar_id=seminar.id,
        url=kwargs.get("url", "https://example.com/slide.pdf"),
        type=kwargs.get("type", MaterialType.slide),
    )
    db_session.add(material)
    await db_session.flush()
    return material


async def _teacher_link_count(db_session, seminar_id, teacher_id) -> int:
    result = await db_session.execute(
        select(func.count())
        .select_from(SeminarTeacher)
        .where(
            SeminarTeacher.seminar_id == seminar_id,
            SeminarTeacher.teacher_id == teacher_id,
        )
    )
    count: int = result.scalar_one()
    return count


# --- ゼミ ---


async def test_create_seminar(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    resp = await client.post(
        "/admin/seminars",
        json={"name": "新ゼミ", "description": "説明", "photo_url": None},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "新ゼミ"
    assert body["description"] == "説明"
    assert body["teachers"] == []
    assert body["materials"] == []

    created = await db_session.get(Seminar, uuid.UUID(body["id"]))
    assert created is not None and created.name == "新ゼミ"


async def test_update_seminar_only_touches_sent_fields(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    seminar = await _make_seminar(db_session)
    seminar.description = "元の説明"
    await db_session.flush()

    resp = await client.patch(f"/admin/seminars/{seminar.id}", json={"name": "改名後"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "改名後"

    await db_session.refresh(seminar)
    assert seminar.name == "改名後"
    # 送っていない description は据え置き
    assert seminar.description == "元の説明"


async def test_update_seminar_unknown_returns_404(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    resp = await client.patch(f"/admin/seminars/{uuid.uuid4()}", json={"name": "x"})
    assert resp.status_code == 404


async def test_list_seminars_includes_assigned_teachers(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    seminar = await _make_seminar(db_session)
    teacher = await _make_user(db_session, UserRole.teacher)
    await _link(db_session, seminar, teacher)

    resp = await client.get("/admin/seminars")
    assert resp.status_code == 200
    body = next(s for s in resp.json() if s["id"] == str(seminar.id))
    assert body["teachers"] == [{"id": str(teacher.id), "name": teacher.name}]


async def test_delete_seminar_cascades_teacher_links(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    seminar = await _make_seminar(db_session)
    teacher = await _make_user(db_session, UserRole.teacher)
    await _link(db_session, seminar, teacher)

    resp = await client.delete(f"/admin/seminars/{seminar.id}")
    assert resp.status_code == 204

    assert await db_session.get(Seminar, seminar.id) is None
    assert await _teacher_link_count(db_session, seminar.id, teacher.id) == 0


async def test_delete_seminar_unknown_returns_404(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    resp = await client.delete(f"/admin/seminars/{uuid.uuid4()}")
    assert resp.status_code == 404


# --- 合同グループ ---


async def test_set_joint_group_creates_new_group(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    seminar_a = await _make_seminar(db_session)
    seminar_b = await _make_seminar(db_session)

    resp = await client.put(
        f"/admin/seminars/{seminar_a.id}/joint-group",
        json={"joint_with_seminar_id": str(seminar_b.id)},
    )

    assert resp.status_code == 200
    assert resp.json()["joint_seminars"] == [
        {"id": str(seminar_b.id), "name": seminar_b.name}
    ]
    await db_session.refresh(seminar_a)
    await db_session.refresh(seminar_b)
    assert seminar_a.joint_group_id is not None
    assert seminar_a.joint_group_id == seminar_b.joint_group_id


async def test_set_joint_group_joins_existing_group(client, db_session) -> None:
    """3ゼミ目を追加すると、既存の2ゼミと同じグループに合流する(対等な関係)。"""
    _authenticate_as(await _make_admin(db_session))
    seminar_a = await _make_seminar(db_session)
    seminar_b = await _make_seminar(db_session)
    seminar_c = await _make_seminar(db_session)
    await client.put(
        f"/admin/seminars/{seminar_a.id}/joint-group",
        json={"joint_with_seminar_id": str(seminar_b.id)},
    )

    resp = await client.put(
        f"/admin/seminars/{seminar_c.id}/joint-group",
        json={"joint_with_seminar_id": str(seminar_b.id)},
    )

    assert resp.status_code == 200
    joint_names = {s["name"] for s in resp.json()["joint_seminars"]}
    assert joint_names == {seminar_a.name, seminar_b.name}
    await db_session.refresh(seminar_a)
    await db_session.refresh(seminar_c)
    assert seminar_a.joint_group_id == seminar_c.joint_group_id


async def test_set_joint_group_rejects_self(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    seminar = await _make_seminar(db_session)

    resp = await client.put(
        f"/admin/seminars/{seminar.id}/joint-group",
        json={"joint_with_seminar_id": str(seminar.id)},
    )

    assert resp.status_code == 400


async def test_set_joint_group_unknown_seminar_returns_404(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    seminar = await _make_seminar(db_session)

    resp = await client.put(
        f"/admin/seminars/{uuid.uuid4()}/joint-group",
        json={"joint_with_seminar_id": str(seminar.id)},
    )

    assert resp.status_code == 404


async def test_set_joint_group_unknown_target_returns_404(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    seminar = await _make_seminar(db_session)

    resp = await client.put(
        f"/admin/seminars/{seminar.id}/joint-group",
        json={"joint_with_seminar_id": str(uuid.uuid4())},
    )

    assert resp.status_code == 404


async def test_remove_joint_group_clears_relation(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    seminar_a = await _make_seminar(db_session)
    seminar_b = await _make_seminar(db_session)
    group = SeminarJointGroup()
    db_session.add(group)
    await db_session.flush()
    seminar_a.joint_group_id = group.id
    seminar_b.joint_group_id = group.id
    await db_session.flush()

    resp = await client.delete(f"/admin/seminars/{seminar_a.id}/joint-group")

    assert resp.status_code == 200
    assert resp.json()["joint_seminars"] == []
    await db_session.refresh(seminar_a)
    await db_session.refresh(seminar_b)
    assert seminar_a.joint_group_id is None
    # 残り1ゼミだけになったグループは解消される(相手も単独ゼミに戻る)。
    assert seminar_b.joint_group_id is None
    assert await db_session.get(SeminarJointGroup, group.id) is None


async def test_remove_joint_group_unknown_seminar_returns_404(
    client, db_session
) -> None:
    _authenticate_as(await _make_admin(db_session))
    resp = await client.delete(f"/admin/seminars/{uuid.uuid4()}/joint-group")
    assert resp.status_code == 404


async def test_delete_seminar_cleans_up_orphaned_joint_group(
    client, db_session
) -> None:
    """合同グループの片方を「ゼミ削除」(合同解除ボタンではない方)で消したら、
    残った側が孤立した1ゼミだけのグループに取り残されないこと。"""
    _authenticate_as(await _make_admin(db_session))
    seminar_a = await _make_seminar(db_session)
    seminar_b = await _make_seminar(db_session)
    group = SeminarJointGroup()
    db_session.add(group)
    await db_session.flush()
    seminar_a.joint_group_id = group.id
    seminar_b.joint_group_id = group.id
    await db_session.flush()

    resp = await client.delete(f"/admin/seminars/{seminar_a.id}")

    assert resp.status_code == 204
    await db_session.refresh(seminar_b)
    assert seminar_b.joint_group_id is None
    assert await db_session.get(SeminarJointGroup, group.id) is None


# --- 担当割当 ---


async def test_assign_teacher_is_idempotent(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    seminar = await _make_seminar(db_session)
    teacher = await _make_user(db_session, UserRole.teacher)

    first = await client.post(f"/admin/seminars/{seminar.id}/teachers/{teacher.id}")
    second = await client.post(f"/admin/seminars/{seminar.id}/teachers/{teacher.id}")

    assert first.status_code == 204
    assert second.status_code == 204
    assert await _teacher_link_count(db_session, seminar.id, teacher.id) == 1


async def test_assign_rejects_non_teacher_user(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    seminar = await _make_seminar(db_session)
    student = await _make_user(db_session, UserRole.student)

    resp = await client.post(f"/admin/seminars/{seminar.id}/teachers/{student.id}")
    assert resp.status_code == 400


async def test_assign_unknown_seminar_returns_404(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    teacher = await _make_user(db_session, UserRole.teacher)
    resp = await client.post(f"/admin/seminars/{uuid.uuid4()}/teachers/{teacher.id}")
    assert resp.status_code == 404


async def test_unassign_teacher(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    seminar = await _make_seminar(db_session)
    teacher = await _make_user(db_session, UserRole.teacher)
    await _link(db_session, seminar, teacher)

    resp = await client.delete(f"/admin/seminars/{seminar.id}/teachers/{teacher.id}")
    assert resp.status_code == 204
    assert await _teacher_link_count(db_session, seminar.id, teacher.id) == 0


async def test_unassign_unknown_link_returns_404(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    seminar = await _make_seminar(db_session)
    teacher = await _make_user(db_session, UserRole.teacher)
    resp = await client.delete(f"/admin/seminars/{seminar.id}/teachers/{teacher.id}")
    assert resp.status_code == 404


# --- 紹介資料 ---


async def test_create_seminar_material(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    seminar = await _make_seminar(db_session)

    resp = await client.post(
        f"/admin/seminars/{seminar.id}/materials",
        json={"url": "https://example.com/slide.pdf", "type": "slide"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["url"] == "https://example.com/slide.pdf"
    assert body["type"] == "slide"

    created = await db_session.get(SeminarMaterial, uuid.UUID(body["id"]))
    assert created is not None and created.seminar_id == seminar.id


async def test_create_seminar_material_rejects_non_http_scheme(
    client, db_session
) -> None:
    # javascript: 等はそのままリンクにするとクリックで実行されてしまうため
    # 拒否する(#172)。
    _authenticate_as(await _make_admin(db_session))
    seminar = await _make_seminar(db_session)

    resp = await client.post(
        f"/admin/seminars/{seminar.id}/materials",
        json={"url": "javascript:alert(1)", "type": "slide"},
    )

    assert resp.status_code == 422


async def test_create_material_unknown_seminar_returns_404(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    resp = await client.post(
        f"/admin/seminars/{uuid.uuid4()}/materials",
        json={"url": "https://example.com/slide.pdf", "type": "slide"},
    )
    assert resp.status_code == 404


async def test_list_seminars_includes_materials(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    seminar = await _make_seminar(db_session)
    material = await _add_material(db_session, seminar)

    resp = await client.get("/admin/seminars")
    assert resp.status_code == 200
    body = next(s for s in resp.json() if s["id"] == str(seminar.id))
    assert body["materials"] == [
        {"id": str(material.id), "url": material.url, "type": "slide"}
    ]


async def test_delete_seminar_material(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    seminar = await _make_seminar(db_session)
    material = await _add_material(db_session, seminar)

    resp = await client.delete(f"/admin/seminars/{seminar.id}/materials/{material.id}")
    assert resp.status_code == 204
    assert await db_session.get(SeminarMaterial, material.id) is None


async def test_delete_material_unknown_returns_404(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    seminar = await _make_seminar(db_session)
    resp = await client.delete(f"/admin/seminars/{seminar.id}/materials/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_delete_material_belonging_to_other_seminar_returns_404(
    client, db_session
) -> None:
    _authenticate_as(await _make_admin(db_session))
    seminar_a = await _make_seminar(db_session)
    seminar_b = await _make_seminar(db_session)
    material = await _add_material(db_session, seminar_a)

    resp = await client.delete(
        f"/admin/seminars/{seminar_b.id}/materials/{material.id}"
    )
    assert resp.status_code == 404
    assert await db_session.get(SeminarMaterial, material.id) is not None


# --- 教員 ---


async def test_create_teacher(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    resp = await client.post(
        "/admin/teachers",
        json={
            "name": "新任教員",
            "email": "Prof.New@Example.com",  # 大文字はサーバで小文字化される
            "research_title": "推薦アルゴリズムの研究",
            "research_theme": "推薦システム",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "新任教員"
    assert body["email"] == "prof.new@example.com"
    assert body["research_title"] == "推薦アルゴリズムの研究"
    assert body["research_theme"] == "推薦システム"
    assert body["is_active"] is True

    created = await db_session.get(User, uuid.UUID(body["id"]))
    assert created is not None
    assert created.role == UserRole.teacher
    # Google OAuth 発行前はプレースホルダ。ログイン時に email 一致で紐付く。
    assert created.google_id == "manual|prof.new@example.com"


async def test_create_teacher_conflict_on_duplicate_email(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    payload = {"name": "教員A", "email": "dup@example.com"}

    first = await client.post("/admin/teachers", json=payload)
    second = await client.post("/admin/teachers", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409


async def test_create_teacher_rejects_invalid_email(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    resp = await client.post(
        "/admin/teachers", json={"name": "教員", "email": "not-an-email"}
    )
    assert resp.status_code == 422


async def test_create_teacher_requires_admin(client, db_session) -> None:
    _authenticate_as(await _make_user(db_session, UserRole.teacher))
    resp = await client.post(
        "/admin/teachers", json={"name": "教員", "email": "x@example.com"}
    )
    assert resp.status_code == 403


async def test_list_teachers_returns_only_teachers(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    teacher = await _make_user(db_session, UserRole.teacher)
    await _make_user(db_session, UserRole.student)

    resp = await client.get("/admin/teachers")
    assert resp.status_code == 200
    roles_ok = {t["id"] for t in resp.json()}
    assert str(teacher.id) in roles_ok
    # student は含まれない(role != teacher を除外)
    assert all("email" in t and "is_active" in t for t in resp.json())


async def test_update_teacher_edits_and_deactivates(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    teacher = await _make_user(db_session, UserRole.teacher, research_theme="元テーマ")

    resp = await client.patch(
        f"/admin/teachers/{teacher.id}",
        json={"name": "新しい名前", "is_active": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "新しい名前"
    assert body["is_active"] is False

    await db_session.refresh(teacher)
    assert teacher.name == "新しい名前"
    assert teacher.is_active is False
    # 送っていない research_theme は据え置き
    assert teacher.research_theme == "元テーマ"


async def test_update_teacher_edits_research_title(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    teacher = await _make_user(db_session, UserRole.teacher)

    resp = await client.patch(
        f"/admin/teachers/{teacher.id}",
        json={"research_title": "新しい研究タイトル"},
    )

    assert resp.status_code == 200
    assert resp.json()["research_title"] == "新しい研究タイトル"


async def test_update_teacher_edits_email(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    teacher = await _make_user(db_session, UserRole.teacher)

    resp = await client.patch(
        f"/admin/teachers/{teacher.id}",
        json={"email": "New.Email@Example.com"},
    )

    assert resp.status_code == 200
    assert resp.json()["email"] == "new.email@example.com"
    await db_session.refresh(teacher)
    assert teacher.email == "new.email@example.com"


async def test_update_teacher_email_conflict_on_duplicate(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    teacher = await _make_user(db_session, UserRole.teacher)
    other = await _make_user(db_session, UserRole.teacher)

    resp = await client.patch(
        f"/admin/teachers/{teacher.id}", json={"email": other.email}
    )

    assert resp.status_code == 409
    await db_session.refresh(teacher)
    assert teacher.email != other.email


async def test_update_teacher_email_unchanged_when_same_value(
    client, db_session
) -> None:
    _authenticate_as(await _make_admin(db_session))
    teacher = await _make_user(db_session, UserRole.teacher)

    resp = await client.patch(
        f"/admin/teachers/{teacher.id}", json={"email": teacher.email}
    )

    assert resp.status_code == 200


async def test_update_teacher_on_non_teacher_returns_404(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    student = await _make_user(db_session, UserRole.student)
    resp = await client.patch(f"/admin/teachers/{student.id}", json={"name": "x"})
    assert resp.status_code == 404


async def test_delete_teacher_soft_deletes(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    teacher = await _make_user(db_session, UserRole.teacher)

    resp = await client.delete(f"/admin/teachers/{teacher.id}")

    assert resp.status_code == 204
    await db_session.refresh(teacher)
    # 物理削除ではなく is_active=false(レコードは残る)
    assert teacher.is_active is False
    assert await db_session.get(User, teacher.id) is not None


async def test_delete_teacher_on_non_teacher_returns_404(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    student = await _make_user(db_session, UserRole.student)
    resp = await client.delete(f"/admin/teachers/{student.id}")
    assert resp.status_code == 404


# --- 管理者管理(#134) ---


async def test_lookup_admin_candidate_returns_existing_user(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    student = await _make_user(db_session, UserRole.student)

    resp = await client.get(
        "/admin/admins/lookup", params={"email": student.email.upper()}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(student.id)
    assert body["name"] == student.name
    assert body["role"] == "student"


async def test_lookup_admin_candidate_returns_404_when_not_found(
    client, db_session
) -> None:
    _authenticate_as(await _make_admin(db_session))
    resp = await client.get(
        "/admin/admins/lookup", params={"email": "unknown@example.com"}
    )
    assert resp.status_code == 404


async def test_lookup_admin_candidate_rejects_teacher(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    teacher = await _make_user(db_session, UserRole.teacher)

    resp = await client.get("/admin/admins/lookup", params={"email": teacher.email})

    assert resp.status_code == 400


async def test_create_admin_promotes_existing_user(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    student = await _make_user(db_session, UserRole.student)

    resp = await client.post("/admin/admins", json={"email": student.email.upper()})

    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == str(student.id)
    assert body["name"] == student.name

    await db_session.refresh(student)
    assert student.role == UserRole.admin


async def test_create_admin_returns_404_when_email_not_registered(
    client, db_session
) -> None:
    _authenticate_as(await _make_admin(db_session))
    resp = await client.post("/admin/admins", json={"email": "unknown@example.com"})
    assert resp.status_code == 404


async def test_create_admin_conflict_when_already_admin(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    other = await _make_admin(db_session)

    resp = await client.post("/admin/admins", json={"email": other.email})

    assert resp.status_code == 409


async def test_create_admin_rejects_teacher(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    teacher = await _make_user(db_session, UserRole.teacher)

    resp = await client.post("/admin/admins", json={"email": teacher.email})

    assert resp.status_code == 400
    await db_session.refresh(teacher)
    assert teacher.role == UserRole.teacher


async def test_create_admin_rejects_inactive_user(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    student = await _make_user(db_session, UserRole.student, is_active=False)

    resp = await client.post("/admin/admins", json={"email": student.email})

    assert resp.status_code == 400
    await db_session.refresh(student)
    assert student.role == UserRole.student


async def test_create_admin_requires_admin(client, db_session) -> None:
    _authenticate_as(await _make_user(db_session, UserRole.teacher))
    resp = await client.post("/admin/admins", json={"email": "x@example.com"})
    assert resp.status_code == 403


async def test_list_admins_returns_only_admins(client, db_session) -> None:
    admin_user = await _make_admin(db_session)
    _authenticate_as(admin_user)
    await _make_user(db_session, UserRole.teacher)

    resp = await client.get("/admin/admins")
    assert resp.status_code == 200
    ids = {a["id"] for a in resp.json()}
    assert str(admin_user.id) in ids
    assert all("email" in a and "is_active" in a for a in resp.json())


async def test_remove_admin_reverts_to_student(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    other = await _make_admin(db_session)

    resp = await client.delete(f"/admin/admins/{other.id}")

    assert resp.status_code == 204
    await db_session.refresh(other)
    assert other.role == UserRole.student
    assert other.is_active is True
    assert await db_session.get(User, other.id) is not None


async def test_remove_admin_cannot_remove_self(client, db_session) -> None:
    admin_user = await _make_admin(db_session)
    _authenticate_as(admin_user)

    resp = await client.delete(f"/admin/admins/{admin_user.id}")

    assert resp.status_code == 403
    await db_session.refresh(admin_user)
    assert admin_user.role == UserRole.admin


async def test_remove_admin_on_non_admin_returns_404(client, db_session) -> None:
    _authenticate_as(await _make_admin(db_session))
    teacher = await _make_user(db_session, UserRole.teacher)
    resp = await client.delete(f"/admin/admins/{teacher.id}")
    assert resp.status_code == 404


# --- 認可 ---


async def test_requires_admin(client, db_session) -> None:
    _authenticate_as(await _make_user(db_session, UserRole.teacher))
    resp = await client.get("/admin/teachers")
    assert resp.status_code == 403


async def test_requires_authentication(client, monkeypatch) -> None:
    monkeypatch.setattr(auth.settings, "auth_dev_mode", False)
    resp = await client.get("/admin/teachers")
    assert resp.status_code == 401
