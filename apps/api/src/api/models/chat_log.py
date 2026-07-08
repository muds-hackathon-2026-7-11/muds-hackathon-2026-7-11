import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base
from api.models.mixins import CreatedAtMixin, IDMixin


class ChatLog(IDMixin, CreatedAtMixin, Base):
    """AIゼミ相談アシスタントの会話履歴(1発話=1レコードのappend-only)。

    requirements.md の Phase2 `chat_logs` に対応。相談チャットの継続や
    後からの振り返り・改善に使う。recommendations はモデルが返した推薦ゼミの
    構造化データ(あれば)を保持する。
    """

    __tablename__ = "chat_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    message: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text)
    recommendations: Mapped[list | None] = mapped_column(JSONB, nullable=True)
