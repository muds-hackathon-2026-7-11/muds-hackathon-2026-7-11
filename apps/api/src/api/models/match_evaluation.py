import uuid

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base
from api.models.mixins import CreatedAtMixin, IDMixin


class MatchEvaluation(IDMixin, CreatedAtMixin, Base):
    """マッチ度のLLM計算結果キャッシュ。同一入力ハッシュがあれば再計算しない。"""

    __tablename__ = "match_evaluations"
    __table_args__ = (
        Index("ix_match_evaluations_lookup", "user_id", "seminar_id", "input_hash"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    seminar_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("seminars.id", ondelete="CASCADE")
    )
    input_hash: Mapped[str] = mapped_column(String)
    score: Mapped[int] = mapped_column(Integer)
    feedback: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
