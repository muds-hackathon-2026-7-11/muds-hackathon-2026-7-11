"""志望提出API(取得・下書き保存・提出)。

学生が第1〜第3志望とその理由を、現在アクティブな募集期間
(api.services.get_current_term)に対して下書き保存・提出する。
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
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
from api.services import get_current_term

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
    """学生の直近の提出(募集期間を問わず、最も開始日が新しいもの)を返す。

    提出期間外でも「前回何を書いたか」を閲覧だけできるようにするため
    (編集・再提出はできない。is_editable=falseとして返す側で扱う)。
    """
    result = await db.execute(
        select(ApplicationForm)
        .join(RecruitmentTerm, ApplicationForm.term_id == RecruitmentTerm.id)
        .where(ApplicationForm.student_id == student_id)
        .order_by(RecruitmentTerm.starts_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _form_out(
    db: AsyncSession, form: ApplicationForm, *, is_editable: bool
) -> ApplicationFormOut:
    result = await db.execute(
        select(ApplicationChoice)
        .where(ApplicationChoice.application_form_id == form.id)
        .order_by(ApplicationChoice.priority)
    )
    choices = result.scalars().all()
    return ApplicationFormOut(
        id=form.id,
        status=form.status,
        submitted_at=form.submitted_at,
        choices=[ApplicationChoiceOut.model_validate(c) for c in choices],
        is_editable=is_editable,
    )


async def _validate_choices(
    db: AsyncSession, *, term: RecruitmentTerm, choices: list[ApplicationChoiceIn]
) -> None:
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

    if not seminar_ids:
        return

    result = await db.execute(
        select(SeminarRecruitment.seminar_id).where(
            SeminarRecruitment.term_id == term.id,
            SeminarRecruitment.seminar_id.in_(seminar_ids),
            SeminarRecruitment.is_recruiting.is_(True),
        )
    )
    recruiting_ids = {row[0] for row in result.all()}
    if not_recruiting := set(seminar_ids) - recruiting_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"現在募集していないゼミが含まれています: {sorted(not_recruiting)}",
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
    user: User = Depends(require_role(UserRole.student)),
) -> ApplicationFormOut:
    term = await get_current_term(db)
    if term is not None:
        form = await _get_form(db, term_id=term.id, student_id=user.id)
        if form is None:
            return _empty_form_out(is_editable=True)
        return await _form_out(db, form, is_editable=True)

    # 提出期間外: 編集はできないが、直近の提出内容は閲覧できるようにする
    # (次の募集期間が始まれば、そちらの新しい下書きに切り替わる)。
    latest_form = await _get_latest_form(db, student_id=user.id)
    if latest_form is None:
        return _empty_form_out(is_editable=False)
    return await _form_out(db, latest_form, is_editable=False)


@router.put("/me", response_model=ApplicationFormOut)
async def upsert_my_application(
    payload: ApplicationUpsertIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
) -> ApplicationFormOut:
    term = await _require_current_term(db)
    await _validate_choices(db, term=term, choices=payload.choices)

    form = await _get_form(db, term_id=term.id, student_id=user.id)
    if form is None:
        form = ApplicationForm(
            term_id=term.id, student_id=user.id, status=ApplicationStatus.draft
        )
        db.add(form)
        await db.flush()
    else:
        form.status = ApplicationStatus.draft
        await db.execute(
            delete(ApplicationChoice).where(
                ApplicationChoice.application_form_id == form.id
            )
        )

    for choice in payload.choices:
        db.add(
            ApplicationChoice(
                application_form_id=form.id,
                seminar_id=choice.seminar_id,
                priority=choice.priority,
                reason=choice.reason,
            )
        )
    await db.flush()

    return await _form_out(db, form, is_editable=True)


@router.post("/me/submit", response_model=ApplicationFormOut)
async def submit_my_application(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
) -> ApplicationFormOut:
    term = await _require_current_term(db)

    form = await _get_form(db, term_id=term.id, student_id=user.id)
    if form is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="下書きが存在しません。先に志望を保存してください。",
        )

    choice_count = await db.execute(
        select(ApplicationChoice.id).where(
            ApplicationChoice.application_form_id == form.id
        )
    )
    if choice_count.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="志望が1件も登録されていません。",
        )

    form.status = ApplicationStatus.submitted
    form.submitted_at = datetime.now(timezone.utc)
    await db.flush()

    return await _form_out(db, form, is_editable=True)
