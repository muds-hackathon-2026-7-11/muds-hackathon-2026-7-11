"""募集期間(recruitment_terms)まわりの共通ヘルパー。

api.seed と api.ensure_recruitment_term の両方から使う。

1年度に何回募集するか(前期・後期等)は固定せず、運営がUI/APIで自由に
期間を設定できるようにする方針のため、ここではdev/デモ用途の簡易な
「その年度の募集期間が1件も無ければ、まず1件作る」というget_or_create
のみ提供する。実運用での複数期間の作成・編集は運営向けAPI(#57)側で行う。
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
    (本来の募集期間は1ヶ月程度を想定しているが、開発・デモ用途で
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
