"""merge ai usage counters and sheets export heads

Revision ID: 98f017574d55
Revises: bbde17a5a6be, ee8ff8ae57d1
Create Date: 2026-07-29

マイグレーションのヘッドが2つに分岐していたのを合流させる。スキーマは変えない。

経緯: #201(利用上限)のマイグレーション bbde17a5a6be は作成時のヘッド
496c24efe3d1 を親にしていたが、そのブランチをmainへ追従させないままマージ
したため、その間に入った 35a5327a582a → 307e06bb4aac → ee8ff8ae57d1 の系列と
分岐してしまった。この状態では `alembic upgrade head` が「どちらのヘッドか
指定せよ」で失敗し、CIも本番デプロイも通らない。

既にmainへ入った2本は書き換えず(bbde17a5a6be を適用済みの環境が壊れるため)、
両方を親に持つこの空のリビジョンで合流させる。

再発防止: マイグレーションを含むPRは、マージ直前に main を取り込んで
`uv run alembic heads` が1つだけ返ることを確認すること。
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "98f017574d55"
down_revision: Union[str, Sequence[str], None] = ("bbde17a5a6be", "ee8ff8ae57d1")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. 合流のみでスキーマ変更は無い。"""


def downgrade() -> None:
    """Downgrade schema. 合流のみでスキーマ変更は無い。"""
