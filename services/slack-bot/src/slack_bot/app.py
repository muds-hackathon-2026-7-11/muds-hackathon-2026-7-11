import logging
import os

import httpx
from slack_bolt import App

from slack_bot.api_client import fetch_seminars, submit_question

logger = logging.getLogger(__name__)


def _home_view() -> dict:
    web_app_url = os.environ.get("WEB_APP_URL", "http://localhost:3100")
    return {
        "type": "home",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🎓 ゼミナビ"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "ゼミ選択をサポートします"},
            },
            {"type": "divider"},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🌐 アプリを開く"},
                        "url": web_app_url,
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "💬 質問する"},
                        "action_id": "question",
                    },
                ],
            },
        ],
    }


def _question_modal_view(seminars: list[dict]) -> dict:
    seminar_options = [
        {
            "text": {"type": "plain_text", "text": seminar["name"]},
            "value": seminar["id"],
        }
        for seminar in seminars
    ]
    return {
        "type": "modal",
        "callback_id": "question_submit",
        "title": {"type": "plain_text", "text": "質問する"},
        "submit": {"type": "plain_text", "text": "送信"},
        "close": {"type": "plain_text", "text": "キャンセル"},
        "blocks": [
            {
                "type": "input",
                "block_id": "seminar_block",
                "label": {"type": "plain_text", "text": "ゼミを選択"},
                "element": {
                    "type": "static_select",
                    "action_id": "seminar_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "ゼミを選んでください",
                    },
                    "options": seminar_options,
                },
            },
            {
                "type": "input",
                "block_id": "content_block",
                "label": {"type": "plain_text", "text": "質問内容"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "content_input",
                    "multiline": True,
                },
            },
        ],
    }


def create_app(token_verification_enabled: bool = True) -> App:
    """Build the Bolt App and register all handlers.

    Handler registration happens inside this factory (rather than at module
    import time) so importing this module never requires SLACK_BOT_TOKEN to
    be set, keeping it testable without live credentials. Tests should pass
    token_verification_enabled=False to skip Bolt's eager auth.test call.
    """
    app = App(
        token=os.environ["SLACK_BOT_TOKEN"],
        token_verification_enabled=token_verification_enabled,
    )

    @app.event("app_home_opened")
    def update_home(client, event) -> None:
        client.views_publish(user_id=event["user"], view=_home_view())

    @app.action("question")
    def open_question_modal(ack, body, client) -> None:
        ack()
        user_id = body["user"]["id"]
        try:
            seminars = fetch_seminars()
        except httpx.HTTPError:
            logger.exception("failed to fetch seminars from API")
            client.chat_postEphemeral(
                channel=user_id,
                user=user_id,
                text="ゼミ情報の取得に失敗しました。時間をおいて再度お試しください。",
            )
            return

        if not seminars:
            client.chat_postEphemeral(
                channel=user_id,
                user=user_id,
                text="現在登録されているゼミがありません。",
            )
            return

        client.views_open(
            trigger_id=body["trigger_id"], view=_question_modal_view(seminars)
        )

    @app.view("question_submit")
    def handle_question_submit(ack, body, view, client) -> None:
        ack()
        user_id = body["user"]["id"]
        values = view["state"]["values"]
        seminar_id = values["seminar_block"]["seminar_select"]["selected_option"][
            "value"
        ]
        content = values["content_block"]["content_input"]["value"]

        try:
            response = submit_question(
                seminar_id=seminar_id, slack_user_id=user_id, content=content
            )
        except httpx.HTTPError:
            logger.exception("failed to submit question to API")
            client.chat_postMessage(
                channel=user_id,
                text="送信に失敗しました。時間をおいて再度お試しください。",
            )
            return

        if response.status_code == 201:
            client.chat_postMessage(
                channel=user_id,
                text="送信しました！\n回答が届いたら通知します。",
            )
        elif response.status_code == 404:
            client.chat_postMessage(
                channel=user_id,
                text=response.json().get("detail", "送信に失敗しました。"),
            )
        else:
            logger.error(
                "unexpected API response: status=%s body=%s",
                response.status_code,
                response.text,
            )
            client.chat_postMessage(
                channel=user_id,
                text="送信に失敗しました。時間をおいて再度お試しください。",
            )

    return app
