import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import require_role
from api.db import get_db
from api.models import Seminar, SeminarTeacher, User, UserRole
from api.schemas import (
    AdminSeminarCreate,
    AdminSeminarOut,
    AdminSeminarUpdate,
    AdminTeacherCreate,
    AdminTeacherOut,
    AdminTeacherUpdate,
)

# 運営(admin)専用。新規の一括投入はCSV(#40/#45)が担うため、ここでは
# CSVでは後から直せない個別の編集・担当(seminar_teachers)の付け外しを扱う。
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_role(UserRole.admin))],
)


# --- ゼミ ---


@router.post("/seminars", response_model=AdminSeminarOut, status_code=201)
async def create_seminar(
    payload: AdminSeminarCreate, db: AsyncSession = Depends(get_db)
) -> Seminar:
    """ゼミを1件作成する(一括投入はCSV #40)。"""
    seminar = Seminar(
        name=payload.name,
        description=payload.description,
        photo_url=payload.photo_url,
    )
    db.add(seminar)
    await db.flush()
    return seminar


@router.get("/seminars", response_model=list[AdminSeminarOut])
async def list_seminars(db: AsyncSession = Depends(get_db)) -> list[Seminar]:
    result = await db.execute(select(Seminar).order_by(Seminar.name))
    return list(result.scalars().all())


@router.patch("/seminars/{seminar_id}", response_model=AdminSeminarOut)
async def update_seminar(
    seminar_id: uuid.UUID,
    payload: AdminSeminarUpdate,
    db: AsyncSession = Depends(get_db),
) -> Seminar:
    seminar = await db.get(Seminar, seminar_id)
    if seminar is None:
        raise HTTPException(status_code=404, detail="指定されたゼミが見つかりません。")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(seminar, field, value)
    await db.flush()
    return seminar


@router.delete("/seminars/{seminar_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_seminar(
    seminar_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Response:
    """ゼミを削除する。担当割当・募集設定・所属(seminar_members)もCASCADEで消える。"""
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
