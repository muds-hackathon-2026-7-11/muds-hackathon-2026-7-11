import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import require_role
from api.db import get_db
from api.models import Answer, Question, Seminar, User, UserRole
from api.schemas import (
    AnswerOut,
    QuestionCreate,
    QuestionCreateWeb,
    QuestionOut,
    QuestionWithAnswersOut,
)
from api.services import notify_answer_candidates
from api.slack_client import SlackClient, get_slack_client

router = APIRouter(prefix="/questions", tags=["questions"])


@router.post("", response_model=QuestionOut, status_code=201)
async def create_question(
    payload: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    slack_client: SlackClient = Depends(get_slack_client),
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

    await notify_answer_candidates(
        db, slack_client, question=question, seminar_name=seminar.name
    )

    return question


@router.post("/me", response_model=QuestionOut, status_code=201)
async def create_question_web(
    payload: QuestionCreateWeb,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student, UserRole.admin)),
) -> Question:
    """Web(FAQ画面)から質問を投稿する(#141)。

    Slack Bot経由のcreate_question(POST /questions)とは別経路。
    投稿者はWeb認証済みユーザーで特定し、slack_user_idは不要。
    注意: ここではnotify_answer_candidates(Slack通知)を意図的に
    呼ばない。呼び出すとSlack Botの通知が二重に発火しかねないため、
    このエンドポイントを変更する際は呼び出さないことを維持すること。
    """
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


@router.get("", response_model=list[QuestionWithAnswersOut])
async def list_questions(
    seminar_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> list[QuestionWithAnswersOut]:
    seminar = await db.get(Seminar, seminar_id)
    if seminar is None:
        raise HTTPException(status_code=404, detail="指定されたゼミが見つかりません。")

    questions_result = await db.execute(
        select(Question)
        .where(Question.seminar_id == seminar_id)
        .order_by(Question.created_at.desc())
    )
    questions = list(questions_result.scalars().all())

    answers_by_question: dict[uuid.UUID, list[AnswerOut]] = defaultdict(list)
    question_ids = [q.id for q in questions]
    if question_ids:
        answers_result = await db.execute(
            select(Answer, User.name)
            .join(User, Answer.user_id == User.id)
            .where(Answer.question_id.in_(question_ids))
            .order_by(Answer.created_at)
        )
        for answer, answerer_name in answers_result.all():
            answers_by_question[answer.question_id].append(
                AnswerOut(
                    id=answer.id,
                    content=answer.content,
                    answerer_name=answerer_name,
                    created_at=answer.created_at,
                )
            )

    return [
        QuestionWithAnswersOut(
            id=q.id,
            seminar_id=q.seminar_id,
            content=q.content,
            status=q.status,
            created_at=q.created_at,
            answers=answers_by_question.get(q.id, []),
        )
        for q in questions
    ]
