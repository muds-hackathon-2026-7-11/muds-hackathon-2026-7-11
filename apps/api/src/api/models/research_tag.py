import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base
from api.models.mixins import IDMixin


class ResearchTag(IDMixin, Base):
    """研究分野タグのマスタ(例: 機械学習、画像処理、LLM)。"""

    __tablename__ = "research_tags"

    name: Mapped[str] = mapped_column(String, unique=True)
    # 大分類(例: "AI・機械学習")。選択UIで大分類ごとに見出しを付けて
    # グルーピング表示するために使う。
    category: Mapped[str] = mapped_column(String)
    # 一覧・選択UIでの表示順(大分類→その中の並びの順で手動管理する。
    # 名前順だとローマ字/カタカナ/漢字が混在してわかりにくいため)。
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class UserInterestTag(IDMixin, Base):
    """ユーザー(学生・教員)が自分の研究に設定した興味分野タグ。"""

    __tablename__ = "user_interest_tags"
    __table_args__ = (
        UniqueConstraint("user_id", "tag_id", name="uq_user_interest_tag"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("research_tags.id", ondelete="CASCADE")
    )
