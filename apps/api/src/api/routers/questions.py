from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_db
from api.models import Question, Seminar, User
from api.schemas import QuestionCreate, QuestionOut

router = APIRouter(prefix="/questions", tags=["questions"])


@router.post("", response_model=QuestionOut, status_code=201)
async def create_question(
    payload: QuestionCreate, db: AsyncSession = Depends(get_db)
) -> Question:
    result = await db.execute(
        select(User).where(User.slack_user_id == payload.slack_user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "SlackアカウントがWebのユーザー登録と紐づいていません。"
                "先にWebでGoogleログインしてください。"
            ),
        )

    seminar = await db.get(Seminar, payload.seminar_id)
    if seminar is None:
        raise HTTPException(status_code=404, detail="指定されたゼミが見つかりません。")

    question = Question(
        seminar_id=payload.seminar_id,
        user_id=user.id,
        content=payload.content,
    )
    db.add(question)
    await db.flush()
    return question
