import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import require_role
from api.db import get_db
from api.models import RecruitmentTerm, Seminar, SeminarRecruitment, UserRole
from api.schemas import (
    RecruitmentTermCreate,
    RecruitmentTermOut,
    RecruitmentTermUpdate,
    SeminarRecruitmentOut,
    SeminarRecruitmentUpsert,
)

# 運営(admin)専用。全エンドポイントに require_role(admin) を適用する。
router = APIRouter(
    prefix="/admin/recruitment-terms",
    tags=["admin"],
    dependencies=[Depends(require_role(UserRole.admin))],
)


def _validate_period(starts_at: date, ends_at: date) -> None:
    if starts_at > ends_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="開始日は終了日以前である必要があります。",
        )


@router.post("", response_model=RecruitmentTermOut, status_code=201)
async def create_recruitment_term(
    payload: RecruitmentTermCreate, db: AsyncSession = Depends(get_db)
) -> RecruitmentTerm:
    """募集ラウンドを作成する。同一年度に複数作成できる(前期/後期等)。"""
    _validate_period(payload.starts_at, payload.ends_at)
    term = RecruitmentTerm(
        academic_year=payload.academic_year,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        status=payload.status,
    )
    db.add(term)
    await db.flush()
    return term


@router.get("", response_model=list[RecruitmentTermOut])
async def list_recruitment_terms(
    db: AsyncSession = Depends(get_db),
) -> list[RecruitmentTerm]:
    result = await db.execute(
        select(RecruitmentTerm).order_by(
            RecruitmentTerm.academic_year.desc(), RecruitmentTerm.starts_at
        )
    )
    return list(result.scalars().all())


@router.patch("/{term_id}", response_model=RecruitmentTermOut)
async def update_recruitment_term(
    term_id: uuid.UUID,
    payload: RecruitmentTermUpdate,
    db: AsyncSession = Depends(get_db),
) -> RecruitmentTerm:
    term = await db.get(RecruitmentTerm, term_id)
    if term is None:
        raise HTTPException(status_code=404, detail="募集ラウンドが見つかりません。")

    starts_at = payload.starts_at if payload.starts_at is not None else term.starts_at
    ends_at = payload.ends_at if payload.ends_at is not None else term.ends_at
    _validate_period(starts_at, ends_at)

    if payload.starts_at is not None:
        term.starts_at = payload.starts_at
    if payload.ends_at is not None:
        term.ends_at = payload.ends_at
    if payload.status is not None:
        term.status = payload.status
    await db.flush()
    return term


@router.put("/{term_id}/seminars/{seminar_id}", response_model=SeminarRecruitmentOut)
async def upsert_seminar_recruitment(
    term_id: uuid.UUID,
    seminar_id: uuid.UUID,
    payload: SeminarRecruitmentUpsert,
    db: AsyncSession = Depends(get_db),
) -> SeminarRecruitmentOut:
    """募集ラウンド×ゼミの定員・募集有無を設定する(無ければ作成)。"""
    term = await db.get(RecruitmentTerm, term_id)
    if term is None:
        raise HTTPException(status_code=404, detail="募集ラウンドが見つかりません。")
    seminar = await db.get(Seminar, seminar_id)
    if seminar is None:
        raise HTTPException(status_code=404, detail="指定されたゼミが見つかりません。")

    result = await db.execute(
        select(SeminarRecruitment).where(
            SeminarRecruitment.term_id == term_id,
            SeminarRecruitment.seminar_id == seminar_id,
        )
    )
    recruitment = result.scalar_one_or_none()
    if recruitment is None:
        recruitment = SeminarRecruitment(
            term_id=term_id,
            seminar_id=seminar_id,
            capacity=payload.capacity,
            target_grades=payload.target_grades,
        )
        db.add(recruitment)
    else:
        recruitment.capacity = payload.capacity
        recruitment.target_grades = payload.target_grades
    await db.flush()

    return SeminarRecruitmentOut(
        seminar_id=seminar_id,
        seminar_name=seminar.name,
        capacity=recruitment.capacity,
        target_grades=recruitment.target_grades,
    )


@router.get("/{term_id}/seminars", response_model=list[SeminarRecruitmentOut])
async def list_seminar_recruitments(
    term_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> list[SeminarRecruitmentOut]:
    """募集ラウンドのゼミ別設定を全ゼミ分返す(未設定は null)。"""
    term = await db.get(RecruitmentTerm, term_id)
    if term is None:
        raise HTTPException(status_code=404, detail="募集ラウンドが見つかりません。")

    result = await db.execute(
        select(Seminar, SeminarRecruitment)
        .outerjoin(
            SeminarRecruitment,
            (SeminarRecruitment.seminar_id == Seminar.id)
            & (SeminarRecruitment.term_id == term_id),
        )
        .order_by(Seminar.name)
    )
    return [
        SeminarRecruitmentOut(
            seminar_id=seminar.id,
            seminar_name=seminar.name,
            capacity=recruitment.capacity if recruitment is not None else None,
            target_grades=(
                recruitment.target_grades if recruitment is not None else None
            ),
        )
        for seminar, recruitment in result.all()
    ]
