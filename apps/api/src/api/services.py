import logging
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import (
    Answer,
    AnswerRequest,
    AnswerRequestStatus,
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

ANSWER_BUTTON_ACTION_ID = "answer_question"


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
            SeminarMember.academic_year == term.academic_year,
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


def _new_question_blocks(question: Question, seminar_name: str) -> list[dict]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":email: *新しい質問が届きました*\n*ゼミ:* {seminar_name}",
            },
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f">{question.content}"},
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "回答する"},
                    "action_id": ANSWER_BUTTON_ACTION_ID,
                    "value": str(question.id),
                }
            ],
        },
    ]


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
    # textはSlackの通知プレビュー・アクセシビリティ表示用のフォールバック
    # (blocksが描画されない場面でもある程度中身が分かるようにする)
    text = f"[{seminar_name}] 新しい質問が届きました: {question.content}"
    blocks = _new_question_blocks(question, seminar_name)

    for candidate in candidates:
        if candidate.slack_user_id is None:
            continue
        try:
            sent = await slack_client.send_dm(
                slack_user_id=candidate.slack_user_id, text=text, blocks=blocks
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


def _answered_update_blocks(
    question: Question, seminar_name: str, answerer_name: str
) -> list[dict]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f":white_check_mark: *回答済みになりました*\n*ゼミ:* {seminar_name}"
                ),
            },
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f">{question.content}"},
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"{answerer_name}さんが回答しました"}
            ],
        },
    ]


def _asker_notification_blocks(
    question: Question, seminar_name: str, answer_content: str
) -> list[dict]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f":speech_balloon: *質問に回答が届きました*\n*ゼミ:* {seminar_name}"
                ),
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*あなたの質問:*\n>{question.content}",
            },
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*回答:*\n>{answer_content}"},
        },
    ]


async def record_answer_and_notify(
    db: AsyncSession,
    slack_client: SlackClient,
    *,
    question: Question,
    answerer: User,
    content: str,
    source: AnswerSource,
    seminar_name: str,
) -> Answer:
    """回答を保存し、他の未回答候補者への通知メッセージを更新し、
    質問者へ回答通知を送る。

    Slack API呼び出しの失敗は個別に握りつぶす(#21のnotify_answer_candidates
    と同じ方針。回答の保存自体は失敗させない)。
    """
    answer = await record_answer(
        db, question=question, user_id=answerer.id, content=content, source=source
    )

    requests_result = await db.execute(
        select(AnswerRequest).where(AnswerRequest.question_id == question.id)
    )
    for answer_request in requests_result.scalars().all():
        if answer_request.user_id == answerer.id:
            answer_request.status = AnswerRequestStatus.answered
            answer_request.responded_at = datetime.now(UTC)
            continue

        if answer_request.status != AnswerRequestStatus.pending:
            continue

        answer_request.status = AnswerRequestStatus.skipped
        answer_request.responded_at = datetime.now(UTC)
        try:
            update_text = (
                f"[{seminar_name}] {answerer.name}さんが回答しました: "
                f"{question.content}"
            )
            await slack_client.update_message(
                channel_id=answer_request.slack_dm_channel_id,
                message_ts=answer_request.slack_message_ts,
                text=update_text,
                blocks=_answered_update_blocks(question, seminar_name, answerer.name),
            )
        except Exception:
            logger.warning(
                "Slackメッセージの更新に失敗しました: question_id=%s, user_id=%s",
                question.id,
                answer_request.user_id,
                exc_info=True,
            )

    asker_result = await db.execute(select(User).where(User.id == question.user_id))
    asker = asker_result.scalar_one_or_none()
    if asker is not None and asker.slack_user_id is not None:
        try:
            await slack_client.send_dm(
                slack_user_id=asker.slack_user_id,
                text=f"[{seminar_name}] 質問に回答が届きました: {content}",
                blocks=_asker_notification_blocks(question, seminar_name, content),
            )
        except Exception:
            logger.warning(
                "質問者への回答通知に失敗しました: question_id=%s",
                question.id,
                exc_info=True,
            )

    await db.flush()
    return answer
