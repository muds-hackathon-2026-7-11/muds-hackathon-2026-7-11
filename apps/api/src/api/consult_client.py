import json
from dataclasses import dataclass, field
from typing import Protocol

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from api.config import settings


@dataclass
class ConsultResult:
    reply: str  # 学生に見せる会話文
    recommendations: list[dict]  # [{"seminar_name": str, "reason": str}]


@dataclass
class ConsultTurn:
    """会話履歴の1発話。role は "user" か "assistant"。"""

    role: str
    content: str


class ConsultClient(Protocol):
    async def consult(
        self,
        *,
        message: str,
        history: list[ConsultTurn],
        seminars_context: str,
    ) -> ConsultResult: ...


_SYSTEM_PROMPT = (
    "あなたは大学のゼミ配属を支援するアドバイザーです。"
    "学生の相談内容に対し、以下に与えられるゼミ情報の中から適したゼミを"
    "理由とともに推薦してください。ゼミ情報に無いゼミは推薦せず、"
    "情報が不足する場合は正直にその旨を伝えます。"
    "必ず日本語で、指定されたJSON形式のみを返してください。\n"
    'JSON形式: {"reply": "<学生への返答文(1〜3文)>", '
    '"recommendations": [{"seminar_name": "<ゼミ名>", "reason": "<推薦理由>"}]}'
)


def _messages(
    message: str, history: list[ConsultTurn], seminars_context: str
) -> list[ChatCompletionMessageParam]:
    messages: list[ChatCompletionMessageParam] = [
        {
            "role": "system",
            "content": f"{_SYSTEM_PROMPT}\n\n# 利用可能なゼミ情報\n{seminars_context}",
        }
    ]
    for turn in history:
        if turn.role == "assistant":
            messages.append({"role": "assistant", "content": turn.content})
        else:
            messages.append({"role": "user", "content": turn.content})
    messages.append({"role": "user", "content": message})
    return messages


class OpenAIConsultClient:
    """OpenAI(ChatGPT)でゼミ相談への推薦を生成する。"""

    def __init__(self, *, api_key: str, base_url: str | None, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    async def consult(
        self,
        *,
        message: str,
        history: list[ConsultTurn],
        seminars_context: str,
    ) -> ConsultResult:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=_messages(message, history, seminars_context),
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        recommendations = [
            {
                "seminar_name": str(r.get("seminar_name", "")),
                "reason": str(r.get("reason", "")),
            }
            for r in data.get("recommendations", [])
            if isinstance(r, dict)
        ]
        return ConsultResult(
            reply=str(data.get("reply", "")), recommendations=recommendations
        )


@dataclass
class FakeConsultClient:
    """テスト用。実APIを叩かず固定の返答を返し、呼び出しを記録する。"""

    reply: str = "テスト用の相談返答です。"
    recommendations: list[dict] = field(
        default_factory=lambda: [{"seminar_name": "テストゼミ", "reason": "理由A"}]
    )
    calls: list[dict] = field(default_factory=list)

    async def consult(
        self,
        *,
        message: str,
        history: list[ConsultTurn],
        seminars_context: str,
    ) -> ConsultResult:
        self.calls.append(
            {
                "message": message,
                "history": history,
                "seminars_context": seminars_context,
            }
        )
        return ConsultResult(reply=self.reply, recommendations=self.recommendations)


def get_consult_client() -> ConsultClient:
    return OpenAIConsultClient(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.match_model,
    )
