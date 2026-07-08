import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import require_role
from api.db import get_db
from api.models import Seminar, SeminarMaterial, SeminarTeacher, User, UserRole
from api.schemas import (
    AdminSeminarCreate,
    AdminSeminarOut,
    AdminSeminarTeacherOut,
    AdminSeminarUpdate,
    AdminTeacherCreate,
    AdminTeacherOut,
    AdminTeacherUpdate,
    AdminUserCreate,
    AdminUserLookupOut,
    AdminUserOut,
    SeminarMaterialCreate,
    SeminarMaterialOut,
)

# 運営(admin)専用。新規の一括投入はCSV(#40/#45)が担うため、ここでは
# CSVでは後から直せない個別の編集・担当(seminar_teachers)の付け外しを扱う。
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_role(UserRole.admin))],
)


# --- ゼミ ---


async def _teachers_by_seminar(
    db: AsyncSession, *, seminar_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[AdminSeminarTeacherOut]]:
    """複数ゼミ分の担当教員を1クエリでまとめて取得する(N+1回避)。"""
    if not seminar_ids:
        return {}

    result = await db.execute(
        select(SeminarTeacher.seminar_id, User)
        .join(User, SeminarTeacher.teacher_id == User.id)
        .where(SeminarTeacher.seminar_id.in_(seminar_ids))
        .order_by(User.name)
    )
    teachers_by_seminar: dict[uuid.UUID, list[AdminSeminarTeacherOut]] = {}
    for seminar_id, teacher in result.all():
        teachers_by_seminar.setdefault(seminar_id, []).append(
            AdminSeminarTeacherOut.model_validate(teacher)
        )
    return teachers_by_seminar


async def _materials_by_seminar(
    db: AsyncSession, *, seminar_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[SeminarMaterialOut]]:
    """複数ゼミ分の紹介資料を1クエリでまとめて取得する(N+1回避)。"""
    if not seminar_ids:
        return {}

    result = await db.execute(
        select(SeminarMaterial).where(SeminarMaterial.seminar_id.in_(seminar_ids))
    )
    materials_by_seminar: dict[uuid.UUID, list[SeminarMaterialOut]] = {}
    for material in result.scalars().all():
        materials_by_seminar.setdefault(material.seminar_id, []).append(
            SeminarMaterialOut.model_validate(material)
        )
    return materials_by_seminar


def _to_seminar_out(
    seminar: Seminar,
    teachers: list[AdminSeminarTeacherOut],
    materials: list[SeminarMaterialOut],
) -> AdminSeminarOut:
    return AdminSeminarOut(
        id=seminar.id,
        name=seminar.name,
        description=seminar.description,
        photo_url=seminar.photo_url,
        teachers=teachers,
        materials=materials,
    )


@router.post("/seminars", response_model=AdminSeminarOut, status_code=201)
async def create_seminar(
    payload: AdminSeminarCreate, db: AsyncSession = Depends(get_db)
) -> AdminSeminarOut:
    """ゼミを1件作成する(一括投入はCSV #40)。"""
    seminar = Seminar(
        name=payload.name,
        description=payload.description,
        photo_url=payload.photo_url,
    )
    db.add(seminar)
    await db.flush()
    return _to_seminar_out(seminar, [], [])


@router.get("/seminars", response_model=list[AdminSeminarOut])
async def list_seminars(db: AsyncSession = Depends(get_db)) -> list[AdminSeminarOut]:
    result = await db.execute(select(Seminar).order_by(Seminar.name))
    seminars = list(result.scalars().all())
    seminar_ids = [s.id for s in seminars]
    teachers_by_seminar = await _teachers_by_seminar(db, seminar_ids=seminar_ids)
    materials_by_seminar = await _materials_by_seminar(db, seminar_ids=seminar_ids)
    return [
        _to_seminar_out(
            s, teachers_by_seminar.get(s.id, []), materials_by_seminar.get(s.id, [])
        )
        for s in seminars
    ]


