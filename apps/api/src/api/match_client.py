import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from api.config import settings

# 一括採点(evaluate_all)のプロンプト/ルーブリックのバージョン。プロンプトや
# 観点を変えたらこれを上げると、キャッシュキー(#118)が変わり再計算される。
MATCHES_PROMPT_VERSION = "matches-v1"


@dataclass
class MatchResult:
    score: int  # 0〜100
    feedback: dict  # {"summary": str, "reasons": list[str]}


@dataclass
class SeminarInput:
    """一括採点への入力(1ゼミ)。index は結果との対応付けに使う。"""

    index: int
    name: str
    text: str


@dataclass
class RubricScores:
    """観点別スコア(各0〜100)。総合スコアは呼び出し側が重み付けで算出する。"""

    field: int  # 研究分野の一致
    method: int  # 研究手法・使用技術の一致
    interest: int  # 興味テーマ・関心の一致
    style: int  # 育成方針・活動スタイルの合致


@dataclass
class BulkMatchItem:
    rubric: RubricScores
    summary: str
    reasons: list[str]


class MatchClient(Protocol):
    async def evaluate(
        self, *, student_text: str, seminar_text: str
    ) -> MatchResult: ...

    async def evaluate_all(
        self, *, student_text: str, seminars: list[SeminarInput]
    ) -> dict[int, BulkMatchItem]:
        """全ゼミを1コールで観点別採点する。返り値は index -> 採点結果。"""
        ...


_SYSTEM_PROMPT = (
    "あなたは大学のゼミ配属を支援するアドバイザーです。"
    "学生の興味・研究テーマと、ゼミの紹介内容の適合度を評価します。"
    "必ず日本語で、指定されたJSON形式のみを返してください。"
)

_USER_TEMPLATE = (
    "次の学生とゼミの適合度を0〜100の整数で採点し、理由を述べてください。\n"
    'JSON形式: {{"score": <0-100の整数>, "summary": "<1〜2文の総評>", '
    '"reasons": ["<根拠1>", "<根拠2>"]}}\n\n'
    "# 学生の興味・研究テーマ\n{student}\n\n"
    "# ゼミの紹介\n{seminar}"
)

_BULK_SYSTEM_PROMPT = (
    "あなたは大学のゼミ配属を支援するアドバイザーです。"
    "学生プロフィールと各ゼミの内容を、次の4観点でそれぞれ0〜100の整数で"
    "採点します。\n"
    "- field: 研究分野の一致\n"
    "- method: 研究手法・使用技術の一致\n"
    "- interest: 興味テーマ・関心の一致\n"
    "- style: 育成方針・活動スタイルの合致\n"
    "総合スコアは算出しません(呼び出し側が重み付けします)。"
    "資料から読み取れない点は低めに評価し、推測で高評価しないでください。"
    "必ず日本語で、指定されたJSON形式のみを返してください。"
)


def _clamp_score(value: Any) -> int:
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return 0


def _bulk_user_message(student_text: str, seminars: list[SeminarInput]) -> str:
    blocks = "\n\n".join(f"[{s.index}] {s.name}\n{s.text}" for s in seminars)
    return (
        "各ゼミについて4観点(field/method/interest/style)を0〜100で採点し、"
        "簡潔な総評(summary)と根拠(reasons)を述べてください。\n"
        'JSON形式: {"results": [{"index": <番号>, "field": <0-100>, '
        '"method": <0-100>, "interest": <0-100>, "style": <0-100>, '
        '"summary": "<1〜2文>", "reasons": ["<根拠1>", "<根拠2>"]}]}\n'
        "全てのゼミについて results に1件ずつ返してください。\n\n"
        f"# 学生プロフィール\n{student_text}\n\n"
        f"# ゼミ一覧(番号で識別)\n{blocks}"
    )


def _parse_bulk(content: str) -> dict[int, BulkMatchItem]:
    """一括採点JSONを index -> BulkMatchItem に変換する。不正なら ValueError。"""
    data = json.loads(content)
    results = data.get("results")
    if not isinstance(results, list):
        raise ValueError("results is not a list")

    out: dict[int, BulkMatchItem] = {}
    for item in results:
        if not isinstance(item, dict) or "index" not in item:
            continue
        try:
            index = int(item["index"])
        except (TypeError, ValueError):
            continue
        raw_reasons = item.get("reasons", [])
        reasons = [str(x) for x in raw_reasons] if isinstance(raw_reasons, list) else []
        out[index] = BulkMatchItem(
            rubric=RubricScores(
                field=_clamp_score(item.get("field")),
                method=_clamp_score(item.get("method")),
                interest=_clamp_score(item.get("interest")),
                style=_clamp_score(item.get("style")),
            ),
            summary=str(item.get("summary", "")),
            reasons=reasons,
        )
    if not out:
        raise ValueError("no results parsed")
    return out


class OpenAIMatchClient:
    """OpenAI(ChatGPT)でマッチ度を採点する。

    base_url は Azure OpenAI やプロキシ等、OpenAI互換エンドポイントの差し替え用。
    """

    def __init__(self, *, api_key: str, base_url: str | None, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    async def evaluate(self, *, student_text: str, seminar_text: str) -> MatchResult:
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _USER_TEMPLATE.format(
                    student=student_text, seminar=seminar_text
                ),
            },
        ]
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        score = max(0, min(100, int(data.get("score", 0))))
        feedback = {
            "summary": str(data.get("summary", "")),
            "reasons": list(data.get("reasons", [])),
        }
        return MatchResult(score=score, feedback=feedback)

    async def evaluate_all(
        self, *, student_text: str, seminars: list[SeminarInput]
    ) -> dict[int, BulkMatchItem]:
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": _BULK_SYSTEM_PROMPT},
            {"role": "user", "content": _bulk_user_message(student_text, seminars)},
        ]
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        return _parse_bulk(content)


@dataclass
class FakeMatchClient:
    """テスト用。実APIを叩かず固定の評価を返し、呼び出しを記録する。"""

    score: int = 75
    feedback: dict = field(
        default_factory=lambda: {"summary": "テスト用の評価", "reasons": ["理由A"]}
    )
    calls: list[tuple[str, str]] = field(default_factory=list)
    bulk_calls: list[tuple[str, list[str]]] = field(default_factory=list)

    async def evaluate(self, *, student_text: str, seminar_text: str) -> MatchResult:
        self.calls.append((student_text, seminar_text))
        return MatchResult(score=self.score, feedback=self.feedback)

    async def evaluate_all(
        self, *, student_text: str, seminars: list[SeminarInput]
    ) -> dict[int, BulkMatchItem]:
        self.bulk_calls.append((student_text, [s.name for s in seminars]))
        return {
            s.index: BulkMatchItem(
                rubric=RubricScores(
                    field=self.score,
                    method=self.score,
                    interest=self.score,
                    style=self.score,
                ),
                summary=str(self.feedback["summary"]),
                reasons=list(self.feedback["reasons"]),
            )
            for s in seminars
        }


def get_match_client() -> MatchClient:
    return OpenAIMatchClient(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.match_model,
    )
