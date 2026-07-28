import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base
from api.models.mixins import CreatedAtMixin, IDMixin


class MatchFeature(str, enum.Enum):
    """どのエンドポイント由来の採点かを区別する(#228)。"""

    reason_match = "reason_match"  # POST /seminars/reason-matches
    matches = "matches"  # GET /seminars/matches
    single_match = "single_match"  # GET /seminars/{id}/match


class MatchLog(IDMixin, CreatedAtMixin, Base):
    """マッチ度診断のLLM入出力ログ(1コール=1レコード)(#228)。

    プロンプト全体は保存しない。入力7,800トークンの約95%は全ユーザー共通の
    ゼミ一覧で、毎回保存すると数百MBに膨らむうえ内容が重複するため、
    学生ごとに変わる query_text と出力だけを持ち、共通部分は bundle_hash と
    prompt_version で識別する。ゼミ資料は docs/seminars/knowledge/ として
    git管理されているので、ハッシュと日時から当時の内容を辿れる。
    """

    __tablename__ = "match_logs"
    __table_args__ = (Index("ix_match_logs_user_created", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    feature: Mapped[MatchFeature] = mapped_column(
        SAEnum(MatchFeature, native_enum=False, length=20, create_constraint=True)
    )
    # 学生ごとに変わる問い合わせ文(志望理由 or 研究概要)。
    query_text: Mapped[str] = mapped_column(Text)
    # 採点対象のゼミ内容セットを識別するハッシュ(routers.match._bundle_hash)。
    # single_match では _input_hash が入る。
    bundle_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String, nullable=True)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    # LLMが返した生のJSON(パース前)。採点のブレを後から検証するために持つ。
    response_json: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)

    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cached_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
