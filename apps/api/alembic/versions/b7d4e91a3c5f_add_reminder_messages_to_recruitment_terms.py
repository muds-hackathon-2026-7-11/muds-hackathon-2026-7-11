"""add reminder messages to recruitment terms

Revision ID: b7d4e91a3c5f
Revises: a1c4f7d29e30
Create Date: 2026-08-04 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7d4e91a3c5f"
down_revision: Union[str, Sequence[str], None] = "a1c4f7d29e30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_DEADLINE_DAY_MESSAGE = (
    ":alarm_clock: 本日{ends_at_label}が志望提出の締切です。"
    "まだ提出していない場合はお早めにご提出ください。"
)
DEFAULT_DAY_BEFORE_MESSAGE = (
    ":alarm_clock: 締切まで1日です。志望提出の締切は{ends_at_label}です。"
    "まだ提出していない場合はお早めにご提出ください。"
)
DEFAULT_TWO_DAYS_BEFORE_MESSAGE = (
    ":alarm_clock: 締切まで2日です。志望提出の締切は{ends_at_label}です。"
    "まだ提出していない場合はお早めにご提出ください。"
)


def upgrade() -> None:
    """Upgrade schema."""
    # server_defaultを付けて既存行にも自動でデフォルト値を入れる
    # (NOT NULLだが、admin画面で編集するまでは「未編集」を表すNULLを
    # 持たない設計のため)。
    op.add_column(
        "recruitment_terms",
        sa.Column(
            "deadline_day_message",
            sa.Text(),
            server_default=DEFAULT_DEADLINE_DAY_MESSAGE,
            nullable=False,
        ),
    )
    op.add_column(
        "recruitment_terms",
        sa.Column(
            "day_before_message",
            sa.Text(),
            server_default=DEFAULT_DAY_BEFORE_MESSAGE,
            nullable=False,
        ),
    )
    op.add_column(
        "recruitment_terms",
        sa.Column(
            "two_days_before_message",
            sa.Text(),
            server_default=DEFAULT_TWO_DAYS_BEFORE_MESSAGE,
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("recruitment_terms", "two_days_before_message")
    op.drop_column("recruitment_terms", "day_before_message")
    op.drop_column("recruitment_terms", "deadline_day_message")
