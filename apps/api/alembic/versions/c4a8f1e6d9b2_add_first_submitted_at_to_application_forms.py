"""add first_submitted_at to application forms

Revision ID: c4a8f1e6d9b2
Revises: b7d4e91a3c5f
Create Date: 2026-08-07 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4a8f1e6d9b2"
down_revision: Union[str, Sequence[str], None] = "b7d4e91a3c5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "application_forms",
        sa.Column("first_submitted_at", sa.DateTime(timezone=True), nullable=True),
    )
    # 既存の提出済みフォームには、現時点のsubmitted_atをそのまま初回提出時刻
    # として補完する(#249)。再提出していない学生は正確な値になり、
    # 再提出済みの学生は最後の再提出時刻という近似値になる(元の初回提出
    # 時刻はそもそも記録されていなかったため、これ以上正確にはできない)。
    op.execute(
        "UPDATE application_forms SET first_submitted_at = submitted_at "
        "WHERE status = 'submitted'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("application_forms", "first_submitted_at")
