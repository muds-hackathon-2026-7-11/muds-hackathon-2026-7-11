"""seminar_member by recruitment term

Revision ID: 171bf2f71d97
Revises: 7dc6130962c8
Create Date: 2026-07-06 17:34:34.248134

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "171bf2f71d97"
down_revision: Union[str, Sequence[str], None] = "7dc6130962c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # academic_year → term_id へは自動移行できないため、既存の所属データ(dev/seed)を
    # 一旦削除する。本番の配属データはまだ無く、dev は `make seed` で再投入する。
    op.execute("DELETE FROM seminar_members")
    op.add_column("seminar_members", sa.Column("term_id", sa.UUID(), nullable=False))
    op.drop_constraint(
        op.f("uq_seminar_member_year"), "seminar_members", type_="unique"
    )
    op.create_unique_constraint(
        "uq_seminar_member_term",
        "seminar_members",
        ["seminar_id", "student_id", "term_id"],
    )
    op.create_foreign_key(
        "fk_seminar_member_term",
        "seminar_members",
        "recruitment_terms",
        ["term_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_column("seminar_members", "academic_year")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM seminar_members")
    op.add_column(
        "seminar_members",
        sa.Column("academic_year", sa.INTEGER(), autoincrement=False, nullable=False),
    )
    op.drop_constraint("fk_seminar_member_term", "seminar_members", type_="foreignkey")
    op.drop_constraint("uq_seminar_member_term", "seminar_members", type_="unique")
    op.create_unique_constraint(
        op.f("uq_seminar_member_year"),
        "seminar_members",
        ["seminar_id", "student_id", "academic_year"],
    )
    op.drop_column("seminar_members", "term_id")
