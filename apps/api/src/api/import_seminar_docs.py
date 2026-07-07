"""ゼミ資料(PDF)を取り込み、AI用の要約知識を seminars.knowledge に投入するスクリプト。

使い方: uv run python -m api.import_seminar_docs <PDFディレクトリ>
        (デフォルトは Makefile 経由で data/seminar_docs)

- `<ディレクトリ>/<ゼミ名>.pdf` の **ファイル名(拡張子除く)がゼミ名** と一致するゼミに
  紐づける(import_seminars と同じくゼミ名マッチ)。
- PDFの各ページを「テキストが取れるページはテキスト」「取れないページ(スクショや
  スライドなど画像主体)はページ画像」として取り出し、OpenAIのVisionモデルで
  要約して seminars.knowledge に保存する。
  FireShotでWebページを撮ったPDF等はページが1枚の画像で、テキスト抽出では
  ヘッダ文言しか取れない。そうしたページは画像としてモデルに読ませる。
- 要約はマッチ度診断・相談チャットの文脈として使う(リクエスト時にPDFは読まない)。

前提: 対象ゼミは import_seminars 等で作成済み。OpenAI が利用可能(課金/quotaあり)。
"""

import argparse
import asyncio
import base64
import io
from dataclasses import dataclass
from pathlib import Path

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionContentPartParam
from PIL import Image
from pypdf import PdfReader
from sqlalchemy import select

from api.config import settings
from api.db import async_session
from api.models import Seminar

# テキストページ合計の上限(トークン節約)。これを超えた分のテキストは切り詰める。
_MAX_INPUT_CHARS = 20000
# ノイズ除去後のページ本文がこの文字数以上ならテキストページ、未満なら画像ページ扱い。
_TEXT_PAGE_MIN_CHARS = 120
# 1つのPDFからモデルに送る画像(タイル)の総数上限(コスト抑制)。超過分は無視。
_MAX_IMAGES_PER_DOC = 16
# 画像の1辺の最大px。OpenAI Visionが内部で2048に縮小するため、それに合わせる。
# 縦長スクショはこの高さで縦に分割し、native解像度に近い状態で読ませる。
_IMAGE_MAX_SIDE = 2048
# 縦長ページを分割するタイル数の上限(1ページあたり)。
_MAX_TILES_PER_PAGE = 3
# これ以下の小さな画像(アイコン・ロゴ等)は無視する。
_MIN_IMAGE_DIM = 200

# PDFビューア/キャプチャ由来のヘッダ・フッタ行。本文ではないので除外する。
_BOILERPLATE_MARKERS = ("FireShot", "chrome-extension://")

_SUMMARY_SYSTEM = (
    "あなたは大学のゼミ紹介資料を要約するアシスタントです。"
    "資料はテキストとページ画像(Webページのスクリーンショットやスライド)で"
    "与えられます。学生のゼミ選択を支援するAIが後で参照するため、"
    "研究分野・扱うテーマ・研究手法や使用技術・身につくスキル・活動内容・"
    "雰囲気・指導方針など、ゼミ選びの判断に役立つ具体的な情報を"
    "過不足なくまとめてください。\n"
    "厳守事項:\n"
    "- 資料に書かれていない情報を推測・補完・創作しない。書かれている事実だけを使う。\n"
    "- 分量は資料の情報量に合わせる。情報が多ければ長く、少なければ短くてよく、"
    "無理に埋めない。空欄を作らないための水増しは禁止。\n"
    "- 要点を落とさない範囲で簡潔に。目安は600〜800字程度だが、"
    "内容に応じて超えても短くてもよい。\n"
    "- 後からAIが読みやすいよう、短い段落や箇条書きで整理する。日本語で書く。\n"
    "- ヘッダ・URL・撮影日時・ページ番号など、資料内容と無関係な要素は無視する。"
)


@dataclass
class _PagePart:
    """要約入力の1ブロック。text か image_url のどちらか一方を持つ。"""

    kind: str  # "text" | "image"
    text: str | None = None
    data_url: str | None = None


def _clean_text(text: str) -> str:
    """FireShot等のキャプチャ由来ヘッダ/フッタ行を除いた本文テキスト。"""
    lines = [
        line
        for line in text.splitlines()
        if not any(marker in line for marker in _BOILERPLATE_MARKERS)
    ]
    return "\n".join(lines).strip()


