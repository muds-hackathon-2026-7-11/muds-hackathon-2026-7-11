import uuid
from datetime import date, timedelta

import pytest

from api import auth
from api.models import (
    RecruitmentTerm,
    RecruitmentTermStatus,
    ResearchTag,
    Seminar,
    SeminarMember,
    User,
    UserRole,
)

pytestmark = pytest.mark.asyncio


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _make_user(db_session, role: UserRole = UserRole.student) -> User:
    user = User(
        google_id=_unique("google"),
        email=f"{_unique('user')}@example.com",
        name="テストユーザー",
        role=role,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_tag(db_session, name: str) -> ResearchTag:
    # research_tags.name はDB全体で一意制約があり、マイグレーションで投入した
    # 初期タグ名(機械学習、画像処理等)と衝突しないよう、ここでは常に一意な
    # 名前にして作成する(db_sessionはロールバックのみでコミットされないため、
    # 既存の初期データとは別に安全に追加・削除できる)。
    tag = ResearchTag(name=_unique(name), category="テストカテゴリ")
    db_session.add(tag)
    await db_session.flush()
    return tag


async def _make_term(db_session, academic_year: int) -> RecruitmentTerm:
    term = RecruitmentTerm(
        academic_year=academic_year,
        starts_at=date.today() - timedelta(days=1),
        ends_at=date.today() + timedelta(days=30),
        status=RecruitmentTermStatus.open,
    )
    db_session.add(term)
    await db_session.flush()
    return term


async def _make_seminar(db_session) -> Seminar:
    seminar = Seminar(name=_unique("seminar"))
    db_session.add(seminar)
    await db_session.flush()
    return seminar


def _auth_headers(email: str) -> dict[str, str]:
    return {"X-Dev-User-Email": email, "X-Dev-User-Role": "student"}


@pytest.fixture(autouse=True)
def _enable_dev_auth(monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_dev_mode", True)


# --- GET /me: current_seminar ---


async def test_get_me_includes_current_seminar_when_assigned(
    client, db_session
) -> None:
    # current_academic_year()は「直近に作成された募集期間」を見るため、
    # 他のテスト/実データより新しい年度にして「現在」として扱われるようにする。
    academic_year = 3000 + int(uuid.uuid4().int % 1000)
    term = await _make_term(db_session, academic_year)
    seminar = await _make_seminar(db_session)
    user = await _make_user(db_session)
    db_session.add(
        SeminarMember(seminar_id=seminar.id, student_id=user.id, term_id=term.id)
    )
    await db_session.flush()

    resp = await client.get("/me", headers=_auth_headers(user.email))

    assert resp.status_code == 200
    body = resp.json()
    assert body["current_seminar"] is not None
    assert body["current_seminar"]["name"] == seminar.name


async def test_get_me_current_seminar_is_null_when_not_assigned(
    client, db_session
) -> None:
    academic_year = 3000 + int(uuid.uuid4().int % 1000)
    await _make_term(db_session, academic_year)
    user = await _make_user(db_session)

    resp = await client.get("/me", headers=_auth_headers(user.email))

    assert resp.status_code == 200
    assert resp.json()["current_seminar"] is None


# --- GET /me ---


async def test_get_me_includes_empty_interest_tags_by_default(
    client, db_session
) -> None:
    user = await _make_user(db_session)

    resp = await client.get("/me", headers=_auth_headers(user.email))

    assert resp.status_code == 200
    assert resp.json()["interest_tags"] == []


async def test_get_me_includes_set_interest_tags(client, db_session) -> None:
    user = await _make_user(db_session)
    tag_a = await _make_tag(db_session, "機械学習")
    tag_b = await _make_tag(db_session, "画像処理")

    resp = await client.patch(
        "/me",
        headers=_auth_headers(user.email),
        json={
            "research_theme": "画像認識の研究",
            "interest_tag_ids": [str(tag_a.id), str(tag_b.id)],
        },
    )
    assert resp.status_code == 200

    resp = await client.get("/me", headers=_auth_headers(user.email))
    body = resp.json()
    assert body["research_theme"] == "画像認識の研究"
    assert {t["name"] for t in body["interest_tags"]} == {tag_a.name, tag_b.name}


# --- PATCH /me ---


async def test_patch_me_updates_research_theme_only(client, db_session) -> None:
    user = await _make_user(db_session)

    resp = await client.patch(
        "/me",
        headers=_auth_headers(user.email),
        json={"research_theme": "自然言語処理の研究", "interest_tag_ids": []},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["research_theme"] == "自然言語処理の研究"
    assert body["interest_tags"] == []


async def test_patch_me_replaces_previous_tags(client, db_session) -> None:
    user = await _make_user(db_session)
    tag_a = await _make_tag(db_session, "機械学習")
    tag_b = await _make_tag(db_session, "画像処理")

    first = await client.patch(
        "/me",
        headers=_auth_headers(user.email),
        json={"research_theme": None, "interest_tag_ids": [str(tag_a.id)]},
    )
    assert [t["name"] for t in first.json()["interest_tags"]] == [tag_a.name]

    second = await client.patch(
        "/me",
        headers=_auth_headers(user.email),
        json={"research_theme": None, "interest_tag_ids": [str(tag_b.id)]},
    )

    assert second.status_code == 200
    # 前回設定したタグ(tag_a)は残らず、新しい指定(tag_b)だけになる。
    assert [t["name"] for t in second.json()["interest_tags"]] == [tag_b.name]


async def test_patch_me_rejects_unknown_tag_id(client, db_session) -> None:
    user = await _make_user(db_session)
    unknown_id = uuid.uuid4()

    resp = await client.patch(
        "/me",
        headers=_auth_headers(user.email),
        json={"research_theme": None, "interest_tag_ids": [str(unknown_id)]},
    )

    assert resp.status_code == 400


async def test_patch_me_can_clear_research_theme(client, db_session) -> None:
    user = await _make_user(db_session)
    user.research_theme = "以前の研究テーマ"
    await db_session.flush()

    resp = await client.patch(
        "/me",
        headers=_auth_headers(user.email),
        json={"research_theme": None, "interest_tag_ids": []},
    )

    assert resp.status_code == 200
    assert resp.json()["research_theme"] is None


async def test_patch_me_dedupes_repeated_tag_id(client, db_session) -> None:
    user = await _make_user(db_session)
    tag = await _make_tag(db_session, "機械学習")

    resp = await client.patch(
        "/me",
        headers=_auth_headers(user.email),
        json={
            "research_theme": None,
            "interest_tag_ids": [str(tag.id), str(tag.id)],
        },
    )

    assert resp.status_code == 200
    assert [t["name"] for t in resp.json()["interest_tags"]] == [tag.name]


async def test_patch_me_forbidden_for_inactive_user(client, db_session) -> None:
    user = await _make_user(db_session)
    user.is_active = False
    await db_session.flush()

    resp = await client.patch(
        "/me",
        headers=_auth_headers(user.email),
        json={"research_theme": "退会後の変更", "interest_tag_ids": []},
    )

    assert resp.status_code == 403


async def test_patch_me_only_updates_own_profile(client, db_session) -> None:
    user_a = await _make_user(db_session)
    user_b = await _make_user(db_session)

    await client.patch(
        "/me",
        headers=_auth_headers(user_a.email),
        json={"research_theme": "Aさんのテーマ", "interest_tag_ids": []},
    )

    resp_b = await client.get("/me", headers=_auth_headers(user_b.email))
    assert resp_b.json()["research_theme"] is None


# --- GET /research-tags ---


async def test_list_research_tags_returns_master_list(client, db_session) -> None:
    tag_a = await _make_tag(db_session, "推薦システム")
    tag_b = await _make_tag(db_session, "ロボティクス")

    resp = await client.get("/research-tags")

    assert resp.status_code == 200
    names = {t["name"] for t in resp.json()}
    assert {tag_a.name, tag_b.name} <= names
