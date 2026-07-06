import csv
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import require_role
from api.db import get_db
from api.models import (
    ApplicationChoice,
    ApplicationForm,
    ApplicationStatus,
    Seminar,
    SeminarMember,
    SeminarRecruitment,
    SeminarTeacher,
    User,
    UserRole,
)
from api.schemas import (
    ApplicantOut,
    PastSeminarOut,
    SeminarApplicantsOut,
    TeacherRecruitmentOut,
    TeacherRecruitmentUpdate,
)
from api.services import get_current_term

router = APIRouter(prefix="/teacher", tags=["teacher"])

# require_role(teacher) は依存として使うと認証済みの teacher(User) を返す。
require_teacher = require_role(UserRole.teacher)


async def _teacher_seminars(db: AsyncSession, teacher: User) -> list[Seminar]:
    result = await db.execute(
        select(Seminar)
        .join(SeminarTeacher, SeminarTeacher.seminar_id == Seminar.id)
        .where(SeminarTeacher.teacher_id == teacher.id)
        .order_by(Seminar.name)
    )
    return list(result.scalars().all())


async def _gather_applicants(
    db: AsyncSession, teacher: User
) -> list[SeminarApplicantsOut]:
    """担当ゼミの応募者(現ラウンド・提出済み・在籍)をゼミ別・志望順にまとめる。"""
    seminars = await _teacher_seminars(db, teacher)
    if not seminars:
        return []
    seminar_ids = [s.id for s in seminars]

    # 応募ゼロのゼミも出せるよう、担当ゼミ全てを初期化しておく。
    by_seminar: dict[uuid.UUID, list[ApplicantOut]] = {sid: [] for sid in seminar_ids}

    term = await get_current_term(db)
    if term is not None:
        rows = (
            await db.execute(
                select(
                    ApplicationChoice.seminar_id,
                    ApplicationChoice.priority,
                    ApplicationChoice.reason,
                    User.id,
                    User.student_id,
                    User.name,
                    User.grade,
                )
                .join(
                    ApplicationForm,
                    ApplicationChoice.application_form_id == ApplicationForm.id,
                )
                .join(User, ApplicationForm.student_id == User.id)
                .where(
                    ApplicationChoice.seminar_id.in_(seminar_ids),
                    ApplicationForm.term_id == term.id,
                    ApplicationForm.status == ApplicationStatus.submitted,
                    User.is_active.is_(True),
                )
                .order_by(ApplicationChoice.priority, User.name)
            )
        ).all()

        # 応募者の「過去の所属ゼミ」をまとめて取得する。
        applicant_ids = list({row[3] for row in rows})
        past_by_student: dict[uuid.UUID, list[PastSeminarOut]] = {}
        if applicant_ids:
            member_rows = (
                await db.execute(
                    select(
                        SeminarMember.student_id,
                        Seminar.name,
                        SeminarMember.academic_year,
                    )
                    .join(Seminar, SeminarMember.seminar_id == Seminar.id)
                    .where(SeminarMember.student_id.in_(applicant_ids))
                    .order_by(SeminarMember.academic_year.desc())
                )
            ).all()
            for member_student_id, seminar_name, academic_year in member_rows:
                past_by_student.setdefault(member_student_id, []).append(
                    PastSeminarOut(
                        seminar_name=seminar_name, academic_year=academic_year
                    )
                )

        for seminar_id, priority, reason, student_pk, student_id, name, grade in rows:
            by_seminar[seminar_id].append(
                ApplicantOut(
                    student_id=student_id,
                    name=name,
                    grade=grade,
                    priority=priority,
                    reason=reason,
                    past_seminars=past_by_student.get(student_pk, []),
                )
            )

    return [
        SeminarApplicantsOut(
            seminar_id=s.id, seminar_name=s.name, applicants=by_seminar[s.id]
        )
        for s in seminars
    ]


@router.get("/applicants", response_model=list[SeminarApplicantsOut])
async def list_applicants(
    teacher: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)
) -> list[SeminarApplicantsOut]:
    """担当ゼミの応募者一覧(ゼミ別・第1〜3志望別)を返す。"""
    return await _gather_applicants(db, teacher)


@router.get("/applicants.csv")
async def download_applicants_csv(
    teacher: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)
) -> Response:
    """担当ゼミの応募者をCSVで返す(自分の担当ゼミのみ)。"""
    data = await _gather_applicants(db, teacher)

    buffer = io.StringIO()
    buffer.write("﻿")  # ExcelでUTF-8を正しく開くためのBOM
    writer = csv.writer(buffer)
    writer.writerow(
        ["ゼミ", "志望順位", "学年", "学籍番号", "氏名", "志望理由", "過去の所属ゼミ"]
    )
    for seminar in data:
        for applicant in seminar.applicants:
            past = "; ".join(
                f"{p.seminar_name}({p.academic_year})" for p in applicant.past_seminars
            )
            writer.writerow(
                [
                    seminar.seminar_name,
                    applicant.priority,
                    applicant.grade or "",
                    applicant.student_id or "",
                    applicant.name,
                    applicant.reason,
                    past,
                ]
            )

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=applicants.csv"},
    )


@router.patch(
    "/seminars/{seminar_id}/recruitment", response_model=TeacherRecruitmentOut
)
async def set_own_seminar_recruitment(
    seminar_id: uuid.UUID,
    payload: TeacherRecruitmentUpdate,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
) -> TeacherRecruitmentOut:
    """自分の担当ゼミの定員・is_recruiting を現ラウンドに対して設定する。"""
    seminar = await db.get(Seminar, seminar_id)
    if seminar is None:
        raise HTTPException(status_code=404, detail="指定されたゼミが見つかりません。")

    link = await db.execute(
        select(SeminarTeacher).where(
            SeminarTeacher.seminar_id == seminar_id,
            SeminarTeacher.teacher_id == teacher.id,
        )
    )
    if link.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="担当していないゼミは操作できません。",
        )

    term = await get_current_term(db)
    if term is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="現在募集中の期間がありません。",
        )

    result = await db.execute(
        select(SeminarRecruitment).where(
            SeminarRecruitment.term_id == term.id,
            SeminarRecruitment.seminar_id == seminar_id,
        )
    )
    recruitment = result.scalar_one_or_none()
    if recruitment is None:
        recruitment = SeminarRecruitment(
            term_id=term.id,
            seminar_id=seminar_id,
            capacity=payload.capacity,
            is_recruiting=(
                payload.is_recruiting if payload.is_recruiting is not None else True
            ),
        )
        db.add(recruitment)
    else:
        recruitment.capacity = payload.capacity
        if payload.is_recruiting is not None:
            recruitment.is_recruiting = payload.is_recruiting
    await db.flush()

    return TeacherRecruitmentOut(
        seminar_id=seminar_id,
        seminar_name=seminar.name,
        capacity=recruitment.capacity,
        is_recruiting=recruitment.is_recruiting,
    )
