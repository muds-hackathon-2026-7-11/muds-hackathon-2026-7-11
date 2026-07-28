"""expand research tags

Revision ID: 307e06bb4aac
Revises: 35a5327a582a
Create Date: 2026-07-28 12:58:21.533768

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "307e06bb4aac"
down_revision: Union[str, Sequence[str], None] = "35a5327a582a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# 最終的なタグ一覧・表示順(大分類ごとにグルーピングして上から順に表示)。
# 既に運用中のマスタなので、既存タグは名前・IDを変えずに残す(sort_order/
# categoryだけ更新することがある)。「暗号」「認証」だけは新リストで
# 「暗号・認証」1つに統合されているため、upgrade()内で明示的に統合する。
# 「文章解析」も新しい呼び方「テキストマイニング」に改名する(同じIDの
# ままなので、既に提出済みの学生の紐付けはそのまま新しい名前に変わる)。
# 新リストの表現と概念が重なる他の既存タグ(Web開発≒Webアプリ、モバイル
# 開発≒モバイルアプリ、VR/AR≒VR/AR/MR、時系列解析≒時系列・時空間分析、
# データ可視化≒情報可視化)は、既存の表記のままにして新しい表記の方は
# 追加しない。
FINAL_TAGS: list[tuple[str, list[str]]] = [
    (
        "AI・機械学習",
        ["深層学習", "生成AI", "強化学習", "アラインメント・安全性", "解釈可能性"],
    ),
    (
        "自然言語処理",
        [
            "LLM",
            "RAG",
            "対話システム",
            "機械翻訳・要約",
            "テキストマイニング",
            "コーパス構築",
        ],
    ),
    (
        "データ分析",
        ["統計解析", "時系列解析", "データ可視化", "グラフデータ", "知識グラフ"],
    ),
    (
        "データベース",
        [
            "問合せ処理・最適化",
            "トランザクション",
            "索引・データ構造",
            "並列・分散処理",
            "NoSQL",
            "データ統合",
            "知識ベース",
            "データベース",
        ],
    ),
    ("画像・映像", ["画像認識", "映像解析", "画像生成", "医療画像"]),
    ("音声・音響", ["音声認識", "音楽情報処理", "音楽生成", "信号処理"]),
    (
        "HCI・UX",
        [
            "UI/UX",
            "ユーザビリティ",
            "インタラクティブシステム",
            "行動解析",
            "感情・感性",
            "アクセシビリティ",
        ],
    ),
    ("VR・AR", ["VR/AR", "VRコンテンツ制作", "メタバース"]),
    (
        "セキュリティ・プライバシ",
        ["暗号・認証", "プライバシ保護", "ブロックチェーン・Web3"],
    ),
    (
        "Web・アプリ",
        ["Web開発", "モバイル開発", "デスクトップ・組込みアプリ", "ソフトウェア基盤"],
    ),
    ("IoT・組込み", ["センサ", "エッジAI", "デジタルツイン"]),
    ("ロボティクス", ["自律移動", "制御"]),
    ("数理最適化", ["最適化", "組合せ最適化"]),
    ("医療・ヘルスケア", ["医療AI", "ヘルスケア・ウェルビーイング", "ゲノム"]),
    ("都市・モビリティ", ["モビリティ", "スマートシティ", "社会インフラ"]),
    ("環境・防災", ["防災・災害", "地球環境", "資源・エネルギー", "SDGs"]),
    ("社会・メディア", ["計算社会科学", "ソーシャルメディア", "法律"]),
    ("経済・ビジネス", ["金融", "マーケティング", "観光", "農業"]),
    ("教育", ["教育AI", "EdTech", "学習支援", "教育"]),
    ("エンタメ・文化", ["ゲーム", "音楽", "漫画・コミック", "食・レシピ", "スポーツ"]),
]

# ダウングレード時に削除する、このマイグレーションで新規追加したタグ名。
NEW_TAG_NAMES = [
    "アラインメント・安全性",
    "解釈可能性",
    "RAG",
    "対話システム",
    "機械翻訳・要約",
    "コーパス構築",
    "グラフデータ",
    "知識グラフ",
    "問合せ処理・最適化",
    "トランザクション",
    "索引・データ構造",
    "並列・分散処理",
    "NoSQL",
    "データ統合",
    "映像解析",
    "画像生成",
    "音楽生成",
    "信号処理",
    "インタラクティブシステム",
    "行動解析",
    "感情・感性",
    "アクセシビリティ",
    "プライバシ保護",
    "ブロックチェーン・Web3",
    "デスクトップ・組込みアプリ",
    "ソフトウェア基盤",
    "デジタルツイン",
    "ヘルスケア・ウェルビーイング",
    "モビリティ",
    "スマートシティ",
    "社会インフラ",
    "防災・災害",
    "地球環境",
    "資源・エネルギー",
    "SDGs",
    "計算社会科学",
    "ソーシャルメディア",
    "法律",
    "観光",
    "農業",
    "教育AI",
    "EdTech",
    "学習支援",
    "ゲーム",
    "音楽",
    "漫画・コミック",
    "食・レシピ",
    "スポーツ",
]

# 元のカテゴリ(downgrade時に戻す用)。
ORIGINAL_CATEGORY_BY_NAME = {
    "暗号・認証": "セキュリティ",
    "医療AI": "バイオ・医療",
    "ゲノム": "バイオ・医療",
    "金融": "社会・経済",
    "マーケティング": "社会・経済",
    "教育": "社会・経済",
}

research_tags = sa.table(
    "research_tags",
    sa.column("id", sa.UUID()),
    sa.column("name", sa.String()),
    sa.column("category", sa.String()),
    sa.column("sort_order", sa.Integer()),
)


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()

    # 「暗号」「認証」を新リストの「暗号・認証」1つに統合する。
    # 「暗号」のIDをそのまま使って改名し、「認証」を選んでいた学生の
    # 紐付けは「暗号・認証」に付け替えてから「認証」自体を削除する。
    conn.execute(
        sa.text(
            "UPDATE research_tags "
            "SET name = '暗号・認証', category = 'セキュリティ・プライバシ' "
            "WHERE name = '暗号'"
        )
    )
    conn.execute(
        sa.text(
            "INSERT INTO user_interest_tags (id, user_id, tag_id) "
            "SELECT gen_random_uuid(), uit.user_id, "
            "  (SELECT id FROM research_tags WHERE name = '暗号・認証') "
            "FROM user_interest_tags uit "
            "WHERE uit.tag_id = (SELECT id FROM research_tags WHERE name = '認証') "
            "ON CONFLICT (user_id, tag_id) DO NOTHING"
        )
    )
    conn.execute(
        sa.text(
            "DELETE FROM user_interest_tags WHERE tag_id = "
            "(SELECT id FROM research_tags WHERE name = '認証')"
        )
    )
    conn.execute(sa.text("DELETE FROM research_tags WHERE name = '認証'"))

    # 「文章解析」を「テキストマイニング」に改名する(同じIDのまま名前だけ
    # 変わるので、既に選んでいた学生の紐付けはそのまま引き継がれる)。
    conn.execute(
        sa.text(
            "UPDATE research_tags SET name = 'テキストマイニング' "
            "WHERE name = '文章解析'"
        )
    )

    existing_names = set(
        conn.execute(sa.text("SELECT name FROM research_tags")).scalars().all()
    )

    new_rows = []
    sort_order = 0
    for category, names in FINAL_TAGS:
        for name in names:
            if name in existing_names:
                conn.execute(
                    sa.text(
                        "UPDATE research_tags SET category = :category, "
                        "sort_order = :sort_order WHERE name = :name"
                    ),
                    {"category": category, "sort_order": sort_order, "name": name},
                )
            else:
                new_rows.append(
                    {"name": name, "category": category, "sort_order": sort_order}
                )
            sort_order += 1

    if new_rows:
        op.bulk_insert(research_tags, new_rows)


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()

    # このマイグレーションで新規追加したタグを削除する(ユーザーの紐付けも
    # 連鎖削除される)。
    for name in NEW_TAG_NAMES:
        conn.execute(
            sa.text("DELETE FROM research_tags WHERE name = :name"), {"name": name}
        )

    # カテゴリを元に戻す。
    for name, category in ORIGINAL_CATEGORY_BY_NAME.items():
        conn.execute(
            sa.text("UPDATE research_tags SET category = :category WHERE name = :name"),
            {"category": category, "name": name},
        )

    # 「暗号・認証」を「暗号」に戻す。ただし統合前に「認証」を選んでいた
    # 学生の紐付けが「認証」タグ自体の削除ごと失われている点は復元できない
    # (このダウングレードはベストエフォート)。
    conn.execute(
        sa.text("UPDATE research_tags SET name = '暗号' WHERE name = '暗号・認証'")
    )
    conn.execute(
        sa.text(
            "UPDATE research_tags SET name = '文章解析' "
            "WHERE name = 'テキストマイニング'"
        )
    )
