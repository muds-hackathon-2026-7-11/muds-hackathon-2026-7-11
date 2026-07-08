import logging
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

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

# 学年別募集(#99)の対象学年。学部生のみを対象とし、大学院生・guest等は
# 対象外(常に学年別募集ゼミには応募できない)。
GRADE_OPTIONS: tuple[str, ...] = ("B1", "B2", "B3", "B4")

JST = ZoneInfo("Asia/Tokyo")


def normalize_grade(raw: str | None) -> str | None:
    """学年文字列をB1〜B4のいずれかに正規化する(#99)。

    実データのusers.gradeは表記が統一されておらず(例:
    "MIDS/B1"、"M1 guest"、空文字)、そのままでは学年別募集の対象判定に
    使えない。末尾がB1〜B4のいずれかに一致すれば学部生としてその学年に
    含める(例: "MIDS/B1" -> "B1")。M1/M2/D1/guestや空文字はどのB1〜B4にも
    一致しないため、常に学年別募集の対象外(None)として扱う。
    """
    if raw is None:
        return None
    for grade in GRADE_OPTIONS:
        if raw.endswith(grade):
            return grade
    return None


async def get_current_term(db: AsyncSession) -> RecruitmentTerm | None:
    """今アクティブな募集ラウンドを1件返す(なければNone)。

    status=open なだけでなく、starts_at <= today <= ends_at も満たす必要がある。
    運営が翌年度分を準備目的で早めに open にしても、開始日前は「募集中」として
    扱わないようにするため。

    todayはJST基準で計算する(サーバーはUTCで動いているため、date.today()
    だと日付の境界(0時〜9時JST)で管理画面の表示や学生の提出可否とズレる)。
    """
    today = datetime.now(JST).date()
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


async def current_academic_year(db: AsyncSession) -> int | None:
    """「現在の年度」を返す(該当する募集期間が無ければNone)。

    直近に開始済みの募集期間のacademic_yearを返す。get_current_termと違い、
    status=openやends_atは問わない。募集期間が(終了日を含めて)アクティブな
    間だけ「現在のゼミ生」等が見えるのは誤りで(1年のほとんどは募集期間外の
    ため)、志望提出画面同様「新しい募集期間が始まったら切り替わる」形にする。

    ただし以下の2つは「まだ始まっていない」とみなして除外する。除外しないと、
    運営が来年度分のラウンドを配属作業より前倒しで作成しただけで(まだ何の
    配属も行われていない段階なのに)、それが「現在の年度」として扱われ、
    今の在籍ゼミ生が誰も表示されなくなる(実際に発生した不具合)。
    - status=preparing(#93で追加された、開始前の準備段階)
    - starts_atが未来のもの(status=openであっても。運営が翌年度分を
      準備目的で早めにopenにしても、開始日前は「現在」として扱わない。
      get_current_termと同じ考え方)

    todayはJST基準で計算する(サーバーはUTCで動いているため、date.today()
    だと日付の境界(0時〜9時JST)で管理画面の表示や学生の提出可否とズレる)。
    """
    today = datetime.now(JST).date()
    result = await db.execute(
        select(RecruitmentTerm.academic_year)
        .where(
            RecruitmentTerm.status != RecruitmentTermStatus.preparing,
            RecruitmentTerm.starts_at <= today,
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
    academic_year = await current_academic_year(db)
    if academic_year is None:
        return []

    members_result = await db.execute(
        select(User)
        .join(SeminarMember, SeminarMember.student_id == User.id)
        .join(RecruitmentTerm, SeminarMember.term_id == RecruitmentTerm.id)
        .where(
            SeminarMember.seminar_id == seminar_id,
            RecruitmentTerm.academic_year == academic_year,
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
