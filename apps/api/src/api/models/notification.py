import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base
from api.models.mixins import CreatedAtMixin, IDMixin


class NotificationType(str, enum.Enum):
    deadline = "deadline"
    answer = "answer"
    application = "application"
    question = "question"


class Notification(IDMixin, CreatedAtMixin, Base):
    """通知履歴"""

    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    type: Mapped[NotificationType] = mapped_column(
        SAEnum(NotificationType, native_enum=False, length=20, create_constraint=True)
    )
    message: Mapped[str] = mapped_column(Text)
    related_type: Mapped[str | None] = mapped_column(String, nullable=True)
    related_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
