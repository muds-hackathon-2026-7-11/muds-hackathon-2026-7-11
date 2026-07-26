"""add website material type

Revision ID: 35a5327a582a
Revises: 496c24efe3d1
Create Date: 2026-07-27 04:33:14.304795

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "35a5327a582a"
down_revision: Union[str, Sequence[str], None] = "496c24efe3d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# native_enum=Falseで定義したCHECK制約(models/seminar.pyのMaterialType)は
# Alembicのautogenerateが値の追加を検出しないため、手動でCHECK制約を
# 差し替える。制約名"materialtype"はSQLAlchemyがSAEnumのnameから自動生成
# したもの(既存DBの実際の制約名と一致させる)。


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("materialtype", "seminar_materials", type_="check")
    op.create_check_constraint(
        "materialtype",
        "seminar_materials",
        "type IN ('slide', 'pdf', 'video', 'website')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("materialtype", "seminar_materials", type_="check")
    op.create_check_constraint(
        "materialtype",
        "seminar_materials",
        "type IN ('slide', 'pdf', 'video')",
    )
