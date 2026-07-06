import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user, require_role
from api.db import get_db
from api.models import ResearchTag, User, UserInterestTag, UserRole
from api.schemas import MeOut, MeUpdateIn, ResearchTagOut

router = APIRouter(tags=["auth"])


async def _get_interest_tags(
    db: AsyncSession, *, user_id: uuid.UUID
) -> list[ResearchTag]:
    result = await db.execute(
        select(ResearchTag)
        .join(UserInterestTag, UserInterestTag.tag_id == ResearchTag.id)
        .where(UserInterestTag.user_id == user_id)
        .order_by(ResearchTag.sort_order)
    )
    return list(result.scalars().all())


def _me_out(user: User, tags: list[ResearchTag]) -> MeOut:
    return MeOut(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        student_id=user.student_id,
        grade=user.grade,
        research_theme=user.research_theme,
        interest_tags=[ResearchTagOut.model_validate(tag) for tag in tags],
        slack_user_id=user.slack_user_id,
    )


@router.get("/me", response_model=MeOut)
async def read_me(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MeOut:
    """認証済みユーザー自身の情報を返す。"""
    tags = await _get_interest_tags(db, user_id=user.id)
    return _me_out(user, tags)


@router.patch("/me", response_model=MeOut)
async def update_me(
    payload: MeUpdateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(
        require_role(UserRole.student, UserRole.teacher, UserRole.admin)
    ),
) -> MeOut:
    """本人の研究概要・興味分野タグを更新する。"""
    # 同じタグIDが複数回送られても1件として扱う(順序は維持)。
    tag_ids = list(dict.fromkeys(payload.interest_tag_ids))

    if tag_ids:
        result = await db.execute(
            select(ResearchTag.id).where(ResearchTag.id.in_(tag_ids))
        )
        valid_ids = {row[0] for row in result.all()}
        unknown_ids = set(tag_ids) - valid_ids
        if unknown_ids:
            ids_label = ", ".join(str(tag_id) for tag_id in sorted(unknown_ids))
            raise HTTPException(
                status_code=400,
                detail=f"存在しない研究分野タグが含まれています: {ids_label}",
            )

    user.research_theme = payload.research_theme

    await db.execute(delete(UserInterestTag).where(UserInterestTag.user_id == user.id))
    db.add_all([UserInterestTag(user_id=user.id, tag_id=tag_id) for tag_id in tag_ids])
    await db.flush()

    tags = await _get_interest_tags(db, user_id=user.id)
    return _me_out(user, tags)
