"""募集期間(recruitment_terms)まわりの共通ヘルパー。

api.seed と api.ensure_recruitment_term の両方から使う。
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import RecruitmentTerm, RecruitmentTermStatus


async def get_or_create_recruitment_term(
    session: AsyncSession, academic_year: int
) -> tuple[RecruitmentTerm, bool]:
    """指定年度の募集期間を取得、無ければ作成する(べき等)。

    開発中ずっと「募集中」として扱われるよう、期間は年度いっぱいまで広めに取る
    (本来の募集期間は4〜5月の1ヶ月程度を想定しているが、開発・デモ用途で
    使い続けられることを優先する)。
    """
    result = await session.execute(
        select(RecruitmentTerm).where(RecruitmentTerm.academic_year == academic_year)
    )
    term = result.scalar_one_or_none()
    if term is not None:
        return term, False

    term = RecruitmentTerm(
        academic_year=academic_year,
        starts_at=date(academic_year, 4, 1),
        ends_at=date(academic_year, 12, 31),
        status=RecruitmentTermStatus.open,
    )
    session.add(term)
    await session.flush()
    return term, True
