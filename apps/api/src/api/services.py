import logging
import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import (
    Answer,
    AnswerRequest,
    AnswerRequestStatus,
    AnswerSource,
    ApplicationChoice,
    ApplicationForm,
    ApplicationStatus,
    Question,
    QuestionStatus,
    RecruitmentTerm,
    RecruitmentTermStatus,
    Seminar,
    SeminarMember,
    SeminarRecruitment,
    SeminarTeacher,
    User,
    UserRole,
)
from api.slack_client import SlackClient

logger = logging.getLogger(__name__)

ANSWER_BUTTON_ACTION_ID = "answer_question"


def _question_action_buttons(question: Question) -> list[dict]:
    return [
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "回答する"},
                    "action_id": ANSWER_BUTTON_ACTION_ID,
                    "value": str(question.id),
                },
            ],
        },
    ]


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


async def term_targets_grade(
    db: AsyncSession, *, term_id: uuid.UUID, student_grade: str | None
) -> bool:
    """指定の募集期間に、この学年を対象とするゼミが1件でもあるか判定する(#99)。

    どのゼミの対象学年にも入っていない学生は、この募集ラウンドの対象外として
    扱う(マイページで「未提出」ではなく「準備中」を表示し、志望提出自体も
    できないようにする側で使う)。
    """
    if student_grade is None:
        return False
    result = await db.execute(
        select(SeminarRecruitment.target_grades).where(
            SeminarRecruitment.term_id == term_id
        )
    )
    return any(
        student_grade in target_grades for target_grades in result.scalars().all()
    )


