import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.db import async_session
from api.routers import (
    admin,
    answers,
    applications,
    assignments,
    consult,
    match,
    me,
    questions,
    recruitment,
    research_tags,
    seminars,
    teacher,
    users,
    users_import,
)
from api.services import JST, send_deadline_reminders
from api.slack_client import get_slack_client

logger = logging.getLogger(__name__)

# アプリ全体のルートロガーにハンドラを設定する。これが無いと、api配下の
# 各モジュールのlogger.info/warning/exception呼び出しがすべて出力先を
# 持たずサイレントに消える(uvicornが構成するのはuvicorn.*系のロガーのみで、
# ルートロガーには手を付けないため)。services/slack-botの__init__.pyでも
# 同じ理由でlogging.basicConfig()を呼んでいる。
logging.basicConfig(level=logging.INFO)

if settings.auth_dev_mode:
    # 本番で誤って有効化した場合に気づけるよう、起動時に警告を出す。
    logger.warning(
        "AUTH_DEV_MODE is ON: JWT検証をスキップしX-Dev-User-Emailで認証します。"
        "ローカル/CI専用の設定です。本番では必ず false にしてください。"
    )


async def _run_deadline_reminders() -> None:
    """締切リマインダー(#153)を1回分実行する。scheduler経由でのみ呼ばれる。

    リクエストの外(ジョブ実行時)なのでget_dbのDI経由ではなく、ここで
    直接セッションを開始・commitする。
    """
    logger.info("締切リマインダーのジョブを開始します")
    async with async_session() as session:
        try:
            await send_deadline_reminders(session, get_slack_client())
            await session.commit()
            logger.info("締切リマインダーのジョブが完了しました")
        except Exception:
            await session.rollback()
            logger.exception("締切リマインダーの実行に失敗しました")


scheduler = AsyncIOScheduler(timezone=JST)
if settings.enable_deadline_reminder_scheduler:
    scheduler.add_job(
        _run_deadline_reminders,
        CronTrigger(hour=12, minute=0, timezone=JST),
        id="deadline_reminders",
    )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    if settings.enable_deadline_reminder_scheduler:
        scheduler.start()
        job = scheduler.get_job("deadline_reminders")
        logger.info(
            "締切リマインダーの次回実行予定: %s", job.next_run_time if job else None
        )
    else:
        # apiコンテナは常時稼働しており、DBに締切が近い募集ラウンドがあると
        # 本物のSlack DMが飛んでしまう。ローカル/CIでは既定でスケジューラ自体を
        # 起動しない(ENABLE_DEADLINE_REMINDER_SCHEDULER=trueで明示的にopt-in)。
        logger.info(
            "ENABLE_DEADLINE_REMINDER_SCHEDULER is OFF: 締切リマインダーの"
            "スケジューラは起動しません(ローカル/CI既定)。"
        )
    try:
        yield
    finally:
        if settings.enable_deadline_reminder_scheduler:
            scheduler.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_app_url],
    allow_methods=["*"],
    allow_headers=["*"],
)
# match.router の GET /seminars/matches(静的パス)を、seminars.router の
# GET /seminars/{seminar_id} に横取りされないよう、match を先に登録する(#118)。
app.include_router(match.router)
app.include_router(seminars.router)
app.include_router(questions.router)
app.include_router(answers.router)
app.include_router(me.router)
app.include_router(users.router)
app.include_router(applications.router)
app.include_router(recruitment.router)
app.include_router(teacher.router)
app.include_router(admin.router)
app.include_router(assignments.router)
app.include_router(users_import.router)
app.include_router(research_tags.router)
app.include_router(consult.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
