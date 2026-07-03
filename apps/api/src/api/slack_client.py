from dataclasses import dataclass, field
from typing import Any, Protocol

from slack_sdk.web.async_client import AsyncWebClient

from api.config import settings


@dataclass
class SentDM:
    slack_user_id: str
    text: str
    channel_id: str
    message_ts: str


@dataclass
class UpdatedMessage:
    channel_id: str
    message_ts: str
    text: str


class SlackClient(Protocol):
    async def send_dm(
        self,
        *,
        slack_user_id: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
    ) -> SentDM: ...

    async def update_message(
        self,
        *,
        channel_id: str,
        message_ts: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
    ) -> UpdatedMessage: ...

    async def get_display_name(self, *, slack_user_id: str) -> str: ...


class RealSlackClient:
    """本物のSlack Web APIを呼び出すクライアント。"""

    def __init__(self, token: str) -> None:
        self._client = AsyncWebClient(token=token)

    async def send_dm(
        self,
        *,
        slack_user_id: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
    ) -> SentDM:
        open_result = await self._client.conversations_open(users=[slack_user_id])
        channel_id = open_result["channel"]["id"]
        post_result = await self._client.chat_postMessage(
            channel=channel_id, text=text, blocks=blocks
        )
        return SentDM(
            slack_user_id=slack_user_id,
            text=text,
            channel_id=channel_id,
            message_ts=post_result["ts"],
        )

    async def update_message(
        self,
        *,
        channel_id: str,
        message_ts: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
    ) -> UpdatedMessage:
        await self._client.chat_update(
            channel=channel_id, ts=message_ts, text=text, blocks=blocks
        )
        return UpdatedMessage(channel_id=channel_id, message_ts=message_ts, text=text)

    async def get_display_name(self, *, slack_user_id: str) -> str:
        result = await self._client.users_info(user=slack_user_id)
        profile = result["user"]["profile"]
        display_name = profile.get("display_name") or profile.get("real_name")
        return str(display_name) if display_name else slack_user_id


@dataclass
class FakeSlackClient:
    """テスト・SLACK_BOT_TOKEN未設定時用。実際にはSlackへ送信しない。"""

    sent: list[SentDM] = field(default_factory=list)
    updated: list[UpdatedMessage] = field(default_factory=list)
    # テストで特定のslack_user_idに紐づく表示名を検証したい場合はここに詰める。
    # 未設定のslack_user_idはslack_user_idをそのまま返す。
    display_names: dict[str, str] = field(default_factory=dict)

    async def send_dm(
        self,
        *,
        slack_user_id: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
    ) -> SentDM:
        sent_dm = SentDM(
            slack_user_id=slack_user_id,
            text=text,
            channel_id=f"fake-dm-{slack_user_id}",
            message_ts=f"fake-ts-{len(self.sent)}",
        )
        self.sent.append(sent_dm)
        return sent_dm

    async def update_message(
        self,
        *,
        channel_id: str,
        message_ts: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
    ) -> UpdatedMessage:
        updated_message = UpdatedMessage(
            channel_id=channel_id, message_ts=message_ts, text=text
        )
        self.updated.append(updated_message)
        return updated_message

    async def get_display_name(self, *, slack_user_id: str) -> str:
        return self.display_names.get(slack_user_id, slack_user_id)


def get_slack_client() -> SlackClient:
    if settings.slack_bot_token is None:
        return FakeSlackClient()
    return RealSlackClient(settings.slack_bot_token)
