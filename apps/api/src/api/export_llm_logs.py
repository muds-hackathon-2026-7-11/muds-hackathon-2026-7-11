"""LLM入出力ログ(chat_logs / match_logs)をJSONLへ書き出す(#228)。

使い方:
    uv run python -m api.export_llm_logs <出力ディレクトリ> [--from YYYY-MM-DD]
                                          [--to YYYY-MM-DD] [--anonymize]

`--anonymize` を付けると user_id を安定ハッシュ(SHA-256の先頭16桁)へ置換する。
同じ学生は同じ仮名になるので「1人がどう相談を進めたか」は追えるが、誰かは
辿れない。**分析目的の取り出しでは原則こちらを使うこと。** 削除依頼など個人を
特定する必要がある場合だけ、DB側で user_id を使う。

出力物には学生の相談内容がそのまま含まれる。既定の出力先は .private/
(gitignore済み)で、外部への共有はしないこと。
"""

import argparse
import asyncio
import hashlib
import json
import uuid
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import async_session
from api.models import ChatLog, MatchLog

# 仮名化のsalt。値を変えると過去の出力と仮名が一致しなくなるため固定する。
# 秘匿目的ではなく「出力単体から user_id を逆算しにくくする」ためのもの。
_PSEUDONYM_SALT = "muds-llm-logs"


def _pseudonym(user_id: uuid.UUID) -> str:
    digest = hashlib.sha256(f"{_PSEUDONYM_SALT}\x00{user_id}".encode()).hexdigest()
    return digest[:16]


def _serialize(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):  # Enum
        return value.value
    return value


def _to_dict(row: Any, *, anonymize: bool) -> dict:
    out: dict[str, Any] = {}
    for column in row.__table__.columns:
        name = column.name
        value = getattr(row, name)
        if name == "user_id":
            out["user"] = _pseudonym(value) if anonymize else str(value)
            continue
        out[name] = _serialize(value)
    return out


def _bounds(
    from_: date | None, to: date | None
) -> tuple[datetime | None, datetime | None]:
    """--to はその日を含めたいので、翌日0時未満として扱う。"""
    start = datetime.combine(from_, time.min) if from_ else None
    end = datetime.combine(to, time.max) if to else None
    return start, end


async def _dump(
    session: AsyncSession,
    model: Any,
    path: Path,
    *,
    anonymize: bool,
    start: datetime | None,
    end: datetime | None,
) -> int:
    stmt = select(model).order_by(model.created_at)
    if start is not None:
        stmt = stmt.where(model.created_at >= start)
    if end is not None:
        stmt = stmt.where(model.created_at <= end)

    rows = (await session.execute(stmt)).scalars().all()
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(_to_dict(row, anonymize=anonymize), ensure_ascii=False))
            f.write("\n")
    return len(rows)


async def export(
    out_dir: Path, *, anonymize: bool, from_: date | None, to: date | None
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    start, end = _bounds(from_, to)

    async with async_session() as session:
        chats = await _dump(
            session,
            ChatLog,
            out_dir / "chat_logs.jsonl",
            anonymize=anonymize,
            start=start,
            end=end,
        )
        matches = await _dump(
            session,
            MatchLog,
            out_dir / "match_logs.jsonl",
            anonymize=anonymize,
            start=start,
            end=end,
        )

    label = "仮名化あり" if anonymize else "user_idそのまま"
    print(f"chat_logs.jsonl : {chats}件")
    print(f"match_logs.jsonl: {matches}件")
    print(f"出力先: {out_dir} ({label})")
    if not anonymize:
        print(
            "警告: user_id をそのまま出力しました。"
            "分析目的なら --anonymize を付けてください。"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LLM入出力ログ(chat_logs / match_logs)をJSONLへ書き出す"
    )
    parser.add_argument("out_dir", type=Path, help="出力ディレクトリ")
    parser.add_argument("--from", dest="from_", type=date.fromisoformat, default=None)
    parser.add_argument("--to", dest="to", type=date.fromisoformat, default=None)
    parser.add_argument(
        "--anonymize",
        action="store_true",
        help="user_id を安定ハッシュへ置換する(分析目的では推奨)",
    )
    args = parser.parse_args()
    asyncio.run(
        export(args.out_dir, anonymize=args.anonymize, from_=args.from_, to=args.to)
    )


if __name__ == "__main__":
    main()
