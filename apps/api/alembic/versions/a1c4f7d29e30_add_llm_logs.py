"""add llm logs

Revision ID: a1c4f7d29e30
Revises: 307e06bb4aac
Create Date: 2026-07-28

chat_logs にセッション情報と計測値を追加し、マッチ度診断用の match_logs を
新規作成する(#228)。

現行コードは chat_logs へ書き込んでいないが、**過去の実装が保存していた行が
残っている環境がある**(開発DBで11件確認)。そのため session_id / turn_index は
server_default で既存行を埋めてから制約を付ける。既存行は1行ごとに別セッション
(turn_index=0)となり会話単位では束ねられないが、データは失われない。
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c4f7d29e30"
down_revision: Union[str, Sequence[str], None] = "307e06bb4aac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "chat_logs",
        sa.Column(
            "session_id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
    )
    # 既存行(通常は0件)を埋めるためだけのデフォルトなので、付け終わったら外す。
    op.alter_column("chat_logs", "session_id", server_default=None)
    op.add_column(
        "chat_logs",
        sa.Column("turn_index", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("chat_logs", "turn_index", server_default=None)
    op.add_column("chat_logs", sa.Column("model", sa.String(), nullable=True))
    op.add_column("chat_logs", sa.Column("prompt_tokens", sa.Integer(), nullable=True))
    op.add_column(
        "chat_logs", sa.Column("completion_tokens", sa.Integer(), nullable=True)
    )
    op.add_column("chat_logs", sa.Column("cached_tokens", sa.Integer(), nullable=True))
    op.add_column("chat_logs", sa.Column("latency_ms", sa.Integer(), nullable=True))
    op.add_column("chat_logs", sa.Column("error", sa.Text(), nullable=True))
    op.create_index(
        "ix_chat_logs_session", "chat_logs", ["session_id", "turn_index"], unique=False
    )
    op.create_index(
        "ix_chat_logs_user_created",
        "chat_logs",
        ["user_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "match_logs",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "feature",
            sa.Enum(
                "reason_match",
                "matches",
                "single_match",
                name="matchfeature",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("bundle_hash", sa.String(), nullable=True),
        sa.Column("prompt_version", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column(
            "response_json",
            sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("cached_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_match_logs_user_created",
        "match_logs",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_match_logs_user_created", table_name="match_logs")
    op.drop_table("match_logs")

    op.drop_index("ix_chat_logs_user_created", table_name="chat_logs")
    op.drop_index("ix_chat_logs_session", table_name="chat_logs")
    op.drop_column("chat_logs", "error")
    op.drop_column("chat_logs", "latency_ms")
    op.drop_column("chat_logs", "cached_tokens")
    op.drop_column("chat_logs", "completion_tokens")
    op.drop_column("chat_logs", "prompt_tokens")
    op.drop_column("chat_logs", "model")
    op.drop_column("chat_logs", "turn_index")
    op.drop_column("chat_logs", "session_id")
