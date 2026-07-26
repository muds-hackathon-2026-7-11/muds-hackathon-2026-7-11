import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base
from api.models.mixins import IDMixin, TimestampMixin


class AiFeature(str, enum.Enum):
    """利用上限を数える単位(#201)。

    マッチ度診断は reason-matches / matches / {id}/match の3エンドポイントが
    あるが、どれも同じLLM採点なので match の1枠を共有する(片方を空けておくと
    上限の抜け道になるため)。
    """

    match = "match"
    consult = "consult"


class AiUsage(IDMixin, TimestampMixin, Base):
    """AI機能(OpenAI呼び出し)の募集期間あたりの利用回数(#201)。

    ユーザー×募集期間×機能で1行。募集期間が変われば別の行になるため、
    新しい募集ラウンドが始まると上限は自動的にリセットされる。
    """

    __tablename__ = "ai_usage_counters"
    __table_args__ = (
        # NULLS NOT DISTINCT (PG15+) が無いと、募集期間外(term_id=NULL)の行が
        # 呼ばれるたびに増殖して上限が機能しなくなる。本番・devとも pg16。
        UniqueConstraint(
            "user_id",
            "term_id",
            "feature",
            name="uq_ai_usage_user_term_feature",
            postgresql_nulls_not_distinct=True,
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    # 募集期間外(get_current_term が None)の利用は NULL の枠でまとめて数える。
    # 1〜2年生が募集開始前に下調べで相談チャットを使うケースがあるため、
    # 期間外でも使えるようにしつつ上限は効かせる。
    term_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("recruitment_terms.id", ondelete="CASCADE"),
        nullable=True,
    )
    feature: Mapped[AiFeature] = mapped_column(
        SAEnum(AiFeature, native_enum=False, length=20, create_constraint=True)
    )
    count: Mapped[int] = mapped_column(Integer, default=0)
