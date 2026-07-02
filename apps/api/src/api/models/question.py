import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base
from api.models.mixins import CreatedAtMixin, IDMixin


class QuestionStatus(str, enum.Enum):
    waiting = "waiting"
    answered = "answered"
    closed = "closed"


class Question(IDMixin, CreatedAtMixin, Base):
    __tablename__ = "questions"

    seminar_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("seminars.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[QuestionStatus] = mapped_column(
        SAEnum(QuestionStatus, native_enum=False, length=20, create_constraint=True),
        default=QuestionStatus.waiting,
    )


class AnswerRequestStatus(str, enum.Enum):
    pending = "pending"
    answered = "answered"
    skipped = "skipped"


class AnswerRequest(IDMixin, CreatedAtMixin, Base):
    """質問投稿時にSlack DMで通知した回答候補者との対応付け。"""

    __tablename__ = "answer_requests"
    __table_args__ = (
        UniqueConstraint("question_id", "user_id", name="uq_answer_request"),
    )

    question_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    slack_dm_channel_id: Mapped[str] = mapped_column(String)
    slack_message_ts: Mapped[str] = mapped_column(String)
    status: Mapped[AnswerRequestStatus] = mapped_column(
        SAEnum(
            AnswerRequestStatus, native_enum=False, length=20, create_constraint=True
        ),
        default=AnswerRequestStatus.pending,
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AnswerSource(str, enum.Enum):
    web = "web"
    slack = "slack"


class Answer(IDMixin, CreatedAtMixin, Base):
    __tablename__ = "answers"

    question_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[AnswerSource] = mapped_column(
        SAEnum(AnswerSource, native_enum=False, length=10, create_constraint=True)
    )
