import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
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
)

logger = logging.getLogger(__name__)

if settings.auth_dev_mode:
    # 本番で誤って有効化した場合に気づけるよう、起動時に警告を出す。
    logger.warning(
        "AUTH_DEV_MODE is ON: JWT検証をスキップしX-Dev-User-Emailで認証します。"
        "ローカル/CI専用の設定です。本番では必ず false にしてください。"
    )

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_app_url],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(seminars.router)
app.include_router(questions.router)
app.include_router(answers.router)
app.include_router(me.router)
app.include_router(users.router)
app.include_router(applications.router)
app.include_router(recruitment.router)
app.include_router(teacher.router)
app.include_router(match.router)
app.include_router(admin.router)
app.include_router(assignments.router)
app.include_router(research_tags.router)
app.include_router(consult.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
