import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base
from api.models.mixins import CreatedAtMixin, IDMixin


class ChatLog(IDMixin, CreatedAtMixin, Base):
    """AIゼミ相談アシスタントの会話履歴(1発話=1レコードのappend-only)(#228)。

    requirements.md の Phase2 `chat_logs` に対応。今後の機能改善(プロンプト調整・
    ゼミ資料の過不足の発見)の根拠にするため、実際の入出力を残す。

    学生には「保存される」旨を画面に表示する前提のデータであり、閲覧は運営に
    限る。エクスポート時は user_id を仮名化できる(api.export_llm_logs)。
    """

    __tablename__ = "chat_logs"
    __table_args__ = (
        # 会話単位での取り出しと、直近ログからのセッション判定に使う。
        Index("ix_chat_logs_session", "session_id", "turn_index"),
        Index("ix_chat_logs_user_created", "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    # 一連の会話をまとめる識別子。クライアントは送ってこないのでサーバ側で
    # 決める(api.chat_logging.resolve_session を参照)。
    session_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True))
    # 会話内での順番(0始まり)。
    turn_index: Mapped[int] = mapped_column(Integer, default=0)

    message: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text)
    recommendations: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # --- 分析用のメタデータ(取得できなければNULL) ---
    # モデルを変えたときの効果測定に使う。
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # プロンプトキャッシュ(#205)のヒット量。0が続くならキャッシュが効いていない。
    cached_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # LLM呼び出しが失敗したときの理由。品質分析に使うため成功時と同じ表に残す。
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