@router.patch("/seminars/{seminar_id}", response_model=AdminSeminarOut)
async def update_seminar(
    seminar_id: uuid.UUID,
    payload: AdminSeminarUpdate,
    db: AsyncSession = Depends(get_db),
) -> AdminSeminarOut:
    seminar = await db.get(Seminar, seminar_id)
    if seminar is None:
        raise HTTPException(status_code=404, detail="指定されたゼミが見つかりません。")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(seminar, field, value)
    await db.flush()
    teachers_by_seminar = await _teachers_by_seminar(db, seminar_ids=[seminar.id])
    materials_by_seminar = await _materials_by_seminar(db, seminar_ids=[seminar.id])
    return _to_seminar_out(
        seminar,
        teachers_by_seminar.get(seminar.id, []),
        materials_by_seminar.get(seminar.id, []),
    )


@router.delete("/seminars/{seminar_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_seminar(
    seminar_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Response:
    """ゼミを削除する。担当割当・募集設定・所属(seminar_members)・紹介資料もCASCADEで消える。"""
    seminar = await db.get(Seminar, seminar_id)
    if seminar is None:
        raise HTTPException(status_code=404, detail="指定されたゼミが見つかりません。")
    await db.delete(seminar)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- 担当割当 (seminar_teachers) ---


@router.post(
    "/seminars/{seminar_id}/teachers/{teacher_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def assign_teacher(
    seminar_id: uuid.UUID,
    teacher_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """ゼミに担当教員を割り当てる(既に割当済みなら何もしない=べき等)。"""
    seminar = await db.get(Seminar, seminar_id)
    if seminar is None:
        raise HTTPException(status_code=404, detail="指定されたゼミが見つかりません。")
    teacher = await db.get(User, teacher_id)
    if teacher is None or teacher.role != UserRole.teacher:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="指定されたユーザーは教員ではありません。",
        )

    existing = await db.execute(
        select(SeminarTeacher).where(
            SeminarTeacher.seminar_id == seminar_id,
            SeminarTeacher.teacher_id == teacher_id,
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(SeminarTeacher(seminar_id=seminar_id, teacher_id=teacher_id))
        await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/seminars/{seminar_id}/teachers/{teacher_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unassign_teacher(
    seminar_id: uuid.UUID,
    teacher_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """ゼミの担当教員を外す。"""
    result = await db.execute(
        select(SeminarTeacher).where(
            SeminarTeacher.seminar_id == seminar_id,
            SeminarTeacher.teacher_id == teacher_id,
        )
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=404, detail="担当割当が見つかりません。")
    await db.delete(link)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- 紹介資料 (seminar_materials) ---


@router.post(
    "/seminars/{seminar_id}/materials",
    response_model=SeminarMaterialOut,
    status_code=201,
)
async def create_seminar_material(
    seminar_id: uuid.UUID,
    payload: SeminarMaterialCreate,
    db: AsyncSession = Depends(get_db),
) -> SeminarMaterial:
    seminar = await db.get(Seminar, seminar_id)
    if seminar is None:
        raise HTTPException(status_code=404, detail="指定されたゼミが見つかりません。")
    material = SeminarMaterial(
        seminar_id=seminar_id, url=payload.url, type=payload.type
    )
    db.add(material)
    await db.flush()
    return material


@router.delete(
    "/seminars/{seminar_id}/materials/{material_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_seminar_material(
    seminar_id: uuid.UUID,
    material_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    material = await db.get(SeminarMaterial, material_id)
    if material is None or material.seminar_id != seminar_id:
        raise HTTPException(status_code=404, detail="資料が見つかりません。")
    await db.delete(material)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- 教員 ---


@router.post("/teachers", response_model=AdminTeacherOut, status_code=201)
async def create_teacher(
    payload: AdminTeacherCreate, db: AsyncSession = Depends(get_db)
) -> User:
    """教員ユーザーを1名追加する(一括投入はCSV #40)。

    Google OAuth 発行前なので google_id はプレースホルダ(manual|<email>)を入れる。
    本人の初回Googleログイン時に email 一致で自動的に紐付く(auth.py)。
    """
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="このメールアドレスのユーザーは既に存在します。",
        )
    teacher = User(
        google_id=f"manual|{payload.email}",
        email=payload.email,
        name=payload.name,
        role=UserRole.teacher,
        research_title=payload.research_title,
        research_theme=payload.research_theme,
        photo_url=payload.photo_url,
    )
    db.add(teacher)
    await db.flush()
    return teacher


@router.get("/teachers", response_model=list[AdminTeacherOut])
async def list_teachers(db: AsyncSession = Depends(get_db)) -> list[User]:
    """担当割当の候補として教員ユーザー一覧を返す。"""
    result = await db.execute(
        select(User).where(User.role == UserRole.teacher).order_by(User.name)
    )
    return list(result.scalars().all())


@router.patch("/teachers/{teacher_id}", response_model=AdminTeacherOut)
async def update_teacher(
    teacher_id: uuid.UUID,
    payload: AdminTeacherUpdate,
    db: AsyncSession = Depends(get_db),
) -> User:
    """教員情報を編集する(is_active=false で無効化)。新規作成はCSV(#40)。"""
    teacher = await db.get(User, teacher_id)
    if teacher is None or teacher.role != UserRole.teacher:
        raise HTTPException(status_code=404, detail="教員が見つかりません。")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(teacher, field, value)
    await db.flush()
    return teacher


@router.delete("/teachers/{teacher_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_teacher(
    teacher_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Response:
    """教員を「削除」する。answers 等がFK参照するため物理削除はせず、
    is_active=false にするソフトdelete(requirements.md)。無効化済みでも 204。
    """
    teacher = await db.get(User, teacher_id)
    if teacher is None or teacher.role != UserRole.teacher:
        raise HTTPException(status_code=404, detail="教員が見つかりません。")
    teacher.is_active = False
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- 管理者管理(#134) ---
# 管理者は教員とは独立したユーザー(role=admin)として追加・削除する。


@router.get("/admins/lookup", response_model=AdminUserLookupOut)
async def lookup_admin_candidate(
    email: str, db: AsyncSession = Depends(get_db)
) -> User:
    """管理者追加の確認用に、メールアドレスから既存ユーザーを検索する。

    追加前に名前を画面に表示して確認できるようにするための下見。
    実際の追加は create_admin 側で改めて検証する。
    """
    normalized = email.strip().lower()
    result = await db.execute(select(User).where(User.email == normalized))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=404, detail="登録されているユーザーが見つかりません。"
        )
    return user


@router.post("/admins", response_model=AdminUserOut, status_code=201)
async def create_admin(
    payload: AdminUserCreate, db: AsyncSession = Depends(get_db)
) -> User:
    """既存ユーザーを管理者に昇格させる。

    管理者は新規に作らず、既にusers(学生・教員として登録済み)にいる
    ユーザーのroleをadminへ変更する形で追加する(#134)。
    """
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=404, detail="登録されているユーザーが見つかりません。"
        )
    if user.role == UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="既に管理者です。"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効化されたユーザーは管理者にできません。",
        )
    user.role = UserRole.admin
    await db.flush()
    return user


@router.get("/admins", response_model=list[AdminUserOut])
async def list_admins(db: AsyncSession = Depends(get_db)) -> list[User]:
    """管理者ユーザー一覧を返す。"""
    result = await db.execute(
        select(User).where(User.role == UserRole.admin).order_by(User.name)
    )
    return list(result.scalars().all())


@router.delete("/admins/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_admin(
    admin_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
) -> Response:
    """管理者を「削除」する。無効化はせず、role=studentに戻すだけ(#134)。

    自分自身の解除は禁止する。操作できるのは常に他の管理者からのみなので、
    これだけで「誰も管理者を管理できなくなる」ロックアウトを防げる
    (自分自身を解除しない限り、操作者自身は管理者であり続けるため)。
    """
    admin_user = await db.get(User, admin_id)
    if admin_user is None or admin_user.role != UserRole.admin:
        raise HTTPException(status_code=404, detail="管理者が見つかりません。")
    if admin_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="自分自身は解除できません。",
        )
    admin_user.role = UserRole.student
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