def _encode_jpeg(image: Image.Image) -> str:
    """PIL画像を data URL (JPEG) にする。"""
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=80)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def _image_to_data_urls(image: Image.Image) -> list[str]:
    """ページ画像を、native解像度をなるべく保った data URL 群にする。

    縦長スクショ(FireShot等)は1辺 _IMAGE_MAX_SIDE で縦に分割し、
    縮小しすぎて文字が潰れるのを防ぐ。分割数は _MAX_TILES_PER_PAGE 上限。
    """
    w, h = image.width, image.height
    if w <= _IMAGE_MAX_SIDE and h <= _IMAGE_MAX_SIDE:
        return [_encode_jpeg(image)]

    # 長辺が縦か横かで分割方向を決める。多くのスクショは縦長。
    if h >= w:
        if w > _IMAGE_MAX_SIDE:  # まず幅を上限に合わせる
            scale = _IMAGE_MAX_SIDE / w
            image = image.resize((_IMAGE_MAX_SIDE, round(h * scale)))
            w, h = image.width, image.height
        urls: list[str] = []
        top = 0
        while top < h and len(urls) < _MAX_TILES_PER_PAGE:
            bottom = min(top + _IMAGE_MAX_SIDE, h)
            urls.append(_encode_jpeg(image.crop((0, top, w, bottom))))
            top += _IMAGE_MAX_SIDE
        return urls

    # 横長ページ(まれ): 高さを合わせて横に分割。
    if h > _IMAGE_MAX_SIDE:
        scale = _IMAGE_MAX_SIDE / h
        image = image.resize((round(w * scale), _IMAGE_MAX_SIDE))
        w, h = image.width, image.height
    urls = []
    left = 0
    while left < w and len(urls) < _MAX_TILES_PER_PAGE:
        right = min(left + _IMAGE_MAX_SIDE, w)
        urls.append(_encode_jpeg(image.crop((left, 0, right, h))))
        left += _IMAGE_MAX_SIDE
    return urls


def _largest_page_image(page) -> Image.Image | None:
    """ページ中で最も大きい埋め込み画像(=ページ全面のスクショ/スライド)を返す。

    小さなアイコン・ロゴは無視する。取得できなければ None。
    """
    best: Image.Image | None = None
    best_area = 0
    try:
        images = list(page.images)
    except Exception:  # noqa: BLE001  壊れた画像XObjectでもページ処理は続ける
        return None
    for img in images:
        try:
            pil = img.image
        except Exception:  # noqa: BLE001
            continue
        if pil.width < _MIN_IMAGE_DIM or pil.height < _MIN_IMAGE_DIM:
            continue
        area = pil.width * pil.height
        if area > best_area:
            best_area, best = area, pil
    return best


def _build_page_parts(reader: PdfReader) -> tuple[list[_PagePart], int, int]:
    """PDFを要約入力ブロック列に変換する。返り値: (parts, textページ数, 画像数)。"""
    parts: list[_PagePart] = []
    text_chars = 0
    text_pages = 0
    image_count = 0
    for page in reader.pages:
        text = _clean_text(page.extract_text() or "")
        has_text = len(text) >= _TEXT_PAGE_MIN_CHARS and text_chars < _MAX_INPUT_CHARS
        if has_text:
            snippet = text[: _MAX_INPUT_CHARS - text_chars]
            text_chars += len(snippet)
            text_pages += 1
            parts.append(_PagePart(kind="text", text=snippet))
            continue

        # テキストが薄いページは画像として読ませる。
        if image_count >= _MAX_IMAGES_PER_DOC:
            continue
        image = _largest_page_image(page)
        if image is None:
            # 画像も無く僅かにテキストがあるだけなら、それを拾っておく。
            if text:
                parts.append(_PagePart(kind="text", text=text))
            continue
        for url in _image_to_data_urls(image):
            if image_count >= _MAX_IMAGES_PER_DOC:
                break
            image_count += 1
            parts.append(_PagePart(kind="image", data_url=url))
    return parts, text_pages, image_count


async def _summarize(client: AsyncOpenAI, *, parts: list[_PagePart]) -> str:
    content: list[ChatCompletionContentPartParam] = [
        {
            "type": "text",
            "text": "# ゼミ紹介資料(ページ順。テキストと画像が混在します)",
        }
    ]
    for i, part in enumerate(parts, start=1):
        if part.kind == "text":
            content.append(
                {"type": "text", "text": f"\n【ページ{i}(テキスト)】\n{part.text}"}
            )
        elif part.data_url is not None:
            content.append({"type": "text", "text": f"\n【ページ{i}(画像)】"})
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": part.data_url, "detail": "high"},
                }
            )
    response = await client.chat.completions.create(
        model=settings.doc_summary_model,
        messages=[
            {"role": "system", "content": _SUMMARY_SYSTEM},
            {"role": "user", "content": content},
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
                reader = PdfReader(str(pdf))
                parts, text_pages, image_count = _build_page_parts(reader)
                if not parts:
                    errors.append(f"{pdf.name}(テキスト・画像とも抽出できなかった)")
                    continue
                seminar.knowledge = await _summarize(client, parts=parts)
                updated += 1
                print(
                    f"OK: {name} <- {pdf.name} "
                    f"(テキスト{text_pages}ページ / 画像{image_count}枚)"
                )
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
