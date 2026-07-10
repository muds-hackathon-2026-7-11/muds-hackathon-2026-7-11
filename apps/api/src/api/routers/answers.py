from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import require_internal_secret
from api.db import get_db
from api.models import AnswerSource, Question, Seminar, User
from api.schemas import AnswerCreate, AnswerOut
from api.services import record_answer_and_notify
from api.slack_client import SlackClient, get_slack_client

router = APIRouter(prefix="/answers", tags=["answers"])


@router.post(
    "",
    response_model=AnswerOut,
    status_code=201,
    dependencies=[Depends(require_internal_secret)],
)
async def create_answer(
    payload: AnswerCreate,
    db: AsyncSession = Depends(get_db),
    slack_client: SlackClient = Depends(get_slack_client),
) -> AnswerOut:
    """Slack Botから回答を投稿する(#33)。

    slack_user_id自体は秘密情報ではなくSlack上で誰でも見えるため、
    require_internal_secretで「Slack Bot経由の呼び出しであること」を
    別途保証する(#170)。
    """
    result = await db.execute(
        select(User).where(User.slack_user_id == payload.slack_user_id)
    )
    answerer = result.scalar_one_or_none()
    if answerer is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "SlackアカウントがWebのユーザー登録と紐づいていません。"
                "先にWebでGoogleログインしてください。"
            ),
        )

    question = await db.get(Question, payload.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="指定された質問が見つかりません。")

    seminar = await db.get(Seminar, question.seminar_id)
    assert seminar is not None

    answer = await record_answer_and_notify(
        db,
        slack_client,
        question=question,
        answerer=answerer,
        content=payload.content,
        source=AnswerSource.slack,
        seminar_name=seminar.name,
    )

    return AnswerOut(
        id=answer.id,
        content=answer.content,
        answerer_name=answerer.name,
        created_at=answer.created_at,
    )
