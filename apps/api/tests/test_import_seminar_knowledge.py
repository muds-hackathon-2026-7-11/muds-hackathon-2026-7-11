import uuid
from pathlib import Path

import pytest

from api import import_seminar_knowledge as mod
from api.import_seminar_knowledge import _resolve_name, apply_knowledge
from api.models import Seminar


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _make_seminar(db_session, name: str) -> Seminar:
    seminar = Seminar(name=name)
    db_session.add(seminar)
    await db_session.flush()
    return seminar


def _write(directory: Path, filename: str, content: str) -> None:
    (directory / filename).write_text(content, encoding="utf-8")


def test_resolve_name_applies_alias_and_passthrough() -> None:
    assert (
        _resolve_name("Virachゼミ（合同）")
        == "Virachゼミ（Virach・Thatsanee・佐々木・神崎・小林・Titi合同）"
    )
    assert _resolve_name("福原ゼミ") == "福原ゼミ"


@pytest.mark.asyncio
async def test_apply_knowledge_sets_knowledge(db_session, tmp_path) -> None:
    name = _unique("seminar")
    seminar = await _make_seminar(db_session, name)
    _write(tmp_path, f"{name}.md", "研究概要テキスト")

    updated, skipped = await apply_knowledge(db_session, tmp_path)
    await db_session.flush()

    assert updated == 1
    assert skipped == []
    assert seminar.knowledge == "研究概要テキスト"


@pytest.mark.asyncio
async def test_apply_knowledge_overwrites_on_rerun(db_session, tmp_path) -> None:
    name = _unique("seminar")
    seminar = await _make_seminar(db_session, name)
    _write(tmp_path, f"{name}.md", "旧テキスト")
    await apply_knowledge(db_session, tmp_path)
    await db_session.flush()

    _write(tmp_path, f"{name}.md", "新テキスト")
    updated, _ = await apply_knowledge(db_session, tmp_path)
    await db_session.flush()

    assert updated == 1
    assert seminar.knowledge == "新テキスト"


@pytest.mark.asyncio
async def test_apply_knowledge_resolves_alias(
    db_session, tmp_path, monkeypatch
) -> None:
    name = _unique("seminar")
    stem = _unique("file")
    seminar = await _make_seminar(db_session, name)
    monkeypatch.setattr(mod, "_NAME_ALIASES", {stem: name})
    _write(tmp_path, f"{stem}.md", "本文")

    updated, skipped = await apply_knowledge(db_session, tmp_path)
    await db_session.flush()

    assert updated == 1
    assert skipped == []
    assert seminar.knowledge == "本文"


@pytest.mark.asyncio
async def test_apply_knowledge_skips_unmatched_but_continues(
    db_session, tmp_path
) -> None:
    name = _unique("seminar")
    seminar = await _make_seminar(db_session, name)
    _write(tmp_path, f"{name}.md", "有効")
    _write(tmp_path, f"{_unique('missing')}.md", "対応ゼミ無し")

    updated, skipped = await apply_knowledge(db_session, tmp_path)
    await db_session.flush()

    assert updated == 1
    assert len(skipped) == 1
    assert seminar.knowledge == "有効"


@pytest.mark.asyncio
async def test_apply_knowledge_ignores_readme_and_teachers(
    db_session, tmp_path
) -> None:
    name = _unique("seminar")
    seminar = await _make_seminar(db_session, name)
    _write(tmp_path, f"{name}.md", "本文")
    _write(tmp_path, "README.md", "説明")
    (tmp_path / "teachers").mkdir()
    _write(tmp_path / "teachers", "someone.md", "教員別")

    updated, skipped = await apply_knowledge(db_session, tmp_path)
    await db_session.flush()

    assert updated == 1  # README と teachers/ は対象外
    assert skipped == []
    assert seminar.knowledge == "本文"
