import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base
from api.models.mixins import IDMixin, TimestampMixin


class ApplicationStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"


class ApplicationForm(IDMixin, TimestampMixin, Base):
    """提出全体を管理。学生1人×1募集期間(term_id)につき1レコード。

    1年度に複数の募集期間(前期・後期等)を持てるため、同一学生が同一年度内に
    複数レコードを持つこと自体は正常(募集期間ごとに1件)。
    """

    __tablename__ = "application_forms"
    __table_args__ = (
        UniqueConstraint(
            "term_id", "student_id", name="uq_application_form_term_student"
        ),
    )

    term_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("recruitment_terms.id", ondelete="CASCADE")
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        SAEnum(ApplicationStatus, native_enum=False, length=20, create_constraint=True),
        default=ApplicationStatus.draft,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ApplicationChoice(IDMixin, Base):
    """志望内容。1提出につき最大3レコード（priority 1〜3）。

    件数の上限(最大3件)はアプリケーション層でバリデーションする。
    """

    __tablename__ = "application_choices"
    __table_args__ = (
        CheckConstraint("priority BETWEEN 1 AND 3", name="ck_choice_priority_range"),
        UniqueConstraint("application_form_id", "priority", name="uq_choice_priority"),
        UniqueConstraint("application_form_id", "seminar_id", name="uq_choice_seminar"),
    )

    application_form_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("application_forms.id", ondelete="CASCADE")
    )
    seminar_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("seminars.id", ondelete="CASCADE")
    )
    priority: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text)
    match_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    match_feedback: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
