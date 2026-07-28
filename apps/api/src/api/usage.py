"""AI機能(OpenAI呼び出し)の利用回数を募集期間ごとに数え、上限を超えたら
呼び出しを止めるための共通処理(#201)。

上限が無いと1人が連打するだけで費用が青天井になる(診断1コール約0.3円、
2秒間隔で約540円/時)。ここで天井を確定させる。

なお、これはアプリを経由した利用にしか効かない。APIキー自体が漏れた場合の
歯止めにはならないため、OpenAI管理画面側の月額予算上限は別途必要。
"""

import logging

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.models import AiFeature, AiUsage, User, UserRole
from api.services import get_current_term

logger = logging.getLogger(__name__)


class UsageLimitReached(Exception):
    """募集期間あたりのAI利用上限に達した。呼び出し側でメッセージ化する。

    LLM呼び出しの失敗(None扱い)とは区別したいので専用の例外にしている。
    利用者に見せる文言は機能ごとに違うため、ここでは持たせない。
    """


def _limit(feature: AiFeature) -> int:
    if feature is AiFeature.consult:
        return settings.ai_consult_limit_per_term
    return settings.ai_match_limit_per_term


async def consume(db: AsyncSession, *, user: User, feature: AiFeature) -> None:
    """OpenAIを1回呼ぶ分の枠を消費する。上限超過なら UsageLimitReached。

    **実際にOpenAIを呼ぶ直前に呼ぶこと。** 採点キャッシュがヒットして
    LLMを呼ばずに済むケースで消費してしまうと、課金されていない分まで
    上限を削ることになる。

    同時に連打されても上限を超えないよう、INSERT ... ON CONFLICT DO UPDATE の
    1文で原子的に加算し、加算後の値で判定する(SELECTしてからUPDATEすると
    並行リクエストで両方が上限内と判定されうる)。
    """
    limit = _limit(feature)
    if limit <= 0:  # 0以下は「無制限」の設定値
        return
    if user.role in (UserRole.teacher, UserRole.admin):
        return

    # 募集期間外は term_id=NULL の枠でまとめて数える。募集期間が変われば
    # 別の行になるので、新しいラウンドが始まれば上限は自然にリセットされる。
    term = await get_current_term(db)
    stmt = (
        pg_insert(AiUsage)
        .values(
            user_id=user.id,
            term_id=term.id if term is not None else None,
            feature=feature,
            count=1,
        )
        .on_conflict_do_update(
            constraint="uq_ai_usage_user_term_feature",
            # on_conflict_do_update は onupdate のPython側デフォルトを見ないため
            # updated_at は明示的に更新する。
            set_={"count": AiUsage.count + 1, "updated_at": func.now()},
        )
        .returning(AiUsage.count)
    )
    used = (await db.execute(stmt)).scalar_one()
    if used > limit:
        logger.info(
            "ai usage limit reached: user=%s feature=%s used=%s limit=%s",
            user.id,
            feature.value,
            used,
            limit,
        )
        raise UsageLimitReached
