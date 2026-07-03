from dataclasses import dataclass, field
from typing import Protocol

from slack_sdk.web.async_client import AsyncWebClient

from api.config import settings


@dataclass
class SentDM:
    slack_user_id: str
    text: str
    channel_id: str
    message_ts: str


class SlackClient(Protocol):
    async def send_dm(self, *, slack_user_id: str, text: str) -> SentDM: ...


class RealSlackClient:
    """本物のSlack Web APIを呼び出すクライアント。"""

    def __init__(self, token: str) -> None:
        self._client = AsyncWebClient(token=token)

    async def send_dm(self, *, slack_user_id: str, text: str) -> SentDM:
        open_result = await self._client.conversations_open(users=[slack_user_id])
        channel_id = open_result["channel"]["id"]
        post_result = await self._client.chat_postMessage(channel=channel_id, text=text)
        return SentDM(
            slack_user_id=slack_user_id,
            text=text,
            channel_id=channel_id,
            message_ts=post_result["ts"],
        )


@dataclass
class FakeSlackClient:
    """テスト・SLACK_BOT_TOKEN未設定時用。実際にはSlackへ送信しない。"""

    sent: list[SentDM] = field(default_factory=list)

    async def send_dm(self, *, slack_user_id: str, text: str) -> SentDM:
        sent_dm = SentDM(
            slack_user_id=slack_user_id,
            text=text,
            channel_id=f"fake-dm-{slack_user_id}",
            message_ts=f"fake-ts-{len(self.sent)}",
        )
        self.sent.append(sent_dm)
        return sent_dm


def get_slack_client() -> SlackClient:
    if settings.slack_bot_token is None:
        return FakeSlackClient()
    return RealSlackClient(settings.slack_bot_token)
