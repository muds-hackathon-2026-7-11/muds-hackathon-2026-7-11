import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Text
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
