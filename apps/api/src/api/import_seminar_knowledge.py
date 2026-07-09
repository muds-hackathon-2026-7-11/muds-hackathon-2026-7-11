"""ゼミ資料の要約ドキュメントを seminars.knowledge へ投入するスクリプト。

使い方: uv run python -m api.import_seminar_knowledge <ディレクトリ>
        (デフォルトは Makefile 経由で docs/seminars/knowledge)

- `<ディレクトリ>/<ゼミ名>.md` のファイル名(拡張子除く)がゼミ名と一致するゼミの
  `seminars.knowledge` に、ファイル内容をそのまま投入する(冪等・毎回上書き)。
- `README.md` と `teachers/` サブディレクトリ(合同ゼミの教員別)は対象外。
- ゼミ名が完全一致しない場合は別名マップ(_NAME_ALIASES)で解決する。解決できない
  ファイルは警告してスキップし、他のファイルは処理を続ける。
- import_seminar_docs.py(PDF→Vision要約) と異なり、要約済みテキストをそのまま入れる
  (このスクリプトはOpenAIを必要としない)。

前提: 対象ゼミは import_seminars 等で作成済み。
"""

import argparse
import asyncio
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import async_session
from api.models import Seminar

# ドキュメントのファイル名(stem) → DB上のゼミ名 の別名。
# 合同ゼミはファイル名を短くしているため、正式名へ対応付ける。
_NAME_ALIASES: dict[str, str] = {
    "Virachゼミ（合同）": (
        "Virachゼミ（Virach・Thatsanee・佐々木・神崎・小林・Titi合同）"
    ),
}

# 投入対象外のファイル名(stem)。
_IGNORE_STEMS: frozenset[str] = frozenset({"README"})


def _resolve_name(stem: str) -> str:
    """ファイル名(stem)を、DB上のゼミ名へ解決する(別名があれば適用)。"""
    return _NAME_ALIASES.get(stem, stem)


def _knowledge_files(directory: Path) -> list[Path]:
    """投入対象の .md 一覧(トップレベルのみ・除外stemを除く)。"""
    return sorted(p for p in directory.glob("*.md") if p.stem not in _IGNORE_STEMS)


async def _find_seminar(session: AsyncSession, name: str) -> Seminar | None:
    result = await session.execute(select(Seminar).where(Seminar.name == name))
    return result.scalar_one_or_none()


async def apply_knowledge(
    session: AsyncSession, directory: Path
) -> tuple[int, list[str]]:
    """ディレクトリの要約mdを seminars.knowledge に反映する(commitはしない)。

    返り値: (更新した件数, スキップした説明のリスト)。
    """
    updated = 0
    skipped: list[str] = []
    for path in _knowledge_files(directory):
        name = _resolve_name(path.stem)
        seminar = await _find_seminar(session, name)
        if seminar is None:
            skipped.append(f"{path.name}(ゼミ「{name}」が見つからない)")
            continue
        seminar.knowledge = path.read_text(encoding="utf-8").strip()
        updated += 1
        print(f"OK: {seminar.name} <- {path.name}")
    return updated, skipped


async def import_knowledge(directory: Path) -> None:
    if not _knowledge_files(directory):
        print(f"knowledgeファイルが見つかりません: {directory}")
        return

    async with async_session() as session:
        updated, skipped = await apply_knowledge(session, directory)
        await session.commit()

    print(f"\n更新: {updated}件")
    if skipped:
        print("スキップ:\n  " + "\n  ".join(skipped))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ゼミ資料の要約ドキュメントを seminars.knowledge へ投入する"
    )
    parser.add_argument(
        "docs_dir",
        type=Path,
        help="要約mdのディレクトリ(例: docs/seminars/knowledge)",
    )
    args = parser.parse_args()
    asyncio.run(import_knowledge(args.docs_dir))


if __name__ == "__main__":
    main()
