import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Answer, AnswerSource, Question, QuestionStatus


async def record_answer(
    session: AsyncSession,
    *,
    question: Question,
    user_id: uuid.UUID,
    content: str,
    source: AnswerSource,
) -> Answer:
    """回答を作成し、質問のstatusをansweredに同期する。

    Answerを追加する場合は必ずこの関数を経由すること。ORMで直接
    `Answer(...)` を作ると、question.statusの同期を書き忘れるミスを
    繰り返しやすい(実際にseed.pyで一度発生した)。
    """
    answer = Answer(
        question_id=question.id,
        user_id=user_id,
        content=content,
        source=source,
    )
    session.add(answer)
    question.status = QuestionStatus.answered
    return answer
