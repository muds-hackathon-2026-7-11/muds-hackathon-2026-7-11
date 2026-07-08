import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base
from api.models.mixins import IDMixin, TimestampMixin


class Seminar(IDMixin, TimestampMixin, Base):
    """ゼミ情報。

    定員・募集期間は年度ごとに変わるため seminar_recruitments / recruitment_terms
    へ切り出してある(ここには持たせない)。
    """

    __tablename__ = "seminars"

    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String, nullable=True)
    # ゼミ資料(PDF)から生成したAI用の要約知識。マッチ度診断・相談チャットの
    # 文脈として使う。import_seminar_docs で投入する(未投入なら NULL)。
    knowledge: Mapped[str | None] = mapped_column(Text, nullable=True)


class SeminarTeacher(IDMixin, Base):
    """担当教員（複数対応）"""

    __tablename__ = "seminar_teachers"
    __table_args__ = (
        UniqueConstraint("seminar_id", "teacher_id", name="uq_seminar_teacher"),
    )

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
    """所属ゼミ生（配属結果を兼ねる）。

    ER図上の assignment_results（配属結果）はこのテーブルで代替する。
    所属は募集ラウンド(recruitment_terms)単位で持つ。前期/後期は別termなので、
    同一年度でも前期ゼミA→後期ゼミBのような移動を別レコードで表現できる。
    現在の所属かどうかは term_id が現在アクティブなtermと一致するかで判定する。
    """

    __tablename__ = "seminar_members"
    __table_args__ = (
        UniqueConstraint(
            "seminar_id", "student_id", "term_id", name="uq_seminar_member_term"
        ),
    )

    seminar_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("seminars.id", ondelete="CASCADE")
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    term_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("recruitment_terms.id", ondelete="CASCADE")
    )
