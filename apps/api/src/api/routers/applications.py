"""志望提出API(取得・下書き保存・提出)。

学生が第1〜第3志望とその理由を、現在アクティブな募集期間
(api.services.get_current_term)に対して下書き保存・提出する。

role=adminであっても実際には在学中の学生であるユーザーがいるため、
/me系エンドポイントはstudentに加えてadminも許可する(常に本人の
データのみを操作するself-serviceなエンドポイントであり、他人の
志望を操作できるわけではないため安全)。
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import require_role
from api.db import get_db
from api.models import (
    ApplicationChoice,
    ApplicationForm,
    ApplicationStatus,
    RecruitmentTerm,
    SeminarRecruitment,
    User,
    UserRole,
)
from api.schemas import (
    ApplicationChoiceIn,
    ApplicationChoiceOut,
    ApplicationFormOut,
    ApplicationUpsertIn,
)
from api.services import get_current_term, normalize_grade

router = APIRouter(prefix="/applications", tags=["applications"])


def _empty_form_out(*, is_editable: bool) -> ApplicationFormOut:
    return ApplicationFormOut(
        id=None,
        status=ApplicationStatus.draft,
        submitted_at=None,
        choices=[],
        is_editable=is_editable,
    )


async def _get_form(
    db: AsyncSession, *, term_id: uuid.UUID, student_id: uuid.UUID
) -> ApplicationForm | None:
    result = await db.execute(
        select(ApplicationForm).where(
            ApplicationForm.term_id == term_id,
            ApplicationForm.student_id == student_id,
        )
    )
    return result.scalar_one_or_none()


async def _get_latest_form(
    db: AsyncSession, *, student_id: uuid.UUID
) -> ApplicationForm | None:
    """学生の直近の提出(募集期間の開始日が最も新しいもの)を返す。

    提出期間外でも「前回何を書いたか」を閲覧だけできるようにするため
    (編集・再提出はできない。is_editable=falseとして返す側で扱う)。
    starts_atが同じ場合はacademic_yearでタイブレークする。
    """
    result = await db.execute(
        select(ApplicationForm)
        .join(RecruitmentTerm, ApplicationForm.term_id == RecruitmentTerm.id)
        .where(ApplicationForm.student_id == student_id)
        .order_by(
            RecruitmentTerm.starts_at.desc(), RecruitmentTerm.academic_year.desc()
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_choices(
    db: AsyncSession, *, form_id: uuid.UUID
) -> list[ApplicationChoice]:
    result = await db.execute(
        select(ApplicationChoice)
        .where(ApplicationChoice.application_form_id == form_id)
        .order_by(ApplicationChoice.priority)
    )
    return list(result.scalars().all())


def _form_out(
    form: ApplicationForm, choices: list[ApplicationChoice], *, is_editable: bool
) -> ApplicationFormOut:
    return ApplicationFormOut(
        id=form.id,
        status=form.status,
        submitted_at=form.submitted_at,
        choices=[ApplicationChoiceOut.model_validate(c) for c in choices],
        is_editable=is_editable,
    )


def _validate_choice_shape(choices: list[ApplicationChoiceIn]) -> None:
    priorities = [c.priority for c in choices]
    if len(priorities) != len(set(priorities)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="志望順位が重複しています。",
        )

    seminar_ids = [c.seminar_id for c in choices]
    if len(seminar_ids) != len(set(seminar_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="同じゼミを複数の志望に登録することはできません。",
        )


async def _validate_recruiting(
    db: AsyncSession,
    *,
    term_id: uuid.UUID,
    seminar_ids: list[uuid.UUID],
    student_grade: str | None,
) -> None:
    if not seminar_ids:
        return

    result = await db.execute(
        select(SeminarRecruitment.seminar_id, SeminarRecruitment.target_grades).where(
            SeminarRecruitment.term_id == term_id,
            SeminarRecruitment.seminar_id.in_(seminar_ids),
        )
    )
    recruiting_ids = {
        seminar_id
        for seminar_id, target_grades in result.all()
        if student_grade is not None and student_grade in target_grades
    }
    if not_recruiting := set(seminar_ids) - recruiting_ids:
        ids_label = ", ".join(str(seminar_id) for seminar_id in sorted(not_recruiting))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"現在募集していないゼミが含まれています: {ids_label}",
        )


async def _require_current_term(db: AsyncSession) -> RecruitmentTerm:
    term = await get_current_term(db)
    if term is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="現在募集中の期間がありません。",
        )
    return term


@router.get("/me", response_model=ApplicationFormOut)
async def get_my_application(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student, UserRole.admin)),
) -> ApplicationFormOut:
    term = await get_current_term(db)
    if term is not None:
        form = await _get_form(db, term_id=term.id, student_id=user.id)
        if form is None:
            return _empty_form_out(is_editable=True)
        choices = await _get_choices(db, form_id=form.id)
        return _form_out(form, choices, is_editable=True)

    # 提出期間外: 編集はできないが、直近の提出内容は閲覧できるようにする
    # (次の募集期間が始まれば、そちらの新しい下書きに切り替わる)。
    latest_form = await _get_latest_form(db, student_id=user.id)
    if latest_form is None:
        return _empty_form_out(is_editable=False)
    choices = await _get_choices(db, form_id=latest_form.id)
    return _form_out(latest_form, choices, is_editable=False)


@router.put("/me", response_model=ApplicationFormOut)
async def upsert_my_application(
    payload: ApplicationUpsertIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student, UserRole.admin)),
) -> ApplicationFormOut:
    term = await _require_current_term(db)
    _validate_choice_shape(payload.choices)
    await _validate_recruiting(
        db,
        term_id=term.id,
        seminar_ids=[c.seminar_id for c in payload.choices],
        student_grade=normalize_grade(user.grade),
    )

    form = await _get_form(db, term_id=term.id, student_id=user.id)
    if form is None:
        form = ApplicationForm(
            term_id=term.id, student_id=user.id, status=ApplicationStatus.draft
        )
        try:
            # 同時に2件のPUTが飛んだ場合の競合(uq_application_form_term_student)
            # をSAVEPOINTで吸収する(api.auth._provision_userと同じパターン)。
            async with db.begin_nested():
                db.add(form)
                await db.flush()
        except IntegrityError:
            form = await _get_form(db, term_id=term.id, student_id=user.id)
            if form is None:
                raise
    else:
        # 提出後(締切前)の上書きは、docs/requirements.mdの通り
        # statusをsubmittedのまま保ち、submitted_atだけ更新する
        # (draftに戻す=取り下げ扱いにはしない。draftはdraftのままでよい)。
        if form.status == ApplicationStatus.submitted:
            form.submitted_at = datetime.now(timezone.utc)

    await db.execute(
        delete(ApplicationChoice).where(
            ApplicationChoice.application_form_id == form.id
        )
    )
    new_choices = [
        ApplicationChoice(
            application_form_id=form.id,
            seminar_id=choice.seminar_id,
            priority=choice.priority,
            reason=choice.reason,
        )
        for choice in payload.choices
    ]
    db.add_all(new_choices)
    await db.flush()

    new_choices.sort(key=lambda c: c.priority)
    return _form_out(form, new_choices, is_editable=True)


@router.post("/me/submit", response_model=ApplicationFormOut)
async def submit_my_application(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student, UserRole.admin)),
) -> ApplicationFormOut:
    term = await _require_current_term(db)

    form = await _get_form(db, term_id=term.id, student_id=user.id)
    if form is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="下書きが存在しません。先に志望を保存してください。",
        )

    choices = await _get_choices(db, form_id=form.id)
    if not choices:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="志望が1件も登録されていません。",
        )
    # 下書き保存後に募集状況が変わっている可能性があるため、提出時にも
    # 募集中のゼミのみであることを再検証する。
    await _validate_recruiting(
        db,
        term_id=term.id,
        seminar_ids=[c.seminar_id for c in choices],
        student_grade=normalize_grade(user.grade),
    )

    form.status = ApplicationStatus.submitted
    form.submitted_at = datetime.now(timezone.utc)
    await db.flush()

    return _form_out(form, choices, is_editable=True)
