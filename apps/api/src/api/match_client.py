import json
from dataclasses import dataclass, field
from typing import Protocol

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from api.config import settings


@dataclass
class MatchResult:
    score: int  # 0〜100
    feedback: dict  # {"summary": str, "reasons": list[str]}


class MatchClient(Protocol):
    async def evaluate(
        self, *, student_text: str, seminar_text: str
    ) -> MatchResult: ...


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


@dataclass
class FakeMatchClient:
    """テスト用。実APIを叩かず固定の評価を返し、呼び出しを記録する。"""

    score: int = 75
    feedback: dict = field(
        default_factory=lambda: {"summary": "テスト用の評価", "reasons": ["理由A"]}
    )
    calls: list[tuple[str, str]] = field(default_factory=list)

    async def evaluate(self, *, student_text: str, seminar_text: str) -> MatchResult:
        self.calls.append((student_text, seminar_text))
        return MatchResult(score=self.score, feedback=self.feedback)


def get_match_client() -> MatchClient:
    return OpenAIMatchClient(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.match_model,
    )
