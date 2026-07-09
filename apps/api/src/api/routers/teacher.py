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
    RecruitmentTerm,
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
from api.services import GRADE_OPTIONS, get_current_term

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


async def _all_seminars(db: AsyncSession) -> list[Seminar]:
    result = await db.execute(select(Seminar).order_by(Seminar.name))
    return list(result.scalars().all())


async def _gather_applicants_for_seminars(
    db: AsyncSession, seminars: list[Seminar]
) -> list[SeminarApplicantsOut]:
    """指定したゼミの応募者(現ラウンド・提出済み・在籍)をゼミ別・志望順にまとめる。"""
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
                    User.research_title,
                    User.research_theme,
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
                        RecruitmentTerm.academic_year,
                    )
                    .join(Seminar, SeminarMember.seminar_id == Seminar.id)
                    .join(RecruitmentTerm, SeminarMember.term_id == RecruitmentTerm.id)
                    .where(SeminarMember.student_id.in_(applicant_ids))
                    .order_by(RecruitmentTerm.academic_year.desc())
                )
            ).all()
            for member_student_id, seminar_name, academic_year in member_rows:
                past_by_student.setdefault(member_student_id, []).append(
                    PastSeminarOut(
                        seminar_name=seminar_name, academic_year=academic_year
                    )
                )

        for (
            seminar_id,
            priority,
            reason,
            student_pk,
            student_id,
            name,
            grade,
            research_title,
            research_theme,
        ) in rows:
            by_seminar[seminar_id].append(
                ApplicantOut(
                    student_id=student_id,
                    name=name,
                    grade=grade,
                    priority=priority,
                    reason=reason,
                    research_title=research_title,
                    research_theme=research_theme,
                    past_seminars=past_by_student.get(student_pk, []),
                )
            )

    return [
        SeminarApplicantsOut(
            seminar_id=s.id, seminar_name=s.name, applicants=by_seminar[s.id]
        )
        for s in seminars
    ]


def _applicants_csv_response(
    data: list[SeminarApplicantsOut], *, filename: str
) -> Response:
    buffer = io.StringIO()
    buffer.write("﻿")  # ExcelでUTF-8を正しく開くためのBOM
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "ゼミ",
            "志望順位",
            "学年",
            "学籍番号",
            "氏名",
            "研究タイトル",
            "研究概要",
            "志望理由",
            "前回所属ゼミ",
        ]
    )
    for seminar in data:
        for applicant in seminar.applicants:
            # past_seminarsはacademic_year降順のため、先頭が前回(直近)の所属。
            last_seminar = applicant.past_seminars[0] if applicant.past_seminars else None
            last_seminar_label = (
                f"{last_seminar.seminar_name}({last_seminar.academic_year})"
                if last_seminar is not None
                else ""
            )
            writer.writerow(
                [
                    seminar.seminar_name,
                    applicant.priority,
                    applicant.grade or "",
                    applicant.student_id or "",
                    applicant.name,
                    applicant.research_title or "",
                    applicant.research_theme or "",
                    applicant.reason,
                    last_seminar_label,
                ]
            )

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/applicants", response_model=list[SeminarApplicantsOut])
async def list_applicants(
    teacher: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)
) -> list[SeminarApplicantsOut]:
    """担当ゼミの応募者一覧(ゼミ別・第1〜3志望別)を返す。"""
    seminars = await _teacher_seminars(db, teacher)
    return await _gather_applicants_for_seminars(db, seminars)


@router.get("/applicants.csv")
async def download_applicants_csv(
    teacher: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)
) -> Response:
    """担当ゼミの応募者をCSVで返す(自分の担当ゼミのみ)。"""
    seminars = await _teacher_seminars(db, teacher)
    data = await _gather_applicants_for_seminars(db, seminars)
    return _applicants_csv_response(data, filename="applicants.csv")


@router.get("/applicants/all.csv")
async def download_all_applicants_csv(
    _teacher: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)
) -> Response:
    """全ゼミの応募者をCSVで返す(自分の担当以外も含む全体版、docs/requirements.md参照)。"""
    seminars = await _all_seminars(db)
    data = await _gather_applicants_for_seminars(db, seminars)
    return _applicants_csv_response(data, filename="applicants_all.csv")


@router.patch(
    "/seminars/{seminar_id}/recruitment", response_model=TeacherRecruitmentOut
)
async def set_own_seminar_recruitment(
    seminar_id: uuid.UUID,
    payload: TeacherRecruitmentUpdate,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
) -> TeacherRecruitmentOut:
    """自分の担当ゼミの定員・募集対象学年を現ラウンドに対して設定する。"""
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
            target_grades=(
                payload.target_grades
                if payload.target_grades is not None
                else list(GRADE_OPTIONS)
            ),
        )
        db.add(recruitment)
    else:
        recruitment.capacity = payload.capacity
        if payload.target_grades is not None:
            recruitment.target_grades = list(payload.target_grades)
    await db.flush()

    return TeacherRecruitmentOut(
        seminar_id=seminar_id,
        seminar_name=seminar.name,
        capacity=recruitment.capacity,
        target_grades=recruitment.target_grades,
    )
