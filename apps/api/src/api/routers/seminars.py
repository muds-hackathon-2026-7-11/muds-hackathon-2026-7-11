import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.db import get_db
from api.models import (
    ApplicationChoice,
    ApplicationForm,
    ApplicationStatus,
    Seminar,
    SeminarMaterial,
    SeminarMember,
    SeminarRecruitment,
    SeminarTeacher,
    User,
)
from api.schemas import (
    PriorityCounts,
    SeminarDetailOut,
    SeminarMaterialOut,
    SeminarMemberOut,
    SeminarOut,
    SeminarStatsOut,
    TeacherOut,
)
from api.services import get_current_term

router = APIRouter(prefix="/seminars", tags=["seminars"])


@router.get("", response_model=list[SeminarOut])
async def list_seminars(db: AsyncSession = Depends(get_db)) -> list[SeminarOut]:
    term = await get_current_term(db)

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


@router.get("/stats", response_model=list[SeminarStatsOut])
async def seminar_stats(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[SeminarStatsOut]:
    """現在の募集ラウンド基準で、ゼミ別の応募状況を集計して返す。

    ルート定義は `/{seminar_id}` より前に置くこと（"stats" がUUIDとして
    解釈されるのを避けるため）。
    """
    seminars = (
        (await db.execute(select(Seminar).order_by(Seminar.name))).scalars().all()
    )
    term = await get_current_term(db)

    if term is None:
        return [
            SeminarStatsOut(
                id=s.id,
                name=s.name,
                capacity=None,
                applicant_count=0,
                priority_counts=PriorityCounts(first=0, second=0, third=0),
                grade_counts={},
                ratio=None,
                continuing_count=0,
            )
            for s in seminars
        ]

    # ゼミごとの定員
    capacity_rows = await db.execute(
        select(SeminarRecruitment.seminar_id, SeminarRecruitment.capacity).where(
            SeminarRecruitment.term_id == term.id
        )
    )
    capacity_by_seminar: dict[uuid.UUID, int] = {
        sid: cap for sid, cap in capacity_rows.all()
    }

    # 志望内容（当該ラウンドの提出済み・在籍学生のみ）
    choice_rows = await db.execute(
        select(ApplicationChoice.seminar_id, ApplicationChoice.priority, User.grade)
        .join(
            ApplicationForm,
            ApplicationChoice.application_form_id == ApplicationForm.id,
        )
        .join(User, ApplicationForm.student_id == User.id)
        .where(
            ApplicationForm.term_id == term.id,
            ApplicationForm.status == ApplicationStatus.submitted,
            User.is_active.is_(True),
        )
    )
    applicant_count: dict[uuid.UUID, int] = {}
    priority_by_seminar: dict[uuid.UUID, dict[int, int]] = {}
    grade_by_seminar: dict[uuid.UUID, dict[str, int]] = {}
    for seminar_id, priority, grade in choice_rows.all():
        applicant_count[seminar_id] = applicant_count.get(seminar_id, 0) + 1
        priorities = priority_by_seminar.setdefault(seminar_id, {1: 0, 2: 0, 3: 0})
        priorities[priority] = priorities.get(priority, 0) + 1
        grades = grade_by_seminar.setdefault(seminar_id, {})
        grade_key = grade or "不明"
        grades[grade_key] = grades.get(grade_key, 0) + 1

    # 継続者（現ラウンドの所属ゼミ生数）
    member_rows = await db.execute(
        select(SeminarMember.seminar_id, func.count())
        .where(SeminarMember.term_id == term.id)
        .group_by(SeminarMember.seminar_id)
    )
    continuing_by_seminar: dict[uuid.UUID, int] = {
        sid: cnt for sid, cnt in member_rows.all()
    }

    stats: list[SeminarStatsOut] = []
    for s in seminars:
        capacity = capacity_by_seminar.get(s.id)
        count = applicant_count.get(s.id, 0)
        ratio = round(count / capacity, 2) if capacity else None
        priorities = priority_by_seminar.get(s.id, {1: 0, 2: 0, 3: 0})
        stats.append(
            SeminarStatsOut(
                id=s.id,
                name=s.name,
                capacity=capacity,
                applicant_count=count,
                priority_counts=PriorityCounts(
                    first=priorities.get(1, 0),
                    second=priorities.get(2, 0),
                    third=priorities.get(3, 0),
                ),
                grade_counts=grade_by_seminar.get(s.id, {}),
                ratio=ratio,
                continuing_count=continuing_by_seminar.get(s.id, 0),
            )
        )
    return stats


@router.get("/{seminar_id}", response_model=SeminarDetailOut)
async def get_seminar(
    seminar_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> SeminarDetailOut:
    seminar = await db.get(Seminar, seminar_id)
    if seminar is None:
        raise HTTPException(status_code=404, detail="指定されたゼミが見つかりません。")

    term = await get_current_term(db)
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
                SeminarMember.term_id == term.id,
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
