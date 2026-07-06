import logging
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import (
    Answer,
    AnswerRequest,
    AnswerSource,
    Question,
    QuestionStatus,
    RecruitmentTerm,
    RecruitmentTermStatus,
    SeminarMember,
    SeminarTeacher,
    User,
)
from api.slack_client import SlackClient

logger = logging.getLogger(__name__)


async def get_current_term(db: AsyncSession) -> RecruitmentTerm | None:
    """今アクティブな募集ラウンドを1件返す(なければNone)。

    status=open なだけでなく、starts_at <= today <= ends_at も満たす必要がある。
    運営が翌年度分を準備目的で早めに open にしても、開始日前は「募集中」として
    扱わないようにするため。
    """
    today = date.today()
    result = await db.execute(
        select(RecruitmentTerm)
        .where(
            RecruitmentTerm.status == RecruitmentTermStatus.open,
            RecruitmentTerm.starts_at <= today,
            RecruitmentTerm.ends_at >= today,
        )
        .order_by(RecruitmentTerm.academic_year.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def find_answer_candidates(
    db: AsyncSession, *, seminar_id: uuid.UUID, exclude_user_id: uuid.UUID
) -> list[User]:
    """質問への回答候補者(今年度の現役ゼミ生+担当教員)のうち、
    Slack連携済み(slack_user_id設定済み)のユーザーを返す。

    質問者自身(exclude_user_id)は除く。
    """
    term = await get_current_term(db)
    if term is None:
        return []

    members_result = await db.execute(
        select(User)
        .join(SeminarMember, SeminarMember.student_id == User.id)
        .where(
            SeminarMember.seminar_id == seminar_id,
            SeminarMember.term_id == term.id,
            User.slack_user_id.is_not(None),
            User.id != exclude_user_id,
        )
    )
    teachers_result = await db.execute(
        select(User)
        .join(SeminarTeacher, SeminarTeacher.teacher_id == User.id)
        .where(
            SeminarTeacher.seminar_id == seminar_id,
            User.slack_user_id.is_not(None),
            User.id != exclude_user_id,
        )
    )

    candidates_by_id = {
        u.id: u
        for u in (*members_result.scalars().all(), *teachers_result.scalars().all())
    }
    return list(candidates_by_id.values())


async def notify_answer_candidates(
    db: AsyncSession,
    slack_client: SlackClient,
    *,
    question: Question,
    seminar_name: str,
) -> None:
    """質問投稿時に、回答候補者へSlack DMで通知し、answer_requestsに記録する。

    Slack API呼び出しの失敗は個別に握りつぶす(1人への送信失敗が他の候補者
    への通知や、質問自体の投稿を巻き込んで失敗させないため)。
    """
    candidates = await find_answer_candidates(
        db, seminar_id=question.seminar_id, exclude_user_id=question.user_id
    )
    text = f"「{seminar_name}」に新しい質問が届きました:\n{question.content}"

    for candidate in candidates:
        if candidate.slack_user_id is None:
            continue
        try:
            sent = await slack_client.send_dm(
                slack_user_id=candidate.slack_user_id, text=text
            )
        except Exception:
            logger.warning(
                "Slack DM送信に失敗しました: question_id=%s, user_id=%s",
                question.id,
                candidate.id,
                exc_info=True,
            )
            continue

        db.add(
            AnswerRequest(
                question_id=question.id,
                user_id=candidate.id,
                slack_dm_channel_id=sent.channel_id,
                slack_message_ts=sent.message_ts,
            )
        )

    await db.flush()


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
    await session.flush()
    return answer
