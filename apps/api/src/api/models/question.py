import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Text
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


class Answer(IDMixin, CreatedAtMixin, Base):
    __tablename__ = "answers"

    question_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    content: Mapped[str] = mapped_column(Text)
