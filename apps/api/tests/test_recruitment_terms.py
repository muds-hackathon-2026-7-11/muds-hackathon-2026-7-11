import uuid
from datetime import date

import pytest

from api.models import RecruitmentTerm, RecruitmentTermStatus
from api.recruitment_terms import get_or_create_recruitment_term

pytestmark = pytest.mark.asyncio


async def test_get_or_create_recruitment_term_creates_when_missing(db_session) -> None:
    academic_year = 3000 + int(uuid.uuid4().int % 1000)

    term, created = await get_or_create_recruitment_term(db_session, academic_year)

    assert created is True
    assert term.academic_year == academic_year


async def test_get_or_create_recruitment_term_gets_existing(db_session) -> None:
    academic_year = 3000 + int(uuid.uuid4().int % 1000)
    first, _ = await get_or_create_recruitment_term(db_session, academic_year)

    second, created = await get_or_create_recruitment_term(db_session, academic_year)

    assert created is False
    assert second.id == first.id


async def test_get_or_create_recruitment_term_does_not_crash_with_multiple_rounds(
    db_session,
) -> None:
    # academic_yearに一意制約は無い(運営が#57のAPIで前期・後期等の複数回を
    # 作成できる)ため、既に2件あってもscalar_one_or_none()のような
    # MultipleResultsFoundで落ちてはいけない。
    academic_year = 3000 + int(uuid.uuid4().int % 1000)
    db_session.add(
        RecruitmentTerm(
            academic_year=academic_year,
            starts_at=date(2026, 4, 1),
            ends_at=date(2026, 9, 30),
            status=RecruitmentTermStatus.open,
        )
    )
    db_session.add(
        RecruitmentTerm(
            academic_year=academic_year,
            starts_at=date(2026, 10, 1),
            ends_at=date(2027, 3, 31),
            status=RecruitmentTermStatus.preparing,
        )
    )
    await db_session.flush()

    term, created = await get_or_create_recruitment_term(db_session, academic_year)

    assert created is False
    assert term.academic_year == academic_year
