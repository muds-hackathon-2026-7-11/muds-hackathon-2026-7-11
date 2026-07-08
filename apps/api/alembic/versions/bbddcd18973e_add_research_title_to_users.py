"""add research_title to users

Revision ID: bbddcd18973e
Revises: 714ce109f293
Create Date: 2026-07-08 13:33:18.594258

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bbddcd18973e"
down_revision: Union[str, Sequence[str], None] = "714ce109f293"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("research_title", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "research_title")
