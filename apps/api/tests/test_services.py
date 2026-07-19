import uuid
from datetime import UTC, date, datetime, timedelta

import pytest

from api.models import RecruitmentTerm, RecruitmentTermStatus
from api.services import get_current_term, normalize_grade


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("B1", "B1"),
        ("B2", "B2"),
        ("B3", "B3"),
        ("B4", "B4"),
        # MIDS学生も末尾のB1〜B4として扱う(#99)。
        ("MIDS/B1", "B1"),
        ("MIDS/B3", "B3"),
        ("MIDS/B4", "B4"),
        # 大学院生・guest・空文字・未設定はB1〜B4のどれにも一致しない。
        ("M1", None),
        ("M1 guest", None),
        ("M2", None),
        ("M2 guest", None),
        ("D1", None),
        ("", None),
        (None, None),
    ],
)
def test_normalize_grade(raw: str | None, expected: str | None) -> None:
    assert normalize_grade(raw) == expected


@pytest.mark.asyncio
async def test_get_current_term_prefers_latest_created_at_when_academic_year_ties(
    db_session,
) -> None:
    # 前期・後期のように、同じacademic_yearでopenな募集ラウンドが複数
    # 存在し、両方が同時にアクティブな場合(#57で作成可能、実際に運用DBで
    # 発生した)、created_atが最も新しいもの(=最後に設定されたラウンド)
    # が決定的に選ばれることを確認する(#182)。starts_atはdate型で日単位
    # までしか区別できない(かつ運営の任意入力)ため、あえて同じ日付にして
    # starts_atでは区別できないケースであることを明示している。academic_year
    # を3000+乱数にしているのは、実DBに残っている本物の募集ラウンドより
    # 必ず新しい年度にして、そちらを誤って拾わないようにするため。
    academic_year = 3000 + int(uuid.uuid4().int % 1000)
    today = date.today()
    now = datetime.now(UTC)
    older = RecruitmentTerm(
        academic_year=academic_year,
        starts_at=today,
        ends_at=today + timedelta(days=90),
        status=RecruitmentTermStatus.open,
        created_at=now - timedelta(seconds=10),
    )
    newer = RecruitmentTerm(
        academic_year=academic_year,
        starts_at=today,
        ends_at=today + timedelta(days=10),
        status=RecruitmentTermStatus.open,
        created_at=now,
    )
    db_session.add_all([older, newer])
    await db_session.flush()

    term = await get_current_term(db_session)

    assert term is not None
    assert term.id == newer.id


@pytest.mark.asyncio
async def test_get_current_term_is_deterministic_even_when_fully_tied(
    db_session,
) -> None:
    # academic_year・starts_at・created_atまで全て一致する場合(同一
    # トランザクションでの一括作成などで理論上起こりうる。Postgresの
    # NOW()はトランザクション開始時刻なので、同時に複数行INSERTすると
    # created_atも同値になる)でも、idによる最終フォールバックで毎回
    # 同じ行を返すことを確認する(#182)。業務的な「正しさ」は無いが、
    # 同じリクエストのたびに結果が変わらないことが重要。
    academic_year = 3000 + int(uuid.uuid4().int % 1000)
    today = date.today()
    same_created_at = datetime.now(UTC)
    first = RecruitmentTerm(
        academic_year=academic_year,
        starts_at=today,
        ends_at=today + timedelta(days=30),
        status=RecruitmentTermStatus.open,
        created_at=same_created_at,
    )
    second = RecruitmentTerm(
        academic_year=academic_year,
        starts_at=today,
        ends_at=today + timedelta(days=30),
        status=RecruitmentTermStatus.open,
        created_at=same_created_at,
    )
    db_session.add_all([first, second])
    await db_session.flush()

    first_call = await get_current_term(db_session)
    second_call = await get_current_term(db_session)

    assert first_call is not None
    assert second_call is not None
    assert first_call.id == second_call.id
