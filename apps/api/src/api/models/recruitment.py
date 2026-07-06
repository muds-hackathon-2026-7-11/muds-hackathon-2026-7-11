import enum
import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base
from api.models.mixins import IDMixin, TimestampMixin


class RecruitmentTermStatus(str, enum.Enum):
    preparing = "preparing"
    open = "open"
    closed = "closed"


class RecruitmentTerm(IDMixin, TimestampMixin, Base):
    """募集期間・年度。全ゼミ共通の募集ラウンドを表す。

    1年度に何回募集するか(前期・後期等)は固定せず、運営がUI/APIで
    自由に期間(starts_at/ends_at)を設定できるようにするため、
    academic_yearに一意制約は設けない(同一年度に複数行を許可する)。
    """

    __tablename__ = "recruitment_terms"

    academic_year: Mapped[int] = mapped_column(Integer)
    starts_at: Mapped[date] = mapped_column(Date)
    ends_at: Mapped[date] = mapped_column(Date)
    status: Mapped[RecruitmentTermStatus] = mapped_column(
        SAEnum(
            RecruitmentTermStatus, native_enum=False, length=20, create_constraint=True
        )
    )


class SeminarRecruitment(IDMixin, Base):
    """年度ごとのゼミの募集設定(定員等)。"""

    __tablename__ = "seminar_recruitments"
    __table_args__ = (
        UniqueConstraint("term_id", "seminar_id", name="uq_recruitment_term_seminar"),
    )

    term_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("recruitment_terms.id", ondelete="CASCADE")
    )
    seminar_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("seminars.id", ondelete="CASCADE")
    )
    capacity: Mapped[int] = mapped_column(Integer)
    is_recruiting: Mapped[bool] = mapped_column(Boolean, default=True)
