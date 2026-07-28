from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base
from api.models.mixins import IDMixin, TimestampMixin


class SheetsExportKey(IDMixin, TimestampMixin, Base):
    """志望理由データのスプレッドシート自動連携(#223)用の専用キー。

    管理者がadmin画面から発行・再発行する(開発者が.envに設定する運用に
    せず、管理者が開発者に頼らず自己完結できるようにするため)。
    常に高々1行しか存在しない想定(再発行のたびに既存行を削除して作り直す)。
    """

    __tablename__ = "sheets_export_keys"

    key: Mapped[str] = mapped_column(String, unique=True)
