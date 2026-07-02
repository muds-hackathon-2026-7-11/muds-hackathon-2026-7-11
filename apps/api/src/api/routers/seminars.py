import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_db
from api.models import (
    RecruitmentTerm,
    RecruitmentTermStatus,
    Seminar,
    SeminarMaterial,
    SeminarMember,
    SeminarRecruitment,
    SeminarTeacher,
    User,
)
from api.schemas import (
    SeminarDetailOut,
    SeminarMaterialOut,
    SeminarMemberOut,
    SeminarOut,
    TeacherOut,
)

router = APIRouter(prefix="/seminars", tags=["seminars"])


async def _get_current_term(db: AsyncSession) -> RecruitmentTerm | None:
    """今アクティブな募集ラウンドを1件返す(なければNone)。"""
    result = await db.execute(
        select(RecruitmentTerm)
        .where(RecruitmentTerm.status == RecruitmentTermStatus.open)
        .order_by(RecruitmentTerm.academic_year.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.get("", response_model=list[SeminarOut])
async def list_seminars(db: AsyncSession = Depends(get_db)) -> list[SeminarOut]:
    term = await _get_current_term(db)

    if term is None:
        result = await db.execute(select(Seminar).order_by(Seminar.name))
        return [
            SeminarOut(
                id=s.id,
                name=s.name,
                description=s.description,
                photo_url=s.photo_url,
                capacity=None,
                recruitment_start=None,
                recruitment_end=None,
            )
            for s in result.scalars().all()
        ]

    result = await db.execute(
        select(Seminar, SeminarRecruitment.capacity)
        .outerjoin(
            SeminarRecruitment,
            (SeminarRecruitment.seminar_id == Seminar.id)
            & (SeminarRecruitment.term_id == term.id),
        )
        .order_by(Seminar.name)
    )
    return [
        SeminarOut(
            id=seminar.id,
            name=seminar.name,
            description=seminar.description,
            photo_url=seminar.photo_url,
            capacity=capacity,
            recruitment_start=term.starts_at,
            recruitment_end=term.ends_at,
        )
        for seminar, capacity in result.all()
    ]


@router.get("/{seminar_id}", response_model=SeminarDetailOut)
async def get_seminar(
    seminar_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> SeminarDetailOut:
    seminar = await db.get(Seminar, seminar_id)
    if seminar is None:
        raise HTTPException(status_code=404, detail="指定されたゼミが見つかりません。")

    term = await _get_current_term(db)
    capacity: int | None = None
    if term is not None:
        recruitment_result = await db.execute(
            select(SeminarRecruitment.capacity).where(
                SeminarRecruitment.seminar_id == seminar_id,
                SeminarRecruitment.term_id == term.id,
            )
        )
        capacity = recruitment_result.scalar_one_or_none()

    teachers_result = await db.execute(
        select(User)
        .join(SeminarTeacher, SeminarTeacher.teacher_id == User.id)
        .where(SeminarTeacher.seminar_id == seminar_id)
        .order_by(User.name)
    )
    teachers = [
        TeacherOut(id=u.id, name=u.name, research_theme=u.research_theme)
        for u in teachers_result.scalars().all()
    ]

    materials_result = await db.execute(
        select(SeminarMaterial).where(SeminarMaterial.seminar_id == seminar_id)
    )
    materials = [
        SeminarMaterialOut.model_validate(m) for m in materials_result.scalars().all()
    ]

    current_members: list[SeminarMemberOut] = []
    if term is not None:
        members_result = await db.execute(
            select(User)
            .join(SeminarMember, SeminarMember.student_id == User.id)
            .where(
                SeminarMember.seminar_id == seminar_id,
                SeminarMember.academic_year == term.academic_year,
            )
            .order_by(User.name)
        )
        current_members = [
            SeminarMemberOut(id=u.id, name=u.name, research_theme=u.research_theme)
            for u in members_result.scalars().all()
        ]

    return SeminarDetailOut(
        id=seminar.id,
        name=seminar.name,
        description=seminar.description,
        photo_url=seminar.photo_url,
        capacity=capacity,
        recruitment_start=term.starts_at if term is not None else None,
        recruitment_end=term.ends_at if term is not None else None,
        teachers=teachers,
        materials=materials,
        current_members=current_members,
    )
