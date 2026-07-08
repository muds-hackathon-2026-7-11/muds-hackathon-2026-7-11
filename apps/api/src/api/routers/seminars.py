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
    RecruitmentTerm,
    ResearchTag,
    Seminar,
    SeminarMaterial,
    SeminarMember,
    SeminarRecruitment,
    SeminarTeacher,
    User,
    UserInterestTag,
)
from api.schemas import (
    PriorityCounts,
    ResearchTagOut,
    SeminarDetailOut,
    SeminarMaterialOut,
    SeminarMemberOut,
    SeminarOut,
    SeminarStatsOut,
    TeacherOut,
)
from api.services import current_academic_year, get_current_term

router = APIRouter(prefix="/seminars", tags=["seminars"])


async def _interest_tags_by_user(
    db: AsyncSession, *, user_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[ResearchTagOut]]:
    """複数ユーザー分の興味分野タグを1クエリでまとめて取得する(N+1回避)。"""
    if not user_ids:
        return {}

    result = await db.execute(
        select(UserInterestTag.user_id, ResearchTag)
        .join(ResearchTag, UserInterestTag.tag_id == ResearchTag.id)
        .where(UserInterestTag.user_id.in_(user_ids))
        .order_by(ResearchTag.sort_order)
    )
    tags_by_user: dict[uuid.UUID, list[ResearchTagOut]] = {}
    for user_id, tag in result.all():
        tags_by_user.setdefault(user_id, []).append(ResearchTagOut.model_validate(tag))
    return tags_by_user


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

    # 継続ゼミ生数は募集期間の有無に関わらず「現在の年度」で数える
    # (現在のゼミ生は年間通して見える必要があるため)。
    academic_year = await current_academic_year(db)
    continuing_by_seminar: dict[uuid.UUID, int] = {}
    if academic_year is not None:
        # 所属は term 単位で持つため、term経由で現在年度の所属を数える。
        # 前期/後期など同年度に複数termがある場合の二重計上を避けて学生で重複排除する。
        member_rows = await db.execute(
            select(
                SeminarMember.seminar_id,
                func.count(SeminarMember.student_id.distinct()),
            )
            .join(RecruitmentTerm, SeminarMember.term_id == RecruitmentTerm.id)
            .where(RecruitmentTerm.academic_year == academic_year)
            .group_by(SeminarMember.seminar_id)
        )
        continuing_by_seminar = {sid: cnt for sid, cnt in member_rows.all()}

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
                continuing_count=continuing_by_seminar.get(s.id, 0),
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

    # 継続者数は term is None の分岐前(現在の年度ベース)で算出済みの
    # continuing_by_seminar をそのまま使う。

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
    teacher_users = list(teachers_result.scalars().all())
    teacher_tags = await _interest_tags_by_user(
        db, user_ids=[u.id for u in teacher_users]
    )
    teachers = [
        TeacherOut(
            id=u.id,
            name=u.name,
            photo_url=u.photo_url,
            research_theme=u.research_theme,
            interest_tags=teacher_tags.get(u.id, []),
        )
        for u in teacher_users
    ]

    materials_result = await db.execute(
        select(SeminarMaterial).where(SeminarMaterial.seminar_id == seminar_id)
    )
    materials = [
        SeminarMaterialOut.model_validate(m) for m in materials_result.scalars().all()
    ]

    current_members: list[SeminarMemberOut] = []
    academic_year = await current_academic_year(db)
    if academic_year is not None:
        members_result = await db.execute(
            select(User)
            .join(SeminarMember, SeminarMember.student_id == User.id)
            .join(RecruitmentTerm, SeminarMember.term_id == RecruitmentTerm.id)
            .where(
                SeminarMember.seminar_id == seminar_id,
                RecruitmentTerm.academic_year == academic_year,
            )
            # 学年順(B1→B4)に並べ、同学年内は名前順。gradeは"B1".."B4"の
            # 文字列なので昇順で学年の昇順になる。gradeがNULLの学生は末尾。
            .order_by(User.grade.asc().nulls_last(), User.name)
        )
        # 前期/後期で同一学生が複数termに所属し得るため重複排除する。
        member_users = list({u.id: u for u in members_result.scalars().all()}.values())
        member_tags = await _interest_tags_by_user(
            db, user_ids=[u.id for u in member_users]
        )
        current_members = [
            SeminarMemberOut(
                id=u.id,
                name=u.name,
                grade=u.grade,
                research_theme=u.research_theme,
                interest_tags=member_tags.get(u.id, []),
            )
            for u in member_users
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
