"""replace is_recruiting with target_grades

Revision ID: 714ce109f293
Revises: 171bf2f71d97
Create Date: 2026-07-07 19:23:46.294163

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "714ce109f293"
down_revision: Union[str, Sequence[str], None] = "171bf2f71d97"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "seminar_recruitments",
        sa.Column(
            "target_grades",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
    )
    # is_recruiting=True だったゼミは、募集対象学年を絞っていなかった
    # (全学年)ことと同義なので、対応するB1〜B4全てをtarget_gradesに入れる。
    op.execute(
        "UPDATE seminar_recruitments "
        "SET target_grades = ARRAY['B1', 'B2', 'B3', 'B4'] "
        "WHERE is_recruiting = true"
    )
    op.drop_column("seminar_recruitments", "is_recruiting")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "seminar_recruitments",
        sa.Column("is_recruiting", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.execute(
        "UPDATE seminar_recruitments "
        "SET is_recruiting = (array_length(target_grades, 1) IS NOT NULL)"
    )
    op.drop_column("seminar_recruitments", "target_grades")
