import enum
import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base
from api.models.mixins import IDMixin, TimestampMixin


class Seminar(IDMixin, TimestampMixin, Base):
    """ゼミ情報"""

    __tablename__ = "seminars"

    name: Mapped[str] = mapped_column(String)
    capacity: Mapped[int] = mapped_column(Integer)
    recruitment_start: Mapped[date] = mapped_column(Date)
    recruitment_end: Mapped[date] = mapped_column(Date)


class SeminarTeacher(IDMixin, Base):
    """担当教員（複数対応）"""

    __tablename__ = "seminar_teachers"

    seminar_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("seminars.id", ondelete="CASCADE")
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )


class MaterialType(str, enum.Enum):
    slide = "slide"
    pdf = "pdf"
    video = "video"


class SeminarMaterial(IDMixin, Base):
    """ゼミ紹介資料"""

    __tablename__ = "seminar_materials"

    seminar_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("seminars.id", ondelete="CASCADE")
    )
    url: Mapped[str] = mapped_column(String)
    type: Mapped[MaterialType] = mapped_column(
        SAEnum(MaterialType, native_enum=False, length=10, create_constraint=True)
    )


class SeminarMember(IDMixin, Base):
    """現在・過去の所属ゼミ生。

    ER図上の assignment_results（配属結果）はこのテーブルで代替する。
    is_current=True が現在の所属、False が過去の所属（配属履歴）を表す。
    """

    __tablename__ = "seminar_members"

    seminar_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("seminars.id", ondelete="CASCADE")
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    academic_year: Mapped[int] = mapped_column(Integer)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
