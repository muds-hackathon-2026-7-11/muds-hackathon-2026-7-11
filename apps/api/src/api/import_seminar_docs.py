"""ゼミ資料(PDF)を取り込み、AI用の要約知識を seminars.knowledge に投入するスクリプト。

使い方: uv run python -m api.import_seminar_docs <PDFディレクトリ>
        (デフォルトは Makefile 経由で data/seminar_docs)

- `<ディレクトリ>/<ゼミ名>.pdf` の **ファイル名(拡張子除く)がゼミ名** と一致するゼミに
  紐づける(import_seminars と同じくゼミ名マッチ)。
- PDFからテキストを抽出し、OpenAIで要約して seminars.knowledge に保存する。
- 要約はマッチ度診断・相談チャットの文脈として使う(リクエスト時にPDFは読まない)。

前提: 対象ゼミは import_seminars 等で作成済み。OpenAI が利用可能(課金/quotaあり)。
"""

import argparse
import asyncio
from pathlib import Path

from openai import AsyncOpenAI
from pypdf import PdfReader
from sqlalchemy import select

from api.config import settings
from api.db import async_session
from api.models import Seminar

# 要約が長くなりすぎないよう、抽出テキストはこの文字数で頭を打つ(トークン節約)。
_MAX_INPUT_CHARS = 20000

_SUMMARY_SYSTEM = (
    "あなたは大学のゼミ紹介資料を要約するアシスタントです。"
    "学生のゼミ選択を支援するAIが後で参照するため、研究分野・扱うテーマ・"
    "身につくスキル・活動内容・雰囲気などの要点を、日本語で簡潔に"
    "(最大400字程度)まとめてください。資料に無い情報は補完しないこと。"
)


def _extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return text.strip()


async def _summarize(client: AsyncOpenAI, *, text: str) -> str:
    response = await client.chat.completions.create(
        model=settings.match_model,
        messages=[
            {"role": "system", "content": _SUMMARY_SYSTEM},
            {"role": "user", "content": f"# ゼミ紹介資料\n{text[:_MAX_INPUT_CHARS]}"},
        ],
        temperature=0,
    )
    return (response.choices[0].message.content or "").strip()


async def import_docs(directory: Path) -> None:
    pdfs = sorted(directory.glob("*.pdf"))
    if not pdfs:
        print(f"PDFが見つかりません: {directory}")
        return

    client = AsyncOpenAI(
        api_key=settings.openai_api_key, base_url=settings.openai_base_url or None
    )
    updated = 0
    skipped: list[str] = []
    errors: list[str] = []

    async with async_session() as session:
        for pdf in pdfs:
            name = pdf.stem.strip()
            seminar = (
                await session.execute(select(Seminar).where(Seminar.name == name))
            ).scalar_one_or_none()
            if seminar is None:
                skipped.append(f"{pdf.name}(ゼミ「{name}」が見つからない)")
                continue
            try:
                text = _extract_pdf_text(pdf)
                if not text:
                    errors.append(f"{pdf.name}(テキスト抽出結果が空)")
                    continue
                seminar.knowledge = await _summarize(client, text=text)
                updated += 1
                print(f"OK: {name} <- {pdf.name}")
            except Exception as e:  # noqa: BLE001
                errors.append(f"{pdf.name}({type(e).__name__}: {e})")

        await session.commit()

    print(f"\n更新: {updated}件")
    if skipped:
        print("スキップ:\n  " + "\n  ".join(skipped))
    if errors:
        print("エラー:\n  " + "\n  ".join(errors))


def main() -> None:
    parser = argparse.ArgumentParser(description="ゼミ資料PDFを要約してDBへ投入する")
    parser.add_argument(
        "docs_dir", type=Path, help="PDFを置いたディレクトリ(例: data/seminar_docs)"
    )
    args = parser.parse_args()
    asyncio.run(import_docs(args.docs_dir))


if __name__ == "__main__":
    main()
