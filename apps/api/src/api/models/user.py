import enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base
from api.models.mixins import IDMixin, TimestampMixin


class UserRole(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"


class User(IDMixin, TimestampMixin, Base):
    """学生・教員・運営を管理"""

    __tablename__ = "users"

    google_id: Mapped[str] = mapped_column(String, unique=True)
    slack_user_id: Mapped[str | None] = mapped_column(
        String, unique=True, nullable=True
    )
    email: Mapped[str] = mapped_column(String, unique=True)
    student_id: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, native_enum=False, length=20, create_constraint=True)
    )
    research_theme: Mapped[str | None] = mapped_column(Text, nullable=True)
