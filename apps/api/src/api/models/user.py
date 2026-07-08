import enum

from sqlalchemy import Boolean, String, Text
from sqlalchemy import Enum as SAEnum
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
    grade: Mapped[str | None] = mapped_column(String, nullable=True)
    # 研究タイトル(#112)。research_theme(長文の概要)とは別に、一覧等で
    # ひと目で分かる短いタイトルを持たせる。
    research_title: Mapped[str | None] = mapped_column(String, nullable=True)
    research_theme: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