async def get_current_term(db: AsyncSession) -> RecruitmentTerm | None:
    """今アクティブな募集ラウンドを1件返す(なければNone)。

    status=open なだけでなく、starts_at <= today <= ends_at も満たす必要がある。
    運営が翌年度分を準備目的で早めに open にしても、開始日前は「募集中」として
    扱わないようにするため。

    募集期間(1ヶ月程度)は「今年度が何年か」とは別の概念。ゼミ生の所属判定
    (current_academic_year)には使わないこと — 募集期間外は常にNoneになる
    ため、それに依存すると質問通知・現在のゼミ生表示が年中止まってしまう。

    todayはJST基準で計算する(サーバーはUTCで動いているため、date.today()
    だと日付の境界(0時〜9時JST)で管理画面の表示や学生の提出可否とズレる)。

    academic_yearが同じopen期間が複数該当する場合(本来運営側で避けるべき
    データだが、実際に発生した)、created_atが最も新しいもの(=最後に
    設定された募集ラウンド)を優先する。starts_atはdate型(日単位)かつ
    運営が手入力する業務上の日付にすぎず、同日開始の複数ラウンドを
    区別できないため使わない。created_atも同一トランザクション内でINSERT
    されると同値になりうる(PostgresのNOW()はトランザクション開始時刻)ため、
    最後にidで機械的なタイブレークを行う(業務的な意味は無いが、最低限
    「同じリクエストのたびに違う結果を返す」ことだけは無くす)。
    """
    today = datetime.now(JST).date()
    result = await db.execute(
        select(RecruitmentTerm)
        .where(
            RecruitmentTerm.status == RecruitmentTermStatus.open,
            RecruitmentTerm.starts_at <= today,
            RecruitmentTerm.ends_at >= today,
        )
        .order_by(
            RecruitmentTerm.academic_year.desc(),
            RecruitmentTerm.created_at.desc(),
            RecruitmentTerm.id.desc(),
        )
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


async def student_has_current_seminar(
    db: AsyncSession, *, student_id: uuid.UUID
) -> bool:
    """現在の年度に所属しているゼミが1件でもあるか(#188)。

    routers/me.pyの_get_current_seminarsと同じ「現在年度のSeminarMemberが
    あるか」の判定だが、こちらは表示用にSeminarの中身までは要らないので
    存在チェックだけの軽量版にしている。
    """
    academic_year = await current_academic_year(db)
    if academic_year is None:
        return False

    result = await db.execute(
        select(SeminarMember.id)
        .join(RecruitmentTerm, SeminarMember.term_id == RecruitmentTerm.id)
        .where(
            SeminarMember.student_id == student_id,
            RecruitmentTerm.academic_year == academic_year,
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def find_answer_candidates(
    db: AsyncSession, *, seminar_id: uuid.UUID, exclude_user_id: uuid.UUID
) -> list[User]:
    """質問への回答候補者(今年度の現役ゼミ生+担当教員)のうち、
    Slack連携済み(slack_user_id設定済み)のユーザーを返す。

    質問者自身(exclude_user_id)は除く。募集期間中かどうかには関係なく、
    年中いつでも通知できるようにする(質問・相談機能は募集期間限定ではない)。
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
            User.is_active.is_(True),
        )
    )
    teachers_result = await db.execute(
        select(User)
        .join(SeminarTeacher, SeminarTeacher.teacher_id == User.id)
        .where(
            SeminarTeacher.seminar_id == seminar_id,
            User.slack_user_id.is_not(None),
            User.id != exclude_user_id,
            User.is_active.is_(True),
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
        *_question_action_buttons(question),
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


def _reply_blocks(answerer_display_name: str, answer_content: str) -> list[dict]:
    """スレッド返信として送る、回答1件分のシンプルな表示。

    親メッセージ(質問本文・ボタン)はそのまま残るので、ここでは
    「誰が」「何を」回答したかだけを示す。
    """
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{answerer_display_name}さんの回答:*\n>{answer_content}",
            },
        },
    ]


def _asker_notification_blocks(
    question: Question,
    seminar_name: str,
    answer_content: str,
    answerer_display_name: str,
) -> list[dict]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f":speech_balloon: *質問に回答が届きました*\n"
                    f"*ゼミ:* {seminar_name}\n"
                    f"*回答者:* {answerer_display_name}"
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

    # 回答者のSlack表示名(「[B3] 氏名」形式)を取得する。DBのUser.nameは
    # まだGoogleログイン連携前で汎用名のことがあるため、Slack側の表示名を
    # 優先する。取得に失敗した場合はUser.nameにフォールバックする。
    answerer_display_name = answerer.name
    if answerer.slack_user_id is not None:
        try:
            answerer_display_name = await slack_client.get_display_name(
                slack_user_id=answerer.slack_user_id
            )
        except Exception:
            logger.warning(
                "回答者の表示名取得に失敗しました: user_id=%s",
                answerer.id,
                exc_info=True,
            )

    requests_result = await db.execute(
        select(AnswerRequest).where(AnswerRequest.question_id == question.id)
    )
    for answer_request in requests_result.scalars().all():
        if answer_request.user_id == answerer.id:
            answer_request.status = AnswerRequestStatus.answered
            answer_request.responded_at = datetime.now(UTC)
            continue

        # statusが既にanswered/skippedでも(=前回別の回答が来た時点で自分は
        # pendingではなくなっていても)、今回の新しい回答は引き続き通知する。
        # ここでのstatus遷移はpending -> skippedの初回だけ行う(一度でも
        # 回答/skip済みの人を巻き戻さない)。
        if answer_request.status == AnswerRequestStatus.pending:
            answer_request.status = AnswerRequestStatus.skipped
            answer_request.responded_at = datetime.now(UTC)

        try:
            reply_text = f"{answerer_display_name}さんの回答: {content}"
            await slack_client.reply_in_thread(
                channel_id=answer_request.slack_dm_channel_id,
                thread_ts=answer_request.slack_message_ts,
                text=reply_text,
                blocks=_reply_blocks(answerer_display_name, content),
            )
        except Exception:
            logger.warning(
                "Slackスレッド返信の送信に失敗しました: question_id=%s, user_id=%s",
                question.id,
                answer_request.user_id,
                exc_info=True,
            )

    asker_result = await db.execute(select(User).where(User.id == question.user_id))
    asker = asker_result.scalar_one_or_none()
    if asker is not None and asker.slack_user_id is not None:
        try:
            asker_text = (
                f"[{seminar_name}] {answerer_display_name}さんから質問に"
                f"回答が届きました: {content}"
            )
            await slack_client.send_dm(
                slack_user_id=asker.slack_user_id,
                text=asker_text,
                blocks=_asker_notification_blocks(
                    question, seminar_name, content, answerer_display_name
                ),
            )
        except Exception:
            logger.warning(
                "質問者への回答通知に失敗しました: question_id=%s",
                question.id,
                exc_info=True,
            )

    await db.flush()
    return answer


def _submission_confirmation_blocks(
    choices: list[ApplicationChoice], seminar_names: dict[uuid.UUID, str]
) -> list[dict]:
    lines = "\n".join(
        f"第{c.priority}志望: {seminar_names.get(c.seminar_id, '不明')}"
        for c in sorted(choices, key=lambda c: c.priority)
    )
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ":white_check_mark: *志望を提出しました*",
            },
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": lines}},
    ]


async def notify_submission(
    db: AsyncSession,
    slack_client: SlackClient,
    *,
    user: User,
    choices: list[ApplicationChoice],
) -> None:
    """志望提出時に、提出した本人へSlackで確認通知を送る(#153)。

    Slack API呼び出しの失敗は他の通知系と同じく個別に握りつぶし、
    提出処理自体を失敗させない。締切前の上書き(再提出)でも都度送ってよい。
    """
    if user.slack_user_id is None or not choices:
        return

    seminar_ids = [c.seminar_id for c in choices]
    result = await db.execute(
        select(Seminar.id, Seminar.name).where(Seminar.id.in_(seminar_ids))
    )
    seminar_names: dict[uuid.UUID, str] = {row.id: row.name for row in result.all()}

    text = "志望を提出しました: " + ", ".join(
        f"第{c.priority}志望 {seminar_names.get(c.seminar_id, '不明')}"
        for c in sorted(choices, key=lambda c: c.priority)
    )
    try:
        await slack_client.send_dm(
            slack_user_id=user.slack_user_id,
            text=text,
            blocks=_submission_confirmation_blocks(choices, seminar_names),
        )
    except Exception:
        logger.warning(
            "提出確認通知の送信に失敗しました: user_id=%s",
            user.id,
            exc_info=True,
        )


async def find_students_without_submission(
    db: AsyncSession, *, term_id: uuid.UUID
) -> list[User]:
    """指定の募集期間で、まだ志望を提出していない学生(Slack連携済み)を返す。

    「提出していない」は、その期間のApplication自体が無い、または
    status=draftのまま(下書き止まり)を含む。role=adminであっても実際には
    在学中の学生であるユーザーがいるため、applications.pyの各エンドポイント
    と同じくstudentに加えてadminも対象にする(role=teacherは対象外)。

    対象学年(target_grades)にも絞る(#153)。募集ラウンドが対象としていない
    学年の学生はそもそも志望を提出できない(マイページで「準備中」表示)ため、
    ここで絞らないと「提出できないのに催促される」リマインダーが届いてしまう。
    """
    target_grades: set[str] = set()
    for grades in (
        await db.execute(
            select(SeminarRecruitment.target_grades).where(
                SeminarRecruitment.term_id == term_id
            )
        )
    ).scalars():
        target_grades.update(grades)
    if not target_grades:
        return []

    submitted_result = await db.execute(
        select(ApplicationForm.student_id).where(
            ApplicationForm.term_id == term_id,
            ApplicationForm.status == ApplicationStatus.submitted,
        )
    )
    submitted_student_ids = {row[0] for row in submitted_result.all()}

    students_result = await db.execute(
        select(User).where(
            User.role.in_([UserRole.student, UserRole.admin]),
            User.is_active.is_(True),
            User.slack_user_id.is_not(None),
        )
    )
    return [
        student
        for student in students_result.scalars().all()
        if student.id not in submitted_student_ids
        and normalize_grade(student.grade) in target_grades
    ]


def _deadline_reminder_text(*, is_deadline_day: bool, ends_at_label: str) -> str:
    suffix = "まだ提出していない場合はお早めにご提出ください。"
    if is_deadline_day:
        return f":alarm_clock: 本日{ends_at_label}が志望提出の締切です。{suffix}"
    return (
        f":alarm_clock: 締切まで1日です。志望提出の締切は{ends_at_label}です。{suffix}"
    )


async def send_deadline_reminders(db: AsyncSession, slack_client: SlackClient) -> None:
    """締切前日・当日の昼12時に、まだ志望を提出していない学生へリマインダーDMを送る(#153)。

    1日1回、締切の前日と当日それぞれの日付にだけ一致する募集期間を対象に
    するため、この関数自体は1日1回の定期実行(main.pyのスケジューラ)を
    前提とする(同じ学生・期間に何度も送らないための重複排除テーブルは
    持たない)。
    """
    today = datetime.now(JST).date()
    result = await db.execute(
        select(RecruitmentTerm).where(
            RecruitmentTerm.status == RecruitmentTermStatus.open
        )
    )
    terms = list(result.scalars().all())

    for term in terms:
        is_deadline_day = term.ends_at == today
        is_day_before = term.ends_at - timedelta(days=1) == today
        if not is_deadline_day and not is_day_before:
            continue

        students = await find_students_without_submission(db, term_id=term.id)
        ends_at_label = term.ends_at.strftime("%Y年%m月%d日")
        text = _deadline_reminder_text(
            is_deadline_day=is_deadline_day, ends_at_label=ends_at_label
        )
        for student in students:
            if student.slack_user_id is None:
                continue
            try:
                await slack_client.send_dm(
                    slack_user_id=student.slack_user_id, text=text
                )
            except Exception:
                logger.warning(
                    "締切リマインダーの送信に失敗しました: term_id=%s, user_id=%s",
                    term.id,
                    student.id,
                    exc_info=True,
                )
