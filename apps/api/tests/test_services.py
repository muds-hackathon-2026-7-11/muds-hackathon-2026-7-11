import uuid
from datetime import date, timedelta

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
async def test_get_current_term_prefers_latest_starts_at_when_academic_year_ties(
    db_session,
) -> None:
    # 前期・後期のように、同じacademic_yearでopenな募集ラウンドが複数
    # 存在し、両方が同時にアクティブな場合(#57で作成可能、実際に運用DBで
    # 発生した)、starts_atが最も遅いもの(=最も新しく設定されたラウンド)
    # が決定的に選ばれることを確認する(#182)。academic_yearを3000+乱数に
    # しているのは、実DBに残っている本物の募集ラウンドより必ず新しい年度に
    # して、そちらを誤って拾わないようにするため。
    academic_year = 3000 + int(uuid.uuid4().int % 1000)
    today = date.today()
    older = RecruitmentTerm(
        academic_year=academic_year,
        starts_at=today - timedelta(days=10),
        ends_at=today + timedelta(days=90),
        status=RecruitmentTermStatus.open,
    )
    newer = RecruitmentTerm(
        academic_year=academic_year,
        starts_at=today - timedelta(days=1),
        ends_at=today + timedelta(days=10),
        status=RecruitmentTermStatus.open,
    )
    db_session.add_all([older, newer])
    await db_session.flush()

    term = await get_current_term(db_session)

    assert term is not None
    assert term.id == newer.id
