import logging

from fastapi import FastAPI

from api.config import settings
from api.routers import me, questions, seminars

logger = logging.getLogger(__name__)

if settings.auth_dev_mode:
    # 本番で誤って有効化した場合に気づけるよう、起動時に警告を出す。
    logger.warning(
        "AUTH_DEV_MODE is ON: JWT検証をスキップしX-Dev-User-Emailで認証します。"
        "ローカル/CI専用の設定です。本番では必ず false にしてください。"
    )

app = FastAPI()
app.include_router(seminars.router)
app.include_router(questions.router)
app.include_router(me.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
