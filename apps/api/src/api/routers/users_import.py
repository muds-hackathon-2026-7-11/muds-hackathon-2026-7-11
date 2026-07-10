import csv
import io

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import require_role
from api.db import get_db
from api.import_users import import_rows
from api.models import UserRole
from api.schemas import UserImportResult, UserImportSkip

# 運営(admin)専用。data/README.mdの`make import-users`と同じCSV
# (Slack管理画面のワークスペースメンバー一覧エクスポート)をブラウザから
# アップロードして、学年更新・新入生追加・卒業生の非アクティブ化を行える
# ようにする(#163)。ロジック自体はapi.import_usersに集約し、CLIスクリプト
# (import_users.py)とここで重複させない。
router = APIRouter(
    prefix="/admin/users",
    tags=["admin"],
    dependencies=[Depends(require_role(UserRole.admin))],
)


@router.post("/import", response_model=UserImportResult)
async def upload_users_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> UserImportResult:
    """Slackメンバー一覧CSVをアップロードし、学生データを更新する。

    教員は対象外(管理者画面の「教員・管理者管理」から個別に追加・編集する
    運用のため、api.import_users.import_rowsが取り込み時にスキップする)。

    CSV列: username, email, status, billing-active, has-2fa, has-sso,
    userid, fullname, displayname, expiration-timestamp
    (`make import-users`が読む形式と同じ。api.import_users.parse_fullname
    参照)。
    """
    raw = await file.read()
    text = raw.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))

    summary = await import_rows(db, rows)
    await db.flush()

    return UserImportResult(
        created=summary.created,
        updated=summary.updated,
        deactivated=summary.deactivated,
        skipped=[
            UserImportSkip(row=s.row, email=s.email, reason=s.reason)
            for s in summary.skipped
        ],
    )
